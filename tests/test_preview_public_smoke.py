from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "release" / "preview_public_smoke.py"


def _load_module():
    release_root = str(ROOT / "scripts" / "release")
    if release_root not in sys.path:
        sys.path.insert(0, release_root)
    spec = importlib.util.spec_from_file_location("preview_public_smoke_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_public_smoke_installs_exact_published_requirement_and_runs_native_start(tmp_path, monkeypatch) -> None:
    module = _load_module()
    verified = {
        "tag": "preview-v0.52.0",
        "version": "0.52.0",
        "artifact_commit": "b" * 40,
        "reconstruction_source_commit": "a" * 40,
    }
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github/release-ownership.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module.coordinated_release, "verify_preview_release", lambda ownership, tag: verified)
    monkeypatch.setattr(module.preview_release, "verify_published_preview", lambda **kwargs: True)

    wheel = "agentic_workspace-0.52.0-py3-none-linux_x86_64.whl"
    digest = "1" * 64
    url = f"https://github.com/owner/repo/releases/download/{verified['tag']}/{wheel}"
    requirement = f"agentic-workspace @ {url}#sha256={digest}"
    manifest = {
        **verified,
        "release_class": "preview",
        "support_bearing": False,
        "packages": [
            {
                "name": "agentic-workspace",
                "ecosystem": "python",
                "version": "0.52.0",
                "wheel": {"asset": wheel, "sha256": digest},
            }
        ],
    }
    readiness = {
        "kind": "agentic-workspace/distribution-install-readiness/v1",
        "status": "passed",
        "release_class": "preview",
        "support_bearing": False,
        "tag": verified["tag"],
        "version": verified["version"],
        "artifact": {"name": wheel, "sha256": digest, "url": url},
        "install": {"requirement": requirement, "command": f'uv tool install "{requirement}"'},
        "registry_resolution_used": False,
    }
    calls: list[tuple[list[str], Path, dict[str, str] | None]] = []

    def run(args: list[str], *, cwd: Path = tmp_path, env=None):
        calls.append((args, cwd, env))
        if args[:3] == ["gh", "release", "download"]:
            destination = Path(args[args.index("--dir") + 1])
            (destination / module.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
            (destination / module.READINESS_NAME).write_text(json.dumps(readiness), encoding="utf-8")
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[:3] == ["uv", "tool", "install"]:
            assert args == ["uv", "tool", "install", requirement]
            assert env is not None and env["UV_NO_CACHE"] == "1" and "PYTHONPATH" not in env
            executable = Path(env["UV_TOOL_BIN_DIR"]) / ("agentic-workspace.exe" if module.os.name == "nt" else "agentic-workspace")
            executable.parent.mkdir(parents=True, exist_ok=True)
            executable.write_text("installed", encoding="utf-8")
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[:3] == ["git", "rev-parse", f"{'a' * 40}^{{tree}}"]:
            return subprocess.CompletedProcess(args, 0, "c" * 40 + "\n", "")
        if args[:3] == ["git", "rev-parse", f"{'b' * 40}^{{tree}}"]:
            return subprocess.CompletedProcess(args, 0, "d" * 40 + "\n", "")
        if args[:3] == ["git", "init", "-q"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        if Path(args[0]).name.startswith("agentic-workspace") and args[1] == "start":
            payload = {
                "decision_packet": {"status": "direct"},
                "runtime_compatibility": {"observed_runtime": {"version": verified["version"]}},
            }
            return subprocess.CompletedProcess(args, 0, json.dumps(payload), "")
        raise AssertionError(args)

    monkeypatch.setattr(module, "_run", run)
    result = module.smoke_published_preview(repo="owner/repo", tag=verified["tag"])

    assert result["status"] == "passed"
    assert result["reconstruction_source_tree"] == "c" * 40
    assert result["artifact_tree"] == "d" * 40
    assert result["install_command"] == readiness["install"]["command"]
    assert result["start"] == {"decision_status": "direct", "runtime_version": "0.52.0"}
    assert any(args[:3] == ["uv", "tool", "install"] for args, _, _ in calls)
    assert any(len(args) > 1 and args[1] == "start" for args, _, _ in calls)


def test_preview_workflow_smokes_public_bytes_after_publication() -> None:
    workflow = (ROOT / ".github" / "workflows" / "preview-release.yml").read_text(encoding="utf-8")

    publish = workflow.index("name: Publish GitHub prerelease assets")
    smoke = workflow.index("name: Smoke published preview from public bytes")
    assert publish < smoke
    assert "scripts/release/preview_public_smoke.py" in workflow[smoke:]
    assert "preview-public-smoke.json" in workflow[smoke:]
