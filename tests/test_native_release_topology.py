"""Isolated release consumers exercise one Rust authority, without source fallback."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/tooling/release"))


@pytest.fixture(scope="module")
def wheel(tmp_path_factory):
    output = (
        Path(os.environ["AW_NATIVE_ARTIFACT_DIR"]) if os.environ.get("AW_NATIVE_ARTIFACT_DIR") else tmp_path_factory.mktemp("native-wheel")
    )
    if not os.environ.get("AW_NATIVE_ARTIFACT_DIR"):
        subprocess.run(["uv", "build", "--wheel", "--out-dir", str(output)], cwd=ROOT, check=True, capture_output=True)
    wheels = list(output.glob("agentic_workspace-*.whl"))
    if len(wheels) > 1:
        import importlib.util

        spec = importlib.util.spec_from_file_location("platform_release", ROOT / "src/tooling/release/platform_release.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        data = module.load(output)
        selected = next(p for p in data["platforms"] if p["target"] == module.current_platform()["target"])
        wheels = [output / selected["wheel"]["asset"]]
    assert len(wheels) == 1
    return wheels[0]


def test_wheel_contains_only_binding_host_adapter_and_paired_core(wheel):
    with zipfile.ZipFile(wheel) as archive:
        files = archive.namelist()
        code = {name for name in files if name.endswith(".py")}
        assert code == {
            f"agentic_workspace/{name}.py"
            for name in ("__init__", "cli", "_binding", "native_core", "codex_provider", "sealed_codex_transport")
        }
        for name in code:
            source = "src/adapters/codex" if Path(name).stem in {"codex_provider", "sealed_codex_transport"} else "src/cli/python"
            assert archive.read(name).decode().replace("\r\n", "\n") == (ROOT / source / name).read_text(encoding="utf-8")
        # The host adapter has provider I/O, not the old Python policy/runtime host.
        provider = ast.parse(archive.read("agentic_workspace/codex_provider.py"))
        for node in ast.walk(provider):
            if isinstance(node, ast.Import):
                assert all(alias.name.split(".")[0] in sys.stdlib_module_names for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                assert not node.level and node.module.split(".")[0] in sys.stdlib_module_names
        metadata = archive.read(next(name for name in files if name.endswith("/METADATA"))).decode()
        assert "Requires-Dist:" not in metadata
        manifest = json.loads(archive.read("agentic_workspace/_native/artifact.json"))
        assert manifest["sha256"] and manifest["cli_sha256"]
        toolchain = manifest["rust_toolchain"]
        assert toolchain["release"] == tomllib.loads((ROOT / "rust-toolchain.toml").read_text())["toolchain"]["channel"]
        assert toolchain["commit_hash"] and toolchain["commit_date"] and toolchain["llvm_version"]
        assert toolchain["host"] == manifest["rust_host"] == manifest["rust_target"]
        assert toolchain["declaration_sha256"] == hashlib.sha256((ROOT / "rust-toolchain.toml").read_bytes()).hexdigest()
        assert not any("_payload" in name or "_generated" in name for name in files)


def test_source_public_import_is_native_and_fails_closed(tmp_path, shared_core_binary):
    script = """
import importlib.util, json, sys
import agentic_workspace as aw
for module in ("decision", "contract_tooling", "static_read_profile", "review_stack_topology"):
    assert importlib.util.find_spec("agentic_workspace." + module) is None
assert not any(name in sys.modules for name in (
    'agentic_workspace.client', 'aw_maintainer.native_conformance',
    'agentic_workspace.workspace_runtime_core', 'agentic_workspace.modules'))
assert not hasattr(aw, 'invoke_operation')
assert not hasattr(aw, 'compile_source_decision')
print(json.dumps(aw.start({'target': '.', 'task': 'Inspect this consumer'})))
"""
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src/cli/python"), "AGENTIC_WORKSPACE_CORE_BINARY": str(shared_core_binary)}
    result = subprocess.run([sys.executable, "-c", script], cwd=tmp_path, env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "decision_packet" in json.loads(result.stdout)
    environment["AGENTIC_WORKSPACE_CORE_BINARY"] = str(tmp_path / "missing-core")
    rejected = subprocess.run([sys.executable, "-c", script], cwd=tmp_path, env=environment, capture_output=True, text=True)
    assert rejected.returncode != 0
    assert "core is unavailable" in rejected.stderr
    assert not (tmp_path / ".agentic-workspace").exists()


def test_isolated_python_owner_mutation_and_missing_core_rejection(wheel, tmp_path):
    venv = tmp_path / "venv"
    subprocess.run(["uv", "venv", "--python", sys.executable, str(venv)], check=True, capture_output=True)
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    subprocess.run(
        ["uv", "pip", "install", "--python", str(python), "--no-deps", "--no-index", "--no-cache", "--link-mode", "copy", str(wheel)],
        check=True,
        capture_output=True,
    )
    target = tmp_path / "consumer"
    target.mkdir()
    environment = {key: value for key, value in os.environ.items() if key not in {"AGENTIC_WORKSPACE_CORE_BINARY", "PYTHONPATH"}}
    environment["PATH"] = ""
    script = """
import json
from pathlib import Path
from agentic_workspace import start, select_reference, invoke_carried
context={'target':str(Path.cwd()), 'task':'Configure this consumer', 'projection':'full'}
first=start(context)
first=start({**context,'request':first['configuration_write']['creation_discovery_request']})
request=next(r for r in first['configuration_write']['creation_requests'] if r['arguments']['key']=='workspace.cli_invoke')
request['arguments']['value']='aw-native'
context['request']=request
context['projection']='compact'
proposal=start(context)
context['projection']='carried'
answered=select_reference(context,proposal['detail_refs']['/decision_packet/decision_request'],answer='authorize-write')
result=invoke_carried(answered['carriage'],answered['view']['decision_packet']['primary_action']['reference'])
assert result['effect_outcome']['status']=='committed',result
assert result['continuation']['retry_effect'] is False
print(json.dumps({'effect':result['effect_outcome']['status']}))
"""
    result = subprocess.run([str(python), "-I", "-c", script], cwd=target, env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["effect"] == "committed"
    parity = subprocess.run(
        [str(python), str(ROOT / "src/tooling/check/check_language_facade.py"), "--installed-python"],
        cwd=target,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert parity.returncode == 0, parity.stderr
    capability = subprocess.run(
        [str(python), "-I", "-m", "agentic_workspace.sealed_codex_transport", "--aw-capability"],
        input='{"model":"fixture"}',
        cwd=target,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert capability.returncode == 0, capability.stderr
    assert json.loads(capability.stdout)["reason"] == "native-adapter-executable-unavailable"
    assert json.loads(capability.stdout)["status"] == "unavailable"
    invalid = subprocess.run(
        [str(python), "-I", "-m", "agentic_workspace.sealed_codex_transport"],
        input="{}",
        cwd=target,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert invalid.returncode != 0 and "worker carriage missing or changed" in invalid.stderr
    native = next(venv.rglob("agentic_workspace/_native/agentic-workspace-core*"))
    native.write_bytes(native.read_bytes() + b"altered")
    rejected = subprocess.run(
        [str(python), "-I", "-c", "from agentic_workspace import start; start({'target':'.'})"],
        cwd=target,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert rejected.returncode != 0 and "digest mismatch" in rejected.stderr
    rejected_bridge = subprocess.run(
        [str(python), "-I", "-m", "agentic_workspace.sealed_codex_transport"],
        input="{}",
        cwd=target,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert rejected_bridge.returncode != 0 and "digest mismatch" in rejected_bridge.stderr


def test_native_npm_has_no_mirrored_runtime_and_runs_paired_cli(tmp_path):
    stage = tmp_path / "stage"
    npm, node = shutil.which("npm"), shutil.which("node")
    if os.environ.get("AW_NATIVE_ARTIFACT_DIR"):
        archives = list(Path(os.environ["AW_NATIVE_ARTIFACT_DIR"]).glob("agentic-workspace-workspace-cli-*.tgz"))
        assert len(archives) == 1
        archive = archives[0]
    else:
        subprocess.run(
            [sys.executable, str(ROOT / "src/tooling/release/stage_native_npm.py"), "--output", str(stage), "--profile", "dev"],
            check=True,
            capture_output=True,
        )
        subprocess.run([npm, "pack", "--pack-destination", str(tmp_path)], cwd=stage, check=True, capture_output=True)
        archive = next(tmp_path.glob("*.tgz"))
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    (consumer / "package.json").write_text('{"private":true}')
    subprocess.run(
        [npm, "install", "--offline", "--no-audit", "--no-fund", "--ignore-scripts", str(archive)],
        cwd=consumer,
        check=True,
        capture_output=True,
    )
    package = consumer / "node_modules/@agentic-workspace/workspace-cli"
    metadata = json.loads((package / "package.json").read_text())
    assert set(metadata["exports"]) == {".", "./operating"}
    assert {p.name for p in (package / "src/native").glob("*.mjs")} == {"operating.mjs", "_transport.mjs"}
    assert not (package / "resources").exists()
    assert not (package / "src/commands").exists()
    environment = {key: value for key, value in os.environ.items() if key != "AGENTIC_WORKSPACE_CORE_BINARY"}
    environment["PATH"] = ""
    result = subprocess.run(
        [node, str(package / "src/cli.mjs"), "start", "--target", str(consumer), "--task", "Inspect this consumer", "--format", "json"],
        cwd=consumer,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["decision_packet"]["status"] == "direct"
    assert not (consumer / ".agentic-workspace").exists()
    native_dir = package / "src/native/bin"
    node_os = {"Windows": "win32", "Linux": "linux", "Darwin": "darwin"}[platform.system()]
    node_arch = "arm64" if platform.machine().lower() in {"aarch64", "arm64"} else "x64"
    if (native_dir / f"{node_os}-{node_arch}").exists():
        native_dir /= f"{node_os}-{node_arch}"
    manifest = json.loads((native_dir / "artifact.json").read_text())
    from tests.test_language_facade import check_node

    contract = json.loads((ROOT / "src/core/contracts/source_decision_contract.json").read_text())["language_facade"]
    core = native_dir / ("agentic-workspace-core.exe" if os.name == "nt" else "agentic-workspace-core")
    check_node(contract, package / "src/native/operating.mjs", core)
    assert manifest["cli_sha256"]
    assert len(list(native_dir.iterdir())) == 3
    script = """
import {start, selectReference, invokeCarried} from '@agentic-workspace/workspace-cli/operating';
const context={target:process.cwd(),task:'Configure this consumer',projection:'full'};
const initial=start(context);
const first=start({...context,request:initial.configuration_write.creation_discovery_request});
const request=first.configuration_write.creation_requests.find(r=>r.arguments.key==='workspace.cli_invoke');
request.arguments.value='aw-native';
context.request=request; context.projection='compact';
const proposal=start(context);
context.projection='carried';
const answered=selectReference(context,proposal.detail_refs['/decision_packet/decision_request'],'authorize-write');
const result=invokeCarried(answered.carriage,answered.view.decision_packet.primary_action.reference);
if(result.effect_outcome.status!=='committed'||result.continuation.retry_effect!==false) throw Error(JSON.stringify(result));
console.log(JSON.stringify(result.effect_outcome));
"""
    effect = subprocess.run([node, "--input-type=module", "-e", script], cwd=consumer, env=environment, capture_output=True, text=True)
    assert effect.returncode == 0, effect.stderr
    assert json.loads(effect.stdout)["status"] == "committed"

    from first_contact import journey, validate_pointer

    git = shutil.which("git")
    environment["PATH"] = os.pathsep.join([str(Path(node).parent), str(Path(git).parent)])
    assert shutil.which("agentic-workspace", path=environment["PATH"]) is None
    subprocess.run([git, "init", "-q", str(consumer)], check=True)
    journey([npm, "exec", "--no", "--", "agentic-workspace"], consumer, environment)
    startup = consumer / ".agentic-workspace/skills/workspace-startup/SKILL.md"
    startup.write_text("stale installed procedure", encoding="utf-8")
    with pytest.raises(ValueError, match="^Installed startup identity mismatch$"):
        validate_pointer(consumer)
    startup.unlink()
    with pytest.raises(ValueError, match="^Installed startup skill missing$"):
        validate_pointer(consumer)
    prefix = tmp_path / "global-install"
    subprocess.run(
        [npm, "install", "--global", "--prefix", str(prefix), "--offline", "--no-audit", "--no-fund", "--ignore-scripts", str(archive)],
        check=True,
        capture_output=True,
    )
    global_env = dict(environment)
    global_env["PATH"] = str(prefix if os.name == "nt" else prefix / "bin") + os.pathsep + environment["PATH"]
    executable = shutil.which("agentic-workspace", path=global_env["PATH"])
    assert executable and Path(executable).is_relative_to(prefix)
    global_consumer = tmp_path / "global-consumer"
    global_consumer.mkdir()
    subprocess.run([git, "init", "-q", str(global_consumer)], check=True)
    journey([executable], global_consumer, global_env)


def test_exact_archive_and_language_packages_share_native_bytes(wheel, tmp_path):
    if not os.environ.get("AW_NATIVE_ARTIFACT_DIR"):
        pytest.skip("exact release set is supplied by the release proof runner")
    directory = Path(os.environ["AW_NATIVE_ARTIFACT_DIR"])
    with zipfile.ZipFile(wheel) as python:
        host = json.loads(python.read("agentic_workspace/_native/artifact.json"))["rust_host"]
    archives = list(directory.glob(f"agentic-workspace-native-*-{host}.zip"))
    assert len(archives) == 1
    with zipfile.ZipFile(archives[0]) as native, zipfile.ZipFile(wheel) as python:
        manifest = json.loads(native.read("artifact.json"))
        python_manifest = json.loads(python.read("agentic_workspace/_native/artifact.json"))
        binaries = [name for name in native.namelist() if name not in {"artifact.json", "LICENSE"}]
        assert len(binaries) == 2
        with tarfile.open(next(directory.glob("agentic-workspace-workspace-cli-*.tgz"))) as node:
            prefix = "package/src/native/bin/"
            if prefix + "artifact.json" not in node.getnames():
                prefix += f"{manifest['platform']}-{manifest['arch']}/"
            node_manifest = json.load(node.extractfile(prefix + "artifact.json"))
            for field in ("rust_toolchain", "rust_host", "rust_target", "source_head", "source_dirty"):
                assert manifest[field] == python_manifest[field] == node_manifest[field]
            assert manifest["source_head"] == subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
            for name in binaries:
                data = native.read(name)
                key = "sha256" if "-core" in name else "cli_sha256"
                assert hashlib.sha256(data).hexdigest() == manifest[key]
                assert python.read(f"agentic_workspace/_native/{name}") == data
                assert node.extractfile(prefix + name).read() == data
                executable = tmp_path / name
                executable.write_bytes(data)
                executable.chmod(0o755)
    cli = next(path for path in tmp_path.iterdir() if "-core" not in path.name)
    environment = {key: value for key, value in os.environ.items() if key != "AGENTIC_WORKSPACE_CORE_BINARY"}
    environment["PATH"] = ""
    result = subprocess.run([str(cli), "--help"], env=environment, cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_source_archive_has_no_development_host_or_workspace_dependencies():
    if not os.environ.get("AW_NATIVE_ARTIFACT_DIR"):
        pytest.skip("requires the exact release source archive")
    directory = Path(os.environ["AW_NATIVE_ARTIFACT_DIR"])
    with tarfile.open(next(directory.glob("agentic_workspace-*.tar.gz"))) as archive:
        names = archive.getnames()
        root = names[0].split("/")[0]
        metadata = archive.extractfile(f"{root}/pyproject.toml").read().decode()
        assert "[tool.uv.workspace]" not in metadata
        assert "[dependency-groups]" not in metadata
        assert not any("/src/agentic_workspace/operations/" in name or "/generated/workspace/python/" in name for name in names)
        assert f"{root}/Cargo.lock" in names
        assert f"{root}/rust-toolchain.toml" in names
        assert f"{root}/deny.toml" in names
        assert f"{root}/src/tooling/check/check_rust_dependencies.py" in names
        assert f"{root}/src/tooling/release/native_toolchain.py" in names
