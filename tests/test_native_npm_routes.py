"""Exact packed npm consumer executes source-owning Rust discovery without Python."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tomllib
from pathlib import Path

import pytest
from tests import native_artifact_consumers

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def packed(tmp_path_factory: pytest.TempPathFactory, request: pytest.FixtureRequest) -> Path:
    if os.environ.get("AW_NATIVE_ARTIFACT_DIR"):
        request.getfixturevalue("shared_core_binary")
        assert native_artifact_consumers.CURRENT is not None
        return native_artifact_consumers.CURRENT["package"]
    root = tmp_path_factory.mktemp("packed-native-routes")
    stage = root / "stage"
    staged = subprocess.run(
        [sys.executable, str(ROOT / "scripts/release/stage_native_npm.py"), "--output", str(stage), "--profile", "dev"],
        cwd=ROOT,
        env={**os.environ, "CARGO_BUILD_TARGET": "unavailable-cross-target"},
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stdout + staged.stderr
    npm = shutil.which("npm")
    assert npm
    checked = subprocess.run(
        [npm, "test"],
        cwd=stage,
        capture_output=True,
        text=True,
        env={key: value for key, value in os.environ.items() if key != "AGENTIC_WORKSPACE_CORE_BINARY"},
    )
    assert checked.returncode == 0, checked.stdout + checked.stderr
    subprocess.run([npm, "pack", "--pack-destination", str(root)], cwd=stage, check=True, capture_output=True, text=True)
    (archive,) = root.glob("*.tgz")
    consumer = root / "consumer"
    consumer.mkdir()
    (consumer / "package.json").write_text(json.dumps({"name": "isolated-route-consumer", "version": "1.0.0", "private": True}))
    subprocess.run(
        [npm, "install", "--ignore-scripts", "--offline", "--no-audit", "--no-fund", str(archive)],
        cwd=consumer,
        check=True,
        capture_output=True,
        text=True,
    )
    return consumer / "node_modules/@agentic-workspace/workspace-cli"


def run(package: Path, target: Path, *flags: str) -> dict:
    node = shutil.which("node")
    assert node
    environment = {key: value for key, value in os.environ.items() if key != "AGENTIC_WORKSPACE_CORE_BINARY"}
    environment["PATH"] = ""
    context = {"target": str(target)}
    if flags[0] == "routes":
        for key in ("parent", "exact"):
            if f"--{key}" in flags:
                context[key] = flags[flags.index(f"--{key}") + 1]
        module = (package / "src/native/operating.mjs").as_uri()
        command = [
            node,
            "--input-type=module",
            "-e",
            f"import {{start}} from {json.dumps(module)}; "
            "const input=JSON.parse(process.argv[1]); const context={target:input.target,task:'Inspect routes',projection:'full'}; "
            "let view=start(context); "
            "if(input.exact || input.parent) { const kind=input.exact?'semantic-routes/select/v1':'semantic-routes/discover/v1'; "
            "const request=view.semantic_routes.requests.find(r=>r.request_kind===kind); "
            "request.arguments=input.exact?{posture:'selected',routes:[input.exact]}:{parent:input.parent}; view=start({...context,request}); } "
            "console.log(JSON.stringify(view.semantic_routes));",
            json.dumps(context),
        ]
    else:
        command = [node, str(package / "src/cli.mjs"), "instructions", *flags, "--target", str(target), "--format", "json"]
    result = subprocess.run(
        command,
        cwd=target,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode:
        return {"status": "failed", "error": result.stderr}
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


def test_packed_npm_includes_registry_readme_and_product_summary(packed: Path) -> None:
    assert (packed / "README.md").read_bytes() == (ROOT / "README.md").read_bytes()
    metadata = json.loads((packed / "package.json").read_text(encoding="utf-8"))
    product = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert metadata["description"] == product["project"]["description"]


def test_real_packed_npm_discovers_without_python_or_source_checkout(packed: Path, tmp_path: Path) -> None:
    registry = tmp_path / "tools/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True)
    original = (ROOT / "tools/skills/REGISTRY.json").read_bytes()
    registry.write_bytes(original)
    declaration = json.loads(original)
    skill = next(skill for skill in declaration["skills"] if skill.get("semantic_routes"))
    route = skill["semantic_routes"][0]
    leaf = route if isinstance(route, str) else route["id"]
    roots = run(packed, tmp_path, "routes")
    assert roots["status"] == "current", roots
    assert leaf.split("/")[0] in [item["id"] for item in roots["discovery"]["children"]]
    exact = run(packed, tmp_path, "routes", "--exact", leaf)
    assert exact["decision"]["semantic_task_routes"]["routes"] == [leaf]
    branch = run(packed, tmp_path, "routes", "--parent", leaf.rsplit("/", 1)[0])
    assert leaf in [item["id"] for item in branch["discovery"]["children"]]
    assert registry.read_bytes() == original
    assert not (tmp_path / ".agentic-workspace").exists()
    package = json.loads((packed / "package.json").read_text())
    manifest = json.loads((packed / "src/native/bin/artifact.json").read_text())
    assert manifest["package_version"] == package["version"]
    assert package["os"] == [manifest["platform"]]
    assert package["cpu"] == [manifest["arch"]]
    assert not list(packed.rglob("*.py"))
    # The binary's embedded payload matters as much as the visible tarball.
    git = shutil.which("git")
    assert git
    subprocess.run([git, "init", "-q", str(tmp_path)], check=True)
    script = """
import {start, invoke} from './src/native/operating.mjs';
const context = {target: process.argv[1], task: 'Adopt portable procedures', projection: 'full'};
let current = start(context);
current = start({...context, request: current.configuration_write.repository_adoption_request});
const request = current.configuration_write.adoption_requests.find(r => r.arguments.mode === 'adopt');
current = start({...context, request});
const answer = current.decision_packet.pending_consequences.decisions.find(d => d.id === 'repository-adoption-authorization').response_request;
answer.arguments.answer = 'authorize-write';
current = start({...context, request: answer});
console.log(JSON.stringify(invoke({...context, invocation: current.decision_packet.primary_action})));
"""
    environment = {key: value for key, value in os.environ.items() if key not in {"AGENTIC_WORKSPACE_CORE_BINARY", "PYTHONPATH"}}
    environment["PATH"] = str(Path(git).parent)
    assert shutil.which("python", path=environment["PATH"]) is None
    adopted = subprocess.run(
        [shutil.which("node"), "--input-type=module", "-e", script, str(tmp_path)],
        cwd=packed,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert adopted.returncode == 0, adopted.stderr
    assert json.loads(adopted.stdout)["effect_outcome"]["status"] == "committed"
    assert not list((tmp_path / ".agentic-workspace").rglob("*.py"))


def test_packed_operating_projection_uses_exact_reference_without_host_runtime(packed: Path, tmp_path: Path) -> None:
    node = shutil.which("node")
    environment = {key: value for key, value in os.environ.items() if key != "AGENTIC_WORKSPACE_CORE_BINARY"}
    environment["PATH"] = ""
    script = """
import {start, selectReference} from '@agentic-workspace/workspace-cli/operating';
const context = {target: process.argv[1], task: 'Inspect this repository'};
const original = JSON.stringify(context);
const view = start(context);
const detail = selectReference(context, view.detail_refs['/current_work']);
if (JSON.stringify(context) !== original) throw new Error('helper mutated context');
console.log(JSON.stringify(detail));
"""
    result = subprocess.run(
        [node, "--input-type=module", "-e", script, str(tmp_path)],
        cwd=packed.parents[2],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["authority"] == "detail-only"
    assert (packed / "src/native/operating.d.mts").is_file()
    assert not (tmp_path / ".agentic-workspace").exists()


def test_legacy_persistent_selection_remains_an_explicit_nonmutating_gap(packed: Path, tmp_path: Path) -> None:
    carrier = tmp_path / ".agentic-workspace/local/current-task-routes.json"
    carrier.parent.mkdir(parents=True)
    carrier.write_bytes(b"existing route intent must remain")
    result = run(packed, tmp_path, "select-route", "--posture", "none", "--expect-source-revision", "sha256:" + "a" * 64)
    assert result["status"] == "failed", result
    assert "unknown command: instructions" in str(result)
    assert carrier.read_bytes() == b"existing route intent must remain"
    # The replacement is constructible through the same installed artifact;
    # obtaining its request still does not complete the legacy mutation.
    node = shutil.which("node")
    environment = {key: value for key, value in os.environ.items() if key != "AGENTIC_WORKSPACE_CORE_BINARY"}
    environment["PATH"] = ""
    context = json.dumps({"target": str(tmp_path), "task": "Inspect route applicability for this task", "projection": "full"})
    invoked = subprocess.run(
        [
            node,
            "--input-type=module",
            "-e",
            "import {start} from '@agentic-workspace/workspace-cli/operating'; console.log(JSON.stringify(start(JSON.parse(process.argv[1]))));",
            context,
        ],
        cwd=packed.parents[2],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert invoked.returncode == 0, invoked.stderr
    view = json.loads(invoked.stdout)
    assert any(request["request_kind"] == "semantic-routes/select/v1" for request in view["semantic_routes"]["requests"])
    assert carrier.read_bytes() == b"existing route intent must remain"


@pytest.mark.parametrize("failure", ["missing", "manifest", "digest", "version", "platform"])
def test_packed_native_artifact_mismatch_fails_closed(packed: Path, tmp_path: Path, failure: str) -> None:
    package = tmp_path / "package"
    shutil.copytree(packed, package)
    target = tmp_path / "target"
    target.mkdir()
    manifest_path = package / "src/native/bin/artifact.json"
    manifest = json.loads(manifest_path.read_text())
    binary = manifest_path.parent / ("agentic-workspace-core.exe" if os.name == "nt" else "agentic-workspace-core")
    if failure == "manifest":
        manifest_path.unlink()
    elif failure == "missing":
        binary.unlink()
    elif failure == "digest":
        binary.write_bytes(binary.read_bytes() + b"tampered")
    else:
        manifest["package_version" if failure == "version" else "platform"] = "wrong"
        manifest_path.write_text(json.dumps(manifest))
    result = run(package, target, "routes")
    assert result["status"] == "failed", result
    assert "shared-core" in str(result) or "shared Agentic Workspace core" in str(result)
    assert not (target / ".agentic-workspace").exists()


def test_sdist_retains_native_npm_build_inputs(tmp_path: Path) -> None:
    built = subprocess.run(["uv", "build", "--sdist", "--out-dir", str(tmp_path)], cwd=ROOT, capture_output=True, text=True)
    assert built.returncode == 0, built.stdout + built.stderr
    (archive,) = tmp_path.glob("*.tar.gz")
    with tarfile.open(archive) as package:
        names = package.getnames()
    for reference in [
        "Cargo.toml",
        "Cargo.lock",
        "rust-toolchain.toml",
        "scripts/release/native_toolchain.py",
        "crates/agentic-workspace-core/src/native_routes.rs",
        "bindings/node/semantic-decision.mjs",
        "scripts/release/stage_native_npm.py",
        "bindings/node/package.json",
        "scripts/release/coordinated_release.py",
    ]:
        assert any(name.endswith("/" + reference) for name in names), reference
    assert not any("/src/native/bin/" in name or "/generated/workspace/" in name for name in names)
    extracted = tmp_path / "source"
    with tarfile.open(archive) as package:
        package.extractall(extracted, filter="data")
    (source,) = extracted.iterdir()
    # Import the real entrypoint outside the checkout: filename inventory alone
    # misses transitive Python imports required by an sdist rebuild.
    result = subprocess.run(
        [sys.executable, str(source / "scripts/release/stage_native_npm.py"), "--help"],
        cwd=source,
        env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("mismatch", ["host", "compiler"])
def test_stage_rejects_rust_build_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mismatch: str) -> None:
    import runpy
    import tomllib

    monkeypatch.syspath_prepend(str(ROOT / "scripts/release"))
    stage_native_npm = runpy.run_path(str(ROOT / "scripts/release/stage_native_npm.py"))

    def observe(command, **kwargs):
        assert command == ["rustc", "-vV"], "mismatched host must fail before Cargo build"
        release = tomllib.loads((ROOT / "rust-toolchain.toml").read_text())["toolchain"]["channel"] if mismatch == "host" else "0.0.0"
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=f"host: unsupported-unknown-platform\nrelease: {release}\ncommit-hash: fixture\ncommit-date: fixture\nLLVM version: fixture\n",
            stderr="",
        )

    monkeypatch.setattr(stage_native_npm["subprocess"], "run", observe)
    with pytest.raises(ValueError, match="does not match Node artifact host|Native packaging requires Rust"):
        stage_native_npm["stage"](tmp_path / "stage", profile="dev")
    assert not (tmp_path / "stage").exists()


def test_source_generated_discovery_uses_explicit_development_core(tmp_path: Path, shared_core_binary: Path) -> None:
    result = subprocess.run(
        [
            shutil.which("node"),
            str(ROOT / "generated/workspace/typescript/src/cli.mjs"),
            "instructions",
            "routes",
            "--target",
            str(tmp_path),
            "--format",
            "json",
        ],
        cwd=tmp_path,
        env={**os.environ, "PATH": "", "AGENTIC_WORKSPACE_CORE_BINARY": str(shared_core_binary)},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "current"
    assert payload["routes"] == []
    assert not (tmp_path / ".agentic-workspace").exists()


def test_readiness_archive_survives_exact_conformance_reuse(tmp_path: Path) -> None:
    import hashlib
    import runpy

    readiness = runpy.run_path(str(ROOT / "scripts/check/run_external_consumer_readiness.py"))
    runner = runpy.run_path(str(ROOT / "scripts/check/run_generated_command_package_proof.py"))
    dist = tmp_path / "dist"
    dist.mkdir()
    npm = shutil.which("npm")
    assert npm
    archive = readiness["_pack_typescript_artifact"](dist, npm)
    original = hashlib.sha256(archive.read_bytes()).hexdigest()
    # This is CI's order: readiness creates dist's root archive first, then the
    # conformance packer fills missing peers and preserves the exact root bytes.
    runner["_pack_packages"](dist)
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == original
    package = tmp_path / "extracted"
    runner["_extract_tarball"](archive, package)
    target = tmp_path / "target"
    target.mkdir()
    registry = target / "tools/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True)
    registry.write_bytes((ROOT / "tools/skills/REGISTRY.json").read_bytes())
    result = run(package, target, "routes")
    assert result["status"] == "current", result
    assert result["discovery"]["children"]
    assert (package / "src/native/bin/artifact.json").is_file()
    assert not (target / ".agentic-workspace").exists()
