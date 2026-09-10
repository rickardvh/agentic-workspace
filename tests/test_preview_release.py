from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "release" / "coordinated_release.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("coordinated_preview_under_test", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()


def _fixture(root: Path) -> dict[str, object]:
    (root / "packages/memory").mkdir(parents=True)
    (root / "generated/workspace/typescript").mkdir(parents=True)
    (root / ".agentic-workspace").mkdir(parents=True)
    (root / ".release/changes").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "agentic-workspace"\nversion = "0.51.0"\n', encoding="utf-8"
    )
    (root / "packages/memory/pyproject.toml").write_text(
        '[project]\nname = "agentic-workspace-memory"\nversion = "0.51.0"\n', encoding="utf-8"
    )
    (root / "generated/workspace/typescript/package.json").write_text(
        json.dumps({"name": "@agentic-workspace/workspace-cli", "version": "0.51.0", "private": True}) + "\n",
        encoding="utf-8",
    )
    (root / ".agentic-workspace/payload-provenance.json").write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/payload-provenance/v1",
                "installed_by": {"version": "0.51.0"},
                "release_identity": {"version": "0.51.0", "tag": "v0.51.0"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (root / ".release/changes/pending.toml").write_text(
        'schema_version = "agentic-workspace/release-change/v1"\nbump = "patch"\nsummary = "Pending product change"\n',
        encoding="utf-8",
    )
    return {
        "changeset_dir": ".release/changes",
        "release_notes_dir": ".release/releases",
        "preview_metadata_dir": ".release/previews",
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


def test_prepare_preview_normalizes_detached_subject_without_consuming_changesets(tmp_path, monkeypatch) -> None:
    module = _load_module()
    ownership = _fixture(tmp_path)
    _git(tmp_path, "init", "-b", "reconstruct/first-stable")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "source")
    source_commit = _git(tmp_path, "rev-parse", "HEAD")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "existing_release_versions", lambda _ownership: [module.Version.parse("0.51.0")])

    result = module.prepare_preview_release(
        ownership,
        tag="preview-v0.52.0",
        source_commit=source_commit,
    )

    assert result["release_class"] == "preview"
    assert result["support_bearing"] is False
    assert result["preserved_changesets"] == [".release/changes/pending.toml"]
    assert (tmp_path / ".release/changes/pending.toml").is_file()
    assert 'version = "0.52.0"' in (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.52.0"' in (tmp_path / "packages/memory/pyproject.toml").read_text(encoding="utf-8")
    assert json.loads((tmp_path / "generated/workspace/typescript/package.json").read_text(encoding="utf-8"))["version"] == "0.52.0"
    provenance = json.loads((tmp_path / ".agentic-workspace/payload-provenance.json").read_text(encoding="utf-8"))
    assert provenance["release_identity"] == {"version": "0.52.0", "tag": "preview-v0.52.0"}
    metadata = json.loads((tmp_path / ".release/previews/preview-v0.52.0.json").read_text(encoding="utf-8"))
    assert metadata == {
        "kind": "agentic-workspace/coordinated-preview-subject/v1",
        "reconstruction_source_commit": source_commit,
        "release_class": "preview",
        "support_bearing": False,
        "tag": "preview-v0.52.0",
        "version": "0.52.0",
    }
    note = (tmp_path / ".release/releases/preview-v0.52.0.md").read_text(encoding="utf-8")
    assert "Non-support-bearing preview" in note
    assert source_commit in note


def test_preview_tag_versions_raise_the_later_stable_version_floor(tmp_path, monkeypatch) -> None:
    module = _load_module()
    ownership = _fixture(tmp_path)
    _git(tmp_path, "init", "-b", "reconstruct/first-stable")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "v0.51 source")
    source_commit = _git(tmp_path, "rev-parse", "HEAD")
    _git(tmp_path, "tag", "v0.51.0")

    _git(tmp_path, "switch", "--detach", source_commit)
    for path in (tmp_path / "pyproject.toml", tmp_path / "packages/memory/pyproject.toml"):
        path.write_text(path.read_text(encoding="utf-8").replace('version = "0.51.0"', 'version = "0.52.0"'), encoding="utf-8")
    package_json = tmp_path / "generated/workspace/typescript/package.json"
    payload = json.loads(package_json.read_text(encoding="utf-8"))
    payload["version"] = "0.52.0"
    package_json.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    _git(tmp_path, "add", "pyproject.toml", "packages/memory/pyproject.toml", "generated/workspace/typescript/package.json")
    _git(tmp_path, "commit", "-m", "preview v0.52.0")
    _git(tmp_path, "tag", "preview-v0.52.0")
    _git(tmp_path, "switch", "reconstruct/first-stable")

    monkeypatch.setattr(module, "ROOT", tmp_path)
    assert sorted(str(version) for version in module.existing_release_versions(ownership)) == ["0.51.0", "0.52.0"]

    plan = module.plan_release(ownership)

    assert plan["current_floor"] == "0.52.0"
    assert plan["version"] == "0.52.1"
    assert plan["tag"] == "v0.52.1"


def test_verify_preview_binds_tagged_artifact_commit_to_exact_source_parent(tmp_path, monkeypatch) -> None:
    module = _load_module()
    ownership = _fixture(tmp_path)
    _git(tmp_path, "init", "-b", "reconstruct/first-stable")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "source")
    source_commit = _git(tmp_path, "rev-parse", "HEAD")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "existing_release_versions", lambda _ownership: [module.Version.parse("0.51.0")])
    module.prepare_preview_release(ownership, tag="preview-v0.52.0", source_commit=source_commit)
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "Preview v0.52.0")
    artifact_commit = _git(tmp_path, "rev-parse", "HEAD")
    _git(tmp_path, "tag", "preview-v0.52.0")

    result = module.verify_preview_release(ownership, tag="preview-v0.52.0", source_commit=source_commit)

    assert result["artifact_commit"] == artifact_commit
    assert result["reconstruction_source_commit"] == source_commit
    assert result["support_bearing"] is False


def test_preview_preparation_rejects_stable_tag(tmp_path, monkeypatch) -> None:
    module = _load_module()
    ownership = _fixture(tmp_path)
    _git(tmp_path, "init", "-b", "reconstruct/first-stable")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "source")
    source_commit = _git(tmp_path, "rev-parse", "HEAD")
    monkeypatch.setattr(module, "ROOT", tmp_path)

    try:
        module.prepare_preview_release(ownership, tag="v0.52.0", source_commit=source_commit)
    except SystemExit as exc:
        assert "Preview preparation requires" in str(exc)
    else:
        raise AssertionError("stable tag must not enter preview preparation")
