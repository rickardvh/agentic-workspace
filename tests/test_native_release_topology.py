"""Isolated release consumers exercise one Rust authority, without source fallback."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def wheel(tmp_path_factory):
    output = (
        Path(os.environ["AW_NATIVE_ARTIFACT_DIR"]) if os.environ.get("AW_NATIVE_ARTIFACT_DIR") else tmp_path_factory.mktemp("native-wheel")
    )
    if not os.environ.get("AW_NATIVE_ARTIFACT_DIR"):
        subprocess.run(["uv", "build", "--wheel", "--out-dir", str(output)], cwd=ROOT, check=True, capture_output=True)
    wheels = list(output.glob("agentic_workspace-*.whl"))
    assert len(wheels) == 1
    return wheels[0]


def test_wheel_contains_only_binding_and_paired_core(wheel):
    with zipfile.ZipFile(wheel) as archive:
        files = archive.namelist()
        code = {name for name in files if name.endswith(".py")}
        assert code == {f"agentic_workspace/{name}.py" for name in ("__init__", "cli", "decision", "native_core")}
        metadata = archive.read(next(name for name in files if name.endswith("/METADATA"))).decode()
        assert "Requires-Dist:" not in metadata
        manifest = json.loads(archive.read("agentic_workspace/_native/artifact.json"))
        assert manifest["sha256"] and manifest["cli_sha256"]
        assert not any("_payload" in name or "_generated" in name for name in files)


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


def test_native_npm_has_no_mirrored_runtime_and_runs_paired_cli(tmp_path):
    stage = tmp_path / "stage"
    npm, node = shutil.which("npm"), shutil.which("node")
    if os.environ.get("AW_NATIVE_ARTIFACT_DIR"):
        archives = list(Path(os.environ["AW_NATIVE_ARTIFACT_DIR"]).glob("agentic-workspace-workspace-cli-*.tgz"))
        assert len(archives) == 1
        archive = archives[0]
    else:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/release/stage_native_npm.py"), "--output", str(stage), "--profile", "dev"],
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
    manifest = json.loads((package / "src/native/bin/artifact.json").read_text())
    assert manifest["cli_sha256"]
    assert len(list((package / "src/native/bin").iterdir())) == 3
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


def test_exact_archive_and_language_packages_share_native_bytes(wheel, tmp_path):
    if not os.environ.get("AW_NATIVE_ARTIFACT_DIR"):
        pytest.skip("exact release set is supplied by the release proof runner")
    directory = Path(os.environ["AW_NATIVE_ARTIFACT_DIR"])
    archives = list(directory.glob("agentic-workspace-native-*.zip"))
    assert len(archives) == 1
    with zipfile.ZipFile(archives[0]) as native, zipfile.ZipFile(wheel) as python:
        manifest = json.loads(native.read("artifact.json"))
        binaries = [name for name in native.namelist() if name not in {"artifact.json", "LICENSE"}]
        assert len(binaries) == 2
        with tarfile.open(next(directory.glob("*.tgz"))) as node:
            for name in binaries:
                data = native.read(name)
                key = "sha256" if "-core" in name else "cli_sha256"
                assert hashlib.sha256(data).hexdigest() == manifest[key]
                assert python.read(f"agentic_workspace/_native/{name}") == data
                assert node.extractfile(f"package/src/native/bin/{name}").read() == data
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
    with tarfile.open(next(directory.glob("*.tar.gz"))) as archive:
        names = archive.getnames()
        root = names[0].split("/")[0]
        metadata = archive.extractfile(f"{root}/pyproject.toml").read().decode()
        assert "[tool.uv.workspace]" not in metadata
        assert "[dependency-groups]" not in metadata
        assert not any("/src/agentic_workspace/operations/" in name or "/generated/workspace/python/" in name for name in names)
        assert f"{root}/Cargo.lock" in names
