from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "release" / "coordinated_release.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("coordinated_release_under_test", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_plan_uses_existing_release_tags_as_floor(monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(
        module,
        "parse_changesets",
        lambda ownership: [module.Changeset(path=module.ROOT / ".release/changes/a.toml", bump="patch", summary="Fix")],
    )
    monkeypatch.setattr(module, "current_package_versions", lambda ownership: [module.Version.parse("0.33.9")])
    monkeypatch.setattr(module, "existing_release_versions", lambda: [module.Version.parse("0.34.0")])

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
    monkeypatch.setattr(module, "existing_release_versions", lambda: [module.Version.parse("1.2.3")])

    plan = module.plan_release({})

    assert plan["bump"] == "minor"
    assert plan["version"] == "1.3.0"


def test_prepare_updates_all_version_mirrors_and_consumes_changesets(tmp_path, monkeypatch) -> None:
    module = _load_module()
    root_pyproject = tmp_path / "pyproject.toml"
    package_pyproject = tmp_path / "packages/memory/pyproject.toml"
    package_json = tmp_path / "generated/workspace/typescript/package.json"
    changeset = tmp_path / ".release/changes/change.toml"
    release_note = tmp_path / ".release/releases/v0.2.0.md"
    package_pyproject.parent.mkdir(parents=True)
    package_json.parent.mkdir(parents=True)
    changeset.parent.mkdir(parents=True)
    root_pyproject.write_text('[project]\nname = "root"\nversion = "0.1.0"\n', encoding="utf-8")
    package_pyproject.write_text('[project]\nname = "pkg"\nversion = "0.1.0"\n', encoding="utf-8")
    package_json.write_text('{"name":"pkg","version":"0.1.0","private":false}\n', encoding="utf-8")
    changeset.write_text(
        'schema_version = "agentic-workspace/release-change/v1"\nbump = "minor"\nsummary = "Feature"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "existing_release_versions", lambda: [module.Version.parse("0.1.0")])
    ownership = {
        "changeset_dir": ".release/changes",
        "packages": [{"pyproject": "pyproject.toml"}, {"pyproject": "packages/memory/pyproject.toml"}],
        "typescript_packages": [{"package_json": "generated/workspace/typescript/package.json"}],
    }

    plan = module.prepare_release(ownership)

    assert plan["version"] == "0.2.0"
    assert plan["release_note"] == ".release/releases/v0.2.0.md"
    assert 'version = "0.2.0"' in root_pyproject.read_text(encoding="utf-8")
    assert 'version = "0.2.0"' in package_pyproject.read_text(encoding="utf-8")
    assert json.loads(package_json.read_text(encoding="utf-8"))["version"] == "0.2.0"
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
