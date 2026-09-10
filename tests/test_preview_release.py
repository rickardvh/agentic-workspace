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
    (root / "pyproject.toml").write_text('[project]\nname = "agentic-workspace"\nversion = "0.51.0"\n', encoding="utf-8")
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
    ownership = {
        "preview_release_commit_allowed_paths": [
            "pyproject.toml",
            "packages/memory/pyproject.toml",
            "generated/workspace/typescript/package.json",
            ".agentic-workspace/payload-provenance.json",
            ".release/releases/",
            ".release/previews/",
        ],
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
    (root / ".github").mkdir()
    (root / ".github/release-ownership.json").write_text(json.dumps(ownership), encoding="utf-8")
    return ownership


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


def _load_helper():
    spec = importlib.util.spec_from_file_location("preview_helper_under_test", ROOT / "scripts/release/preview_release.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["coordinated_release"] = _load_module()
    spec.loader.exec_module(module)
    return module


def test_existing_tag_recovery_never_normalizes_or_recreates_tag(monkeypatch):
    helper = _load_helper()
    calls = []
    verified = {"tag": "preview-v0.52.0", "version": "0.52.0", "artifact_commit": "b" * 40, "reconstruction_source_commit": "a" * 40}
    monkeypatch.setattr(helper, "_fetch_reconstruction_ref", lambda **kw: "fetched")
    monkeypatch.setattr(helper, "_resolve_commit", lambda ref: "a" * 40)
    monkeypatch.setattr(helper, "_assert_source_is_reconstruction_candidate", lambda *a, **kw: None)
    monkeypatch.setattr(helper, "_tag_commit", lambda tag: "b" * 40)
    monkeypatch.setattr(helper, "_verify_existing_preview", lambda tag, source: verified)
    monkeypatch.setattr(helper, "_recover_publisher", lambda **kw: {"publication_status": "publisher-rerun-requested"})

    def git(*args, **kw):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "remote-tag", "")

    monkeypatch.setattr(helper, "_git", git)
    result = helper.create_preview_subject(
        version="0.52.0", source_ref="a" * 40, remote="origin", reconstruction_ref="reconstruct/first-stable", push=True
    )
    assert result["artifact_commit"] == "b" * 40
    assert result["publication_status"] == "publisher-rerun-requested"
    assert calls == [("ls-remote", "--refs", "origin", "refs/tags/preview-v0.52.0"), ("push", "origin", "refs/tags/preview-v0.52.0")]


def test_recovery_selects_only_exact_failed_or_cancelled_push_run(monkeypatch):
    import pytest

    helper = _load_helper()
    artifact = "b" * 40
    verified = {"tag": "preview-v0.52.0", "artifact_commit": artifact}
    run = {
        "id": 21,
        "head_sha": artifact,
        "head_branch": verified["tag"],
        "event": "push",
        "path": ".github/workflows/preview-release.yml",
        "repository": {"full_name": "owner/repo"},
        "status": "completed",
        "conclusion": "failure",
    }
    monkeypatch.setattr(helper, "verify_published_preview", lambda **kw: False)
    monkeypatch.setattr(
        helper,
        "_git",
        lambda *a, **kw: subprocess.CompletedProcess(
            a, 0, f"{artifact}\trefs/tags/preview-v0.52.0\n" if a[0] == "ls-remote" else "https://github.com/owner/repo", ""
        ),
    )
    calls = []

    def command(args, **kw):
        calls.append(args)
        output = "owner/repo" if args[1] == "repo" else json.dumps({"workflow_runs": [run]})
        return subprocess.CompletedProcess(args, 0, output, "")

    monkeypatch.setattr(helper, "_run", command)
    for conclusion in ("failure", "cancelled"):
        run["conclusion"] = conclusion
        assert helper._recover_publisher(remote="origin", verified=verified)["publication_status"] == "publisher-rerun-requested"
        assert calls[-1] == ["gh", "api", "--method", "POST", "repos/owner/repo/actions/runs/21/rerun"]
    for key, bad in (
        ("head_sha", "c" * 40),
        ("head_branch", "another-tag"),
        ("event", "workflow_dispatch"),
        ("path", ".github/workflows/release.yml"),
        ("repository", {"full_name": "fork/repo"}),
    ):
        original = run[key]
        run[key] = bad
        calls.clear()
        with pytest.raises(SystemExit, match="No exact tag-push"):
            helper._recover_publisher(remote="origin", verified=verified)
        assert not any("POST" in call for call in calls)
        run[key] = original
    for conclusion in ("success", "skipped", "timed_out"):
        run["conclusion"] = conclusion
        calls.clear()
        with pytest.raises(SystemExit):
            helper._recover_publisher(remote="origin", verified=verified)
        assert not any("POST" in call for call in calls)


def test_preview_rejects_forged_delta_and_subjects(tmp_path, monkeypatch):
    import pytest

    module = _load_module()
    ownership = _fixture(tmp_path)
    _git(tmp_path, "init", "-b", "reconstruct/first-stable")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "source")
    source = _git(tmp_path, "rev-parse", "HEAD")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    module.prepare_preview_release(ownership, tag="preview-v0.52.0", source_commit=source)
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "preview")
    _git(tmp_path, "tag", "preview-v0.52.0")
    with pytest.raises(SystemExit, match="metadata mismatch"):
        module.verify_preview_release(ownership, tag="preview-v0.52.0", source_commit="c" * 40)
    with pytest.raises(SystemExit, match="Release tag"):
        module.verify_workspace_versions(ownership, tag="preview-v0.52.0")
    original = (tmp_path / "pyproject.toml").read_text()
    (tmp_path / "pyproject.toml").write_text(original.replace("agentic-workspace", "forged-package"))
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "--amend", "--no-edit")
    _git(tmp_path, "tag", "-f", "preview-v0.52.0")  # Adversarial fixture only.
    with pytest.raises(SystemExit, match="non-version package metadata"):
        module.verify_preview_release(ownership, tag="preview-v0.52.0")
    (tmp_path / "pyproject.toml").write_text(original)
    (tmp_path / "publisher.py").write_text("forged")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "--amend", "--no-edit")
    _git(tmp_path, "tag", "-f", "preview-v0.52.0")
    with pytest.raises(SystemExit, match="non-release-only"):
        module.verify_preview_release(ownership, tag="preview-v0.52.0")


def test_built_preview_root_urls_digests_and_external_install(tmp_path):
    import hashlib
    import os
    import shutil

    import pytest
    from tests.test_workspace_packaging import (
        _assert_workspace_stack_runs_fresh_repo_cli_sequence,
        _install_workspace_root_release_venv,
        _load_release_wheel_patcher,
        _venv_site_package_entry_names,
    )

    artifact_dir = os.environ.get("AW_PREVIEW_ARTIFACT_DIR")
    if not artifact_dir:
        pytest.skip("requires the normalized preview artifact fixture or publisher dist")
    dist = Path(artifact_dir).resolve()
    spec = importlib.util.spec_from_file_location("preview_manifest_test", ROOT / "scripts/release/preview_manifest.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["coordinated_release"] = _load_module()
    spec.loader.exec_module(module)
    ownership = json.loads((ROOT / ".github/release-ownership.json").read_text())
    wheels = sorted(dist.glob("*.whl"))
    root = next(path for path in wheels if path.name.startswith("agentic_workspace-"))
    version = root.name.split("-")[1]
    requirements = module.verify_preview_dependencies(ownership=ownership, dist=dist, version=version)
    assert len(requirements) == len(ownership["packages"]) - 1
    original_digests = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in wheels}
    local_assets = tmp_path / "preview-assets"
    local_assets.mkdir()
    for path in wheels:
        shutil.copy2(path, local_assets / path.name)
    # Transport substitution only: production URLs and hashes were checked above.
    # The install resolves all coordinated wheels from a local immutable mirror.
    patched = _load_release_wheel_patcher().patch_workspace_wheel(
        dist_dir=local_assets, version=version, release_asset_base_url=local_assets.as_uri()
    )
    exe = _install_workspace_root_release_venv(root_wheel=patched, tmpdir_path=tmp_path)
    for name in ("agentic_workspace_memory", "agentic_workspace_planning", "agentic_workspace_verification"):
        assert _venv_site_package_entry_names(tmp_path / ".venv-release", name)
    _assert_workspace_stack_runs_fresh_repo_cli_sequence(workspace_exe=exe, tmp_path=tmp_path)
    assert original_digests == {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in wheels}


def test_existing_release_assets_are_idempotent_and_mismatches_fail_closed(tmp_path, monkeypatch):
    import hashlib

    import pytest

    helper = _load_helper()
    ownership = json.loads((ROOT / ".github/release-ownership.json").read_text())
    verified = {"tag": "preview-v0.52.0", "version": "0.52.0", "artifact_commit": "b" * 40, "reconstruction_source_commit": "a" * 40}
    manifest = {**verified, "release_class": "preview", "support_bearing": False, "packages": [], "semantic_conformance": {"receipts": []}}
    assets = {}
    for package in ownership["packages"] + ownership["typescript_packages"]:
        entry = {"name": package["name"], "version": "0.52.0"}
        for key in ("wheel", "sdist") if "pyproject" in package else ("tarball",):
            name = package["name"].replace("/", "-") + "." + key
            assets[name] = name.encode()
            entry[key] = {"asset": name, "sha256": hashlib.sha256(assets[name]).hexdigest()}
        manifest["packages"].append(entry)
    for major in ownership["semantic_conformance"]["runtime_majors"]:
        name = f"generated-command-conformance-node{major}.json"
        assets[name] = b"receipt"
        manifest["semantic_conformance"]["receipts"].append({"asset": name})
    for name in (
        "distribution-install-readiness.json",
        "redistributable-package-readiness.json",
        "security-supply-chain-readiness.json",
        "agentic-workspace.spdx.json",
    ):
        assets[name] = b"proof"
    manifest_name = "agentic-workspace-preview-release-manifest.json"
    assets[manifest_name] = json.dumps(manifest).encode()
    assets["SHA256SUMS"] = "".join(f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(assets.items())).encode()
    release = {"tag_name": verified["tag"], "prerelease": True, "draft": False, "assets": [{"name": name} for name in assets]}

    def command(args, **kw):
        if args[1] == "api":
            return subprocess.CompletedProcess(args, 0, json.dumps(release), "")
        directory = Path(args[args.index("--dir") + 1])
        for name, data in assets.items():
            (directory / name).write_bytes(data)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(helper, "_run", command)
    assert helper.verify_published_preview(repo="owner/repo", verified=verified)
    bad = {**verified, "artifact_commit": "c" * 40}
    with pytest.raises(SystemExit, match="exact source/artifact"):
        helper.verify_published_preview(repo="owner/repo", verified=bad)
    for name, data in assets.items():
        (tmp_path / name).write_bytes(data)
    assert helper.verify_published_preview(repo="owner/repo", verified=verified, artifact_dir=tmp_path)
    (tmp_path / "agentic-workspace.spdx.json").write_bytes(b"changed")
    with pytest.raises(SystemExit, match="refusing overwrite"):
        helper.verify_published_preview(repo="owner/repo", verified=verified, artifact_dir=tmp_path)
    assets["agentic-workspace.spdx.json"] = b"forged"
    with pytest.raises(SystemExit, match="checksum mismatch"):
        helper.verify_published_preview(repo="owner/repo", verified=verified)
    del assets["agentic-workspace.spdx.json"]
    assert not helper.verify_published_preview(repo="owner/repo", verified=verified)
