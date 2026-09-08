"""Exact packed npm consumer executes source-owning Rust discovery without Python."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def packed(tmp_path_factory: pytest.TempPathFactory) -> Path:
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
    checked = subprocess.run([npm, "test"], cwd=stage, capture_output=True, text=True)
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
    result = subprocess.run(
        [node, str(package / "src/cli.mjs"), "instructions", *flags, "--target", str(target), "--format", "json"],
        cwd=target,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


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
    assert leaf.split("/")[0] in [item["id"] for item in roots["routes"]]
    exact = run(packed, tmp_path, "routes", "--exact", leaf)
    assert exact["route_count"] == 1
    assert exact["routes"][0]["id"] == leaf
    assert any(binding["capability"] == "skill:" + skill["id"] for binding in exact["routes"][0]["capability_bindings"])
    branch = run(packed, tmp_path, "routes", "--parent", leaf.rsplit("/", 1)[0])
    assert leaf in [item["id"] for item in branch["routes"]]
    assert registry.read_bytes() == original
    assert not (tmp_path / ".agentic-workspace").exists()
    package = json.loads((packed / "package.json").read_text())
    manifest = json.loads((packed / "src/native/bin/artifact.json").read_text())
    assert manifest["package_version"] == package["version"]
    assert package["os"] == [manifest["platform"]]
    assert package["cpu"] == [manifest["arch"]]


def test_legacy_persistent_selection_remains_an_explicit_nonmutating_gap(packed: Path, tmp_path: Path) -> None:
    carrier = tmp_path / ".agentic-workspace/local/current-task-routes.json"
    carrier.parent.mkdir(parents=True)
    carrier.write_bytes(b"existing route intent must remain")
    result = run(packed, tmp_path, "select-route", "--posture", "none", "--expect-source-revision", "sha256:" + "a" * 64)
    assert result["status"] == "failed", result
    assert result["mutation_applied"] is False
    assert "native-persistent-route-selection-unavailable" in str(result)
    assert "semantic-routes/select/v1" in str(result)
    assert carrier.read_bytes() == b"existing route intent must remain"
    assert result["recovery"]["api"] == "@agentic-workspace/workspace-cli/native"
    # The replacement is constructible through the same installed artifact;
    # obtaining its request still does not complete the legacy mutation.
    node = shutil.which("node")
    environment = {key: value for key, value in os.environ.items() if key != "AGENTIC_WORKSPACE_CORE_BINARY"}
    environment["PATH"] = ""
    context = json.dumps({"target": str(tmp_path), "task": "Inspect route applicability for this task"})
    invoked = subprocess.run(
        [
            node,
            "--input-type=module",
            "-e",
            "import {start} from '@agentic-workspace/workspace-cli/native'; console.log(JSON.stringify(start(JSON.parse(process.argv[1]))));",
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
    (binary,) = [path for path in manifest_path.parent.iterdir() if path.name != "artifact.json"]
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
    assert "native-route-discovery-unavailable" in str(result)
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
        "crates/agentic-workspace-core/src/native_routes.rs",
        "bindings/node/semantic-decision.mjs",
        "scripts/release/stage_native_npm.py",
        "generated/workspace/typescript/package.json",
        "generated/workspace/typescript/src/native/semantic-decision.mjs",
    ]:
        assert any(name.endswith("/" + reference) for name in names), reference
    assert not any("/src/native/bin/" in name for name in names)


def test_stage_rejects_rust_host_platform_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import runpy

    stage_native_npm = runpy.run_path(str(ROOT / "scripts/release/stage_native_npm.py"))

    def observe(command, **kwargs):
        assert command == ["rustc", "-vV"], "mismatched host must fail before Cargo build"
        return subprocess.CompletedProcess(command, 0, stdout="host: unsupported-unknown-platform\n", stderr="")

    monkeypatch.setattr(stage_native_npm["subprocess"], "run", observe)
    with pytest.raises(ValueError, match="does not match Node artifact host"):
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
