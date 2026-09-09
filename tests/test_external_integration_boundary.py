from __future__ import annotations

import json
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_necessary_surface_payload_has_no_adapter_lifecycle() -> None:
    payload = json.loads((ROOT / "src/agentic_workspace/contracts/workspace_defaults/payload.json").read_text(encoding="utf-8"))
    encoded = json.dumps(payload).lower()
    forbidden_paths = (
        ".agentic-workspace/adapters/",
        ".agentic-workspace/plugins/",
        ".agentic-workspace/adapter.lock",
        ".agentic-workspace/plugin.lock",
    )
    assert all(path not in encoded for path in forbidden_paths)


def test_external_profile_is_package_owned_not_installed_payload() -> None:
    payload = json.loads((ROOT / "src/agentic_workspace/contracts/workspace_defaults/payload.json").read_text(encoding="utf-8"))
    encoded = json.dumps(payload)
    assert "external_consumer_profile.json" not in encoded
    assert (ROOT / "generated/workspace/python/external_consumer_profile.json").is_file()
    assert (ROOT / "generated/workspace/typescript/external_consumer_profile.json").is_file()


def test_lifecycle_preserves_zero_adapter_footprint_and_consumer_removal(tmp_path: Path) -> None:
    from tests.test_external_consumer_readiness import _module

    checker = _module()

    dist = tmp_path / "dist"
    dist.mkdir()
    wheels = checker._build_python_artifacts(dist)
    consumer_root = tmp_path / "consumer"
    python, script = checker._prepare_python_consumer(consumer_root, wheels)
    host_env = tmp_path / "host-env"
    checker._install_python_stack(host_env, wheels)
    host_cli = checker._console_script(host_env, "agentic-workspace")
    target = tmp_path / "repo"

    def call(request):
        return checker._consumer_request(language="python", consumer_root=consumer_root, executable=python, script=script, request=request)

    checker.exercise_native_lifecycle(call, target)
    before = checker._snapshot(target)
    assert not any("external_consumer_profile.json" in ref for ref in before)
    shutil.rmtree(consumer_root)
    result = subprocess.run(
        [
            str(host_cli),
            "start",
            "--target",
            str(target),
            "--task",
            "Maintain the installed consumer Planning owner",
            "--format",
            "json",
            "--projection",
            "full",
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=target,
    )
    assert json.loads(result.stdout)["planning"]["current_owner"]["current"] is True
    assert checker._snapshot(target) == before


def test_runtime_and_payload_have_no_external_adapter_reverse_dependency() -> None:
    manifests = [ROOT / "pyproject.toml", *(ROOT / "packages").glob("*/pyproject.toml")]
    allowed_workspace_dependencies = {
        "agentic-workspace",
        "agentic-workspace-memory",
        "agentic-workspace-planning",
        "agentic-workspace-verification",
    }
    for manifest in manifests:
        project = tomllib.loads(manifest.read_text(encoding="utf-8"))["project"]
        for dependency in project.get("dependencies", []):
            name = re.split(r"[ @<>=;\[]", dependency, maxsplit=1)[0].lower()
            if name.startswith(("agentic-", "agentic_")):
                assert name in allowed_workspace_dependencies, (manifest, name)
    payload = json.loads((ROOT / "src/agentic_workspace/contracts/workspace_defaults/payload.json").read_text(encoding="utf-8"))
    encoded_payload = json.dumps(payload).lower()
    assert not any(token in encoded_payload for token in ("adapter_package", "plugin_package", "adapter_registry"))
    for manifest in ROOT.rglob("package.json"):
        if "node_modules" in manifest.parts:
            continue
        package = json.loads(manifest.read_text(encoding="utf-8"))
        dependencies = {
            name.lower()
            for field in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")
            for name in package.get(field, {})
        }
        assert not any("adapter" in name or "external-consumer" in name for name in dependencies), (manifest, dependencies)
    packaged = json.loads((ROOT / "generated/workspace/typescript/package.json").read_text(encoding="utf-8"))["files"]
    assert not any("adapter" in item.lower() for item in packaged)
    for source in [*ROOT.glob("src/**/*.py"), *ROOT.glob("generated/workspace/**/*.*")]:
        if source.suffix not in {".py", ".mjs", ".js"}:
            continue
        text = source.read_text(encoding="utf-8")
        assert not re.search(r"(?:from|import|require\s*\()[^\n]*adapter_package", text), source
