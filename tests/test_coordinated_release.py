from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "tooling" / "release" / "coordinated_release.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("coordinated_release_under_test", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_optional_rc_keeps_first_stable_gate_and_allows_later_releases(monkeypatch) -> None:
    module = _load_module()
    changeset = module.Changeset(path=module.ROOT / ".release/changes/a.toml", bump="major", summary="Feature")
    monkeypatch.setattr(module, "parse_changesets", lambda ownership: [changeset])
    monkeypatch.setattr(module, "existing_release_versions", lambda ownership: [])
    monkeypatch.setattr(module, "current_package_versions", lambda ownership: [module.Version.parse("0.9.0")])
    ownership = {"release_candidate": {}}

    first_stable = module.plan_release(ownership)
    assert first_stable["release_required"] is False
    assert first_stable["reason"] == "first-stable-requires-explicit-accepted-rc"

    monkeypatch.setattr(module, "current_package_versions", lambda ownership: [module.Version.parse("1.0.0")])
    monkeypatch.setattr(
        module,
        "parse_changesets",
        lambda ownership: [module.Changeset(path=changeset.path, bump="minor", summary="Feature")],
    )
    next_release = module.plan_release(ownership)
    assert next_release["release_required"] is True
    assert next_release["tag"] == "v1.1.0"


def test_plan_uses_existing_release_tags_as_floor(monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(
        module,
        "parse_changesets",
        lambda ownership: [module.Changeset(path=module.ROOT / ".release/changes/a.toml", bump="patch", summary="Fix")],
    )
    monkeypatch.setattr(module, "current_package_versions", lambda ownership: [module.Version.parse("0.33.9")])
    monkeypatch.setattr(module, "existing_release_versions", lambda ownership: [module.Version.parse("0.34.0")])

    plan = module.plan_release({})

    assert plan["release_required"] is True
    assert plan["current_floor"] == "0.34.0"
    assert plan["version"] == "0.34.1"
    assert plan["tag"] == "v0.34.1"


def test_plan_applies_highest_pending_changeset_bump(monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(
        module,
        "parse_changesets",
        lambda ownership: [
            module.Changeset(path=module.ROOT / ".release/changes/a.toml", bump="patch", summary="Fix"),
            module.Changeset(path=module.ROOT / ".release/changes/b.toml", bump="minor", summary="Feature"),
        ],
    )
    monkeypatch.setattr(module, "current_package_versions", lambda ownership: [module.Version.parse("1.2.3")])
    monkeypatch.setattr(module, "existing_release_versions", lambda ownership: [module.Version.parse("1.2.3")])

    plan = module.plan_release({})

    assert plan["bump"] == "minor"
    assert plan["version"] == "1.3.0"


def test_prepare_updates_all_version_mirrors_and_consumes_changesets(tmp_path, monkeypatch) -> None:
    module = _load_module()
    root_pyproject = tmp_path / "pyproject.toml"
    package_pyproject = tmp_path / "packages/memory/pyproject.toml"
    package_json = tmp_path / "generated/workspace/typescript/package.json"
    payload_provenance = tmp_path / ".agentic-workspace/payload-provenance.json"
    changeset = tmp_path / ".release/changes/change.toml"
    release_note = tmp_path / ".release/releases/v0.2.0.md"
    package_pyproject.parent.mkdir(parents=True)
    package_json.parent.mkdir(parents=True)
    payload_provenance.parent.mkdir(parents=True)
    changeset.parent.mkdir(parents=True)
    root_pyproject.write_text('[project]\nname = "root"\nversion = "0.1.0"\n', encoding="utf-8")
    package_pyproject.write_text('[project]\nname = "pkg"\nversion = "0.1.0"\n', encoding="utf-8")
    package_json.write_text('{"name":"pkg","version":"0.1.0","private":false}\n', encoding="utf-8")
    payload_provenance.write_text(
        json.dumps(
            {
                **json.loads((ROOT / ".agentic-workspace/payload-provenance.json").read_text(encoding="utf-8")),
                "release_identity": {"package": "agentic-workspace", "version": "0.1.0"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    changeset.write_text(
        'schema_version = "agentic-workspace/release-change/v1"\nbump = "minor"\nsummary = "Feature"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "existing_release_versions", lambda ownership: [module.Version.parse("0.1.0")])
    ownership = {
        "changeset_dir": ".release/changes",
        "packages": [
            {
                "name": "agentic-workspace",
                "pyproject": "pyproject.toml",
                "payload_provenance": ".agentic-workspace/payload-provenance.json",
            },
            {"name": "agentic-workspace-memory", "pyproject": "packages/memory/pyproject.toml"},
        ],
        "typescript_packages": [{"package_json": "generated/workspace/typescript/package.json"}],
    }

    before_provenance = json.loads(payload_provenance.read_text(encoding="utf-8"))
    plan = module.prepare_release(ownership)

    assert plan["version"] == "0.2.0"
    assert plan["release_note"] == ".release/releases/v0.2.0.md"
    assert 'version = "0.2.0"' in root_pyproject.read_text(encoding="utf-8")
    assert 'version = "0.2.0"' in package_pyproject.read_text(encoding="utf-8")
    assert json.loads(package_json.read_text(encoding="utf-8"))["version"] == "0.2.0"
    provenance = json.loads(payload_provenance.read_text(encoding="utf-8"))
    assert "installed_by" not in provenance
    assert provenance["release_identity"] == {"package": "agentic-workspace", "version": "0.2.0"}
    before_provenance["release_identity"]["version"] = "0.2.0"
    assert provenance == before_provenance
    assert module.verify_workspace_versions(ownership)["version"] == "0.2.0"
    import pytest

    for field, value in [("version", "0.1.0"), ("package", "foreign")]:
        changed = json.loads(json.dumps(provenance))
        changed["release_identity"][field] = value
        payload_provenance.write_text(json.dumps(changed), encoding="utf-8")
        with pytest.raises(SystemExit, match="payload"):
            module.verify_workspace_versions(ownership)
    payload_provenance.write_text(json.dumps(provenance), encoding="utf-8")
    assert release_note.read_text(encoding="utf-8").count("Feature") == 1
    assert not changeset.exists()


def test_tag_plan_targets_release_commit_after_unrelated_master_commit(tmp_path, monkeypatch) -> None:
    module = _load_module()
    root_pyproject = tmp_path / "pyproject.toml"
    package_json = tmp_path / "generated/workspace/typescript/package.json"
    release_note = tmp_path / ".release/releases/v0.34.1.md"
    package_json.parent.mkdir(parents=True)
    release_note.parent.mkdir(parents=True)
    ownership = {
        "changeset_dir": ".release/changes",
        "release_notes_dir": ".release/releases",
        "packages": [{"pyproject": "pyproject.toml"}],
        "typescript_packages": [{"package_json": "generated/workspace/typescript/package.json"}],
    }
    monkeypatch.setattr(module, "ROOT", tmp_path)

    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True, text=True).stdout.strip()

    git("init")
    git("config", "user.name", "Test User")
    git("config", "user.email", "test@example.com")
    root_pyproject.write_text('[project]\nname = "root"\nversion = "0.34.0"\n', encoding="utf-8")
    package_json.write_text('{"name":"pkg","version":"0.34.0","private":false}\n', encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "Release v0.34.0")
    git("tag", "v0.34.0")

    root_pyproject.write_text('[project]\nname = "root"\nversion = "0.34.1"\n', encoding="utf-8")
    package_json.write_text('{"name":"pkg","version":"0.34.1","private":false}\n', encoding="utf-8")
    release_note.write_text("# Release v0.34.1\n\n## Changes\n\n- Fix release flow\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "Release v0.34.1")
    release_commit = git("rev-parse", "HEAD")

    (tmp_path / "docs.md").write_text("unrelated\n", encoding="utf-8")
    git("add", "docs.md")
    git("commit", "-m", "Unrelated follow-up")

    plan = module.pending_tag_plan(ownership)

    assert plan["tag_needed"] is True
    assert plan["publish_candidate"] is True
    assert plan["tag"] == "v0.34.1"
    assert plan["release_commit"] == release_commit
    assert plan["release_note"] == ".release/releases/v0.34.1.md"

    git("tag", "-a", "v0.34.1", release_commit, "-m", "Release v0.34.1")

    retry_plan = module.pending_tag_plan(ownership)

    assert retry_plan["tag_needed"] is False
    assert retry_plan["publish_candidate"] is True
    assert retry_plan["reason"] == "tag-already-points-at-release-commit"
    assert retry_plan["tag"] == "v0.34.1"
    assert retry_plan["release_commit"] == release_commit


def test_tag_plan_targets_protected_merge_commit_not_release_side_parent(tmp_path, monkeypatch) -> None:
    module = _load_module()
    root_pyproject = tmp_path / "pyproject.toml"
    package_json = tmp_path / "generated/workspace/typescript/package.json"
    release_note = tmp_path / ".release/releases/v0.34.1.md"
    package_json.parent.mkdir(parents=True)
    ownership = {
        "changeset_dir": ".release/changes",
        "release_notes_dir": ".release/releases",
        "packages": [{"pyproject": "pyproject.toml"}],
        "typescript_packages": [{"package_json": "generated/workspace/typescript/package.json"}],
    }
    monkeypatch.setattr(module, "ROOT", tmp_path)

    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True, text=True).stdout.strip()

    git("init", "-b", "master")
    git("config", "user.name", "Test User")
    git("config", "user.email", "test@example.com")
    root_pyproject.write_text('[project]\nname = "root"\nversion = "0.34.0"\n', encoding="utf-8")
    package_json.write_text('{"name":"pkg","version":"0.34.0","private":false}\n', encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "Release v0.34.0")
    git("tag", "v0.34.0")

    git("switch", "-c", "automation/coordinated-release")
    root_pyproject.write_text('[project]\nname = "root"\nversion = "0.34.1"\n', encoding="utf-8")
    package_json.write_text('{"name":"pkg","version":"0.34.1","private":false}\n', encoding="utf-8")
    release_note.parent.mkdir(parents=True)
    release_note.write_text("# Release v0.34.1\n\n## Changes\n\n- Protected release\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "Prepare v0.34.1")
    side_parent = git("rev-parse", "HEAD")

    git("switch", "master")
    git("merge", "--no-ff", "automation/coordinated-release", "-m", "Merge protected release PR")
    protected_merge = git("rev-parse", "HEAD")
    git("update-ref", "refs/remotes/origin/master", protected_merge)

    plan = module.pending_tag_plan(ownership)

    assert plan["release_commit"] == protected_merge
    assert plan["release_commit"] != side_parent


def test_preview_and_stable_share_transport_but_not_support_admission() -> None:
    workflow = (ROOT / ".github/workflows/release.yml").read_text()
    lifecycle = (ROOT / "src/tooling/release/release_lifecycle.py").read_text()
    assert "release_class:" in workflow
    assert "prerelease: ${{ needs.promotion-admission.outputs.support_bearing != 'true' }}" in workflow
    assert "Preview cannot carry stable support admission" in lifecycle
    assert "release_model(tag, release_class)" in lifecycle
    assert not (ROOT / ".github/workflows/preview-release.yml").exists()


def test_preview_release_helper_defaults_to_freshly_fetched_reconstruction_ref() -> None:
    helper = (ROOT / "src/tooling/release/preview_release.py").read_text(encoding="utf-8")

    assert 'f"{head_ref}:{tracking_ref}"' in helper
    assert "source_commit = _resolve_commit(source_ref or fetched_reconstruction_ref)" in helper
    assert 'default="HEAD"' not in helper
    assert "freshly fetched master head" in helper
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
