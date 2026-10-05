from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "tooling" / "release" / "coordinated_release.py"


def test_completed_source_consumes_revisions_and_staging_rejects_other_changes(tmp_path, monkeypatch):
    release = _load_module()
    monkeypatch.setattr(release, "ROOT", tmp_path)

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()

    def save(path, text):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")

    def commit():
        git("add", ".")
        git("commit", "-qm", "fixture")
        return git("rev-parse", "HEAD")

    def fragment(path, bump):
        save(".release/changes/" + path + ".toml", f'schema_version = "{release.CHANGESET_SCHEMA}"\nbump = "{bump}"\nsummary = "{path}"\n')

    git("init", "-q")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    git("config", "core.autocrlf", "false")
    ownership = {
        "packages": [{"name": "agentic-workspace", "pyproject": "pyproject.toml", "payload_provenance": "payload.json"}],
        "typescript_packages": [{"package_json": "package.json"}],
        "cargo_packages": [{"name": "agentic-workspace-core", "path": "core"}],
        "cargo_lockfiles": ["Cargo.lock"],
    }
    save("pyproject.toml", '[project]\nname = "agentic-workspace"\nversion = "0.0.0.dev0"\n')
    save("package.json", '{"name":"test", "version":"0.0.0-dev.0"}\n')
    save("core/Cargo.toml", '[package]\nname = "agentic-workspace-core"\nversion = "0.0.0-dev.0"\n')
    save(
        "Cargo.lock",
        'version = 4\n\n[[package]]\nname = "agentic-workspace-core"\nversion = "0.0.0-dev.0"\n\n[[package]]\nname = "third-party"\nversion = "2.0.0"\nsource = "registry"\nchecksum = "original"\n',
    )
    save("uv.lock", 'version = 1\n\n[[package]]\nname = "agentic-workspace"\nversion = "0.0.0.dev0"\nsource = { editable = "." }\n')
    save(
        "payload.json",
        json.dumps(
            {
                "kind": "agentic-workspace/payload-provenance/v1",
                "payload_schema": "agentic-workspace/payload/v1",
                "release_identity": {"package": "agentic-workspace", "version": "0.0.0.dev0"},
                "payload_files": ["core/Cargo.toml"],
                "payload_capabilities": ["test"],
            }
        ),
    )
    save("code.py", "original = True\n")
    fragment("consumed", "major")
    boundary = commit()
    completed = {"source_commit": boundary, "tag": "v1.6.0", "version": "1.6.0"}
    fragment("fix", "patch")
    fragment("feature", "minor")
    source = commit()
    plan = release.select_release(ownership, source=source, completed=completed, reserved=["1.6.0", "1.7.0"], partial=[])
    assert plan["tag"] == "v1.8.0"
    assert {item["path"] for item in plan["changesets"]} == {".release/changes/fix.toml", ".release/changes/feature.toml"}
    stamped = release.stamp_release(ownership, plan)
    assert release.stamp_release(ownership, stamped, verify=True) == stamped
    assert all(len(item["sha256"]) == 64 for item in stamped["transform"])
    assert "0.0.0.dev0" not in (tmp_path / "uv.lock").read_text()
    assert 'version = "2.0.0"' in (tmp_path / "Cargo.lock").read_text()
    save("untracked-code.py", "injected = True\n")
    with pytest.raises(ValueError, match="untracked staging input"):
        release.stamp_release(ownership, stamped, verify=True)
    (tmp_path / "untracked-code.py").unlink()
    save("code.py", "original = False\n")
    with pytest.raises(ValueError, match="Unauthorised staging"):
        release.stamp_release(ownership, stamped, verify=True)
    git("restore", "code.py")
    save("Cargo.lock", (tmp_path / "Cargo.lock").read_text().replace('checksum = "original"', 'checksum = "replacement"'))
    with pytest.raises(ValueError, match="staged content"):
        release.stamp_release(ownership, stamped, verify=True)
    git("restore", ".")
    # Release tags refer to the unchanged development source, never a version commit.
    completed = {"source_commit": source, "tag": plan["tag"], "version": plan["version"]}
    assert not release.select_release(ownership, source=source, completed=completed, reserved=[], partial=[])["release_required"]
    git("mv", ".release/changes/feature.toml", ".release/changes/renamed.toml")
    git("rm", ".release/changes/consumed.toml")
    cleanup = commit()
    assert not release.select_release(ownership, source=cleanup, completed=completed, reserved=[], partial=[])["release_required"]
    fragment("fix", "patch")
    save(".release/changes/fix.toml", (tmp_path / ".release/changes/fix.toml").read_text().replace('"fix"', '"new fix"'))
    second = commit()
    next_plan = release.select_release(ownership, source=second, completed=completed, reserved=[], partial=[])
    assert next_plan["tag"] == "v1.8.1"
    assert len(next_plan["changesets"]) == 1
    with pytest.raises(ValueError, match="recovery"):
        release.select_release(ownership, source=second, completed=completed, reserved=["1.8.1"], partial=["v1.8.1"])
    with pytest.raises(subprocess.CalledProcessError):
        release.select_release(ownership, source=boundary, completed=completed, reserved=[], partial=[])
    # Branch movement cannot stamp a newly selected subject under the old plan.
    with pytest.raises(ValueError, match="pinned"):
        release.stamp_release(ownership, plan)
    git("checkout", "--detach", source)
    corrupted = {**plan, "version": "1.9.0"}
    with pytest.raises(ValueError, match="conflicts"):
        release.stamp_release(ownership, corrupted)


def test_reviewed_version_line_correction_consumes_withdrawn_source_without_reusing_versions(tmp_path, monkeypatch):
    release = _load_module()
    monkeypatch.setattr(release, "ROOT", tmp_path)

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()

    def commit():
        git("add", ".")
        git("commit", "-qm", "fixture")
        return git("rev-parse", "HEAD")

    def fragment(name, bump):
        (tmp_path / f".release/changes/{name}.toml").write_text(
            f'schema_version = "{release.CHANGESET_SCHEMA}"\nbump = "{bump}"\nsummary = "{name}"\n'
        )

    git("init", "-q")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    (tmp_path / ".release/changes").mkdir(parents=True)
    fragment("previous", "patch")
    previous = commit()
    fragment("historical-major", "major")
    withdrawn = commit()
    record = {
        "kind": "agentic-workspace/version-line-correction/v1",
        "previous": {"tag": "v1.10.2", "version": "1.10.2", "source_commit": previous},
        "withdrawn": {"tag": "v2.0.0", "version": "2.0.0", "source_commit": withdrawn},
        "replacement": "1.11.0",
        "reason": "Reviewed repository-owner correction",
    }
    (tmp_path / release.CORRECTION_PATH).write_text(json.dumps(record))
    fragment("policy", "minor")
    source = commit()
    completed = {**record["withdrawn"], "version_line_correction": record}
    plan = release.select_release({}, source=source, completed=completed, reserved=["1.10.2", "2.0.0"], partial=[])
    assert plan["tag"] == "v1.11.0"
    assert plan["boundary"] == {"tag": "v2.0.0", "source_commit": withdrawn}
    assert [r["path"] for r in plan["changesets"]] == [".release/changes/policy.toml"]
    with pytest.raises(ValueError, match="remote admission"):
        release.select_release({}, source=source, completed=record["withdrawn"], reserved=[], partial=[])
    with pytest.raises(ValueError, match="recovery"):
        release.select_release({}, source=source, completed=completed, reserved=["1.11.0", "2.0.0"], partial=["v1.11.0"])
    with pytest.raises(ValueError, match="differs from reviewed"):
        release.select_release({}, source=source, completed=completed, reserved=["1.11.0", "2.0.0"], partial=[])
    completed = {"source_commit": source, "tag": "v1.11.0", "version": "1.11.0", "version_line_correction": record}
    fragment("later-fix", "patch")
    later = commit()
    assert release.select_release({}, source=later, completed=completed, reserved=["1.11.0", "2.0.0"], partial=[])["tag"] == "v1.11.1"
    fragment("real-break", "major")
    later = commit()
    assert release.select_release({}, source=later, completed=completed, reserved=["1.11.0", "2.0.0"], partial=[])["tag"] == "v3.0.0"
    record = json.loads(json.dumps(record))
    record["withdrawn"]["source_commit"] = source
    (tmp_path / release.CORRECTION_PATH).write_text(json.dumps(record))
    altered = commit()
    with pytest.raises(ValueError, match="remote admission"):
        release.select_release({}, source=altered, completed=completed, reserved=[], partial=[])


def _load_module():
    spec = importlib.util.spec_from_file_location("coordinated_release_under_test", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_preview_release_helper_defaults_to_freshly_fetched_reconstruction_ref() -> None:
    helper = (ROOT / "src/tooling/release/preview_release.py").read_text(encoding="utf-8")

    assert 'f"{head_ref}:{tracking_ref}"' in helper
    assert "source_commit = _resolve_commit(source_ref or fetched_reconstruction_ref)" in helper
    assert 'default="HEAD"' not in helper
    assert '"merge-base", "--is-ancestor", source_commit, remote_ref' in helper


def test_native_npm_source_uses_canonical_version_without_a_mirror(tmp_path, monkeypatch):
    module = _load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    (tmp_path / "pyproject.toml").write_text('[project]\nname="agentic-workspace"\nversion = "1.2.0"\n')
    binding = tmp_path / "package.json"
    binding.write_text('{"name":"@agentic-workspace/workspace-cli","private":true}\n')
    original = binding.read_bytes()
    ownership = {
        "packages": [{"name": "agentic-workspace", "pyproject": "pyproject.toml"}],
        "typescript_packages": [{"package_json": "package.json"}],
    }
    assert module.current_workspace_version(ownership) == "1.2.0"
    module.set_workspace_version(ownership, "1.2.1")
    assert module.current_workspace_version(ownership) == "1.2.1"
    assert binding.read_bytes() == original
