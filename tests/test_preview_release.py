from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from tests.test_native_public_cli import native_cli as native_cli

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
                **json.loads((ROOT / ".agentic-workspace/payload-provenance.json").read_text(encoding="utf-8")),
                "release_identity": {"package": "agentic-workspace", "version": "0.51.0"},
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
    _git(tmp_path, "init", "-b", "master")
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
    assert provenance["release_identity"] == {"package": "agentic-workspace", "version": "0.52.0"}
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
    _git(tmp_path, "init", "-b", "master")
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
    _git(tmp_path, "switch", "master")

    monkeypatch.setattr(module, "ROOT", tmp_path)
    assert sorted(str(version) for version in module.existing_release_versions(ownership)) == ["0.51.0", "0.52.0"]

    plan = module.plan_release(ownership)

    assert plan["current_floor"] == "0.52.0"
    assert plan["version"] == "0.52.1"
    assert plan["tag"] == "v0.52.1"


def test_verify_preview_binds_tagged_artifact_commit_to_exact_source_parent(tmp_path, monkeypatch) -> None:
    module = _load_module()
    ownership = _fixture(tmp_path)
    _git(tmp_path, "init", "-b", "master")
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
    _git(tmp_path, "branch", "preview-v0.52.0")
    import pytest

    with pytest.raises(SystemExit, match="must resolve to exact artifact commit"):
        module.verify_preview_release(ownership, tag="preview-v0.52.0", source_commit=source_commit)
    _git(tmp_path, "tag", "preview-v0.52.0")

    result = module.verify_preview_release(ownership, tag="preview-v0.52.0", source_commit=source_commit)

    assert result["artifact_commit"] == artifact_commit
    assert result["reconstruction_source_commit"] == source_commit
    assert result["support_bearing"] is False


def test_preview_preparation_rejects_stable_tag(tmp_path, monkeypatch) -> None:
    module = _load_module()
    ownership = _fixture(tmp_path)
    _git(tmp_path, "init", "-b", "master")
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
    import pytest

    helper = _load_helper()
    calls = []
    verified = {"tag": "preview-v0.52.0", "version": "0.52.0", "artifact_commit": "b" * 40, "reconstruction_source_commit": "a" * 40}
    monkeypatch.setattr(helper, "_fetch_reconstruction_ref", lambda **kw: "fetched")
    monkeypatch.setattr(helper, "_resolve_commit", lambda ref: "a" * 40)
    monkeypatch.setattr(helper, "_assert_source_is_reconstruction_candidate", lambda *a, **kw: None)
    monkeypatch.setattr(helper, "_tag_commit", lambda tag: "b" * 40)
    monkeypatch.setattr(helper, "_verify_existing_preview", lambda tag, source: verified)
    monkeypatch.setattr(helper, "_recover_publisher", lambda **kw: {"publication_status": "publisher-dispatch-requested"})

    def git(*args, **kw):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "remote-tag", "")

    monkeypatch.setattr(helper, "_git", git)
    result = helper.create_preview_subject(version="0.52.0", source_ref="a" * 40, remote="origin", reconstruction_ref="master", push=True)
    assert result["artifact_commit"] == "b" * 40
    assert result["publication_status"] == "publisher-dispatch-requested"
    assert calls == [("push", "origin", "refs/tags/preview-v0.52.0")]
    calls.clear()
    for branch in ("reconstruct/first-stable", "candidate-branch"):
        with pytest.raises(SystemExit, match="trusted master"):
            helper.create_preview_subject(version="0.52.0", source_ref="a" * 40, remote="origin", reconstruction_ref=branch, push=True)
        assert calls == []


def test_recovery_dispatches_trusted_branch_with_exact_immutable_subject(monkeypatch):
    import pytest

    helper = _load_helper()
    artifact = "b" * 40
    verified = {"tag": "preview-v0.52.0", "artifact_commit": artifact}
    complete = False
    remote_artifact = artifact
    monkeypatch.setattr(helper, "verify_published_preview", lambda **kw: complete)
    monkeypatch.setattr(
        helper,
        "_git",
        lambda *a, **kw: subprocess.CompletedProcess(
            a, 0, f"{remote_artifact}\trefs/tags/preview-v0.52.0\n" if a[0] == "ls-remote" else "https://github.com/owner/repo", ""
        ),
    )
    calls = []

    def command(args, **kw):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "owner/repo" if args[1] == "repo" else "", "")

    monkeypatch.setattr(helper, "_run", command)
    assert helper._recover_publisher(remote="origin", verified=verified)["publication_status"] == "publisher-dispatch-requested"
    assert calls[-1] == [
        "gh",
        "workflow",
        "run",
        "preview-release.yml",
        "--repo",
        "owner/repo",
        "--ref",
        "master",
        "-f",
        "preview_tag=preview-v0.52.0",
        "-f",
        f"artifact_commit={artifact}",
    ]
    # A changed remote subject must not receive a substitute dispatch.
    remote_artifact = "c" * 40
    calls.clear()
    with pytest.raises(SystemExit, match="Remote preview tag"):
        helper._recover_publisher(remote="origin", verified=verified)
    assert not any("workflow" in call for call in calls)
    complete = True
    calls.clear()
    assert helper._recover_publisher(remote="origin", verified=verified)["publication_status"] == "publisher-complete"
    assert not any("workflow" in call for call in calls)


def test_trusted_admission_never_executes_forged_tag_authority(tmp_path, monkeypatch):
    import pytest

    helper = _load_helper()
    module = helper.coordinated_release
    repo = tmp_path / "repo"
    repo.mkdir()
    ownership = _fixture(repo)
    _git(repo, "init", "-b", "master")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "source")
    source = _git(repo, "rev-parse", "HEAD")
    monkeypatch.setattr(module, "ROOT", repo)
    _git(repo, "switch", "--detach", source)
    module.prepare_preview_release(ownership, tag="preview-v0.52.0", source_commit=source)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "preview")
    artifact = _git(repo, "rev-parse", "HEAD")
    _git(repo, "tag", "preview-v0.52.0")
    _git(repo, "switch", "master")
    remote = tmp_path / "remote.git"
    _git(repo, "clone", "--bare", str(repo), str(remote))
    _git(repo, "remote", "add", "origin", str(remote))

    def git(*args, cwd=repo, check=True):
        return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True)

    monkeypatch.setattr(helper, "_git", git)
    assert helper.admit_preview_subject(tag="preview-v0.52.0", artifact_commit=artifact)["artifact_commit"] == artifact
    with pytest.raises(SystemExit, match="requested artifact"):
        helper.admit_preview_subject(tag="preview-v0.52.0", artifact_commit="f" * 40)
    for invalid in ("HEAD", "-bad", artifact + "\ntag=forged"):
        with pytest.raises(SystemExit, match="exact artifact commit SHA"):
            helper.admit_preview_subject(tag="preview-v0.52.0", artifact_commit=invalid)
    for tag in ("v0.52.0", "preview-v0.052.0", "preview-v0.52.0\ntag=forged"):
        with pytest.raises((SystemExit, ValueError)):
            helper.admit_preview_subject(tag=tag, artifact_commit=artifact)

    # The tag contains a replacement verifier AND workflow. Neither gets to
    # decide admission: the invoking helper checks their delta as inert data.
    _git(repo, "switch", "--detach", artifact)
    sentinel = tmp_path / "executed"
    verifier = repo / "scripts/release/coordinated_release.py"
    verifier.parent.mkdir(parents=True, exist_ok=True)
    verifier.write_text(f"from pathlib import Path\nPath({str(sentinel)!r}).touch()\n")
    workflow = repo / ".github/workflows/preview-release.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text("on: [push]\npermissions: write-all\njobs: {}\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "--amend", "--no-edit")
    forged = _git(repo, "rev-parse", "HEAD")
    _git(repo, "tag", "preview-v0.52.0-forged", forged)
    # Adversarial fixture replaces its tag, never production recovery code.
    _git(repo, "tag", "-f", "preview-v0.52.0", forged)
    _git(repo, "push", "--force", "origin", "refs/tags/preview-v0.52.0")
    _git(repo, "switch", "master")
    with pytest.raises(SystemExit, match="non-release-only"):
        helper.admit_preview_subject(tag="preview-v0.52.0", artifact_commit=forged)
    assert not sentinel.exists()


def test_preview_rejects_forged_delta_and_subjects(tmp_path, monkeypatch):
    import pytest

    module = _load_module()
    ownership = _fixture(tmp_path)
    _git(tmp_path, "init", "-b", "master")
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
    provenance_path = tmp_path / ".agentic-workspace/payload-provenance.json"
    original_provenance = provenance_path.read_text(encoding="utf-8")
    for field, value in [("version", "0.51.0"), ("package", "foreign"), ("tag", "preview-v0.52.0")]:
        changed = json.loads(original_provenance)
        changed["release_identity"][field] = value
        provenance_path.write_text(json.dumps(changed), encoding="utf-8")
        with pytest.raises(SystemExit, match="payload"):
            module.verify_preview_release(ownership, tag="preview-v0.52.0", source_commit=source)
    provenance_path.write_text(original_provenance, encoding="utf-8")
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


# Exact preview installation is covered by the workflow's shared native topology
# proof and test_preview_public_smoke.py. The retired multi-wheel installer is
# not a second supported release topology.


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
    native_name = "agentic-workspace-native-0.52.0-test.zip"
    assets[native_name] = b"paired native archive"
    manifest["native_archive"] = {"asset": native_name, "sha256": hashlib.sha256(assets[native_name]).hexdigest()}
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


def test_existing_preview_recovery_uses_recorded_source_after_branch_advances(tmp_path, monkeypatch):
    import pytest

    helper = _load_helper()
    module = helper.coordinated_release
    repo = tmp_path / "repo"
    repo.mkdir()
    ownership = _fixture(repo)
    _git(repo, "init", "-b", "master")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "source")
    source = _git(repo, "rev-parse", "HEAD")
    monkeypatch.setattr(module, "ROOT", repo)
    _git(repo, "switch", "--detach", source)
    module.prepare_preview_release(ownership, tag="preview-v0.52.0", source_commit=source)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "preview")
    artifact = _git(repo, "rev-parse", "HEAD")
    _git(repo, "tag", "-a", "preview-v0.52.0", "-m", "immutable preview")
    tag_object = _git(repo, "rev-parse", "refs/tags/preview-v0.52.0")
    _git(repo, "switch", "master")
    (repo / "later.txt").write_text("later reconstruction work")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "advance reconstruction")
    advanced = _git(repo, "rev-parse", "HEAD")
    remote = tmp_path / "remote.git"
    _git(repo, "clone", "--bare", str(repo), str(remote))
    _git(repo, "remote", "add", "origin", str(remote))
    effects = []

    def git(*args, cwd=repo, check=True):
        if args[0] == "push":
            effects.append(args)
        return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True)

    monkeypatch.setattr(helper, "_git", git)
    monkeypatch.setattr(helper, "_resolve_commit", lambda ref: _git(repo, "rev-parse", f"{ref}^{{commit}}"))

    def recover(**kwargs):
        assert kwargs["verified"]["reconstruction_source_commit"] == source
        assert kwargs["verified"]["artifact_commit"] == artifact
        effects.append("recover")
        return {"publication_status": "publisher-complete"}

    monkeypatch.setattr(helper, "_recover_publisher", recover)
    arguments = dict(version="0.52.0", remote="origin", reconstruction_ref="master", push=True)
    for source_ref in (None, source):
        result = helper.create_preview_subject(**arguments, source_ref=source_ref)
        assert result["status"] == "existing-current"
        assert result["artifact_commit"] == artifact
        assert result["reconstruction_source_commit"] == source
    assert effects.count("recover") == 2
    before = list(effects)
    with pytest.raises(SystemExit, match="metadata mismatch"):
        helper.create_preview_subject(**arguments, source_ref=advanced)
    assert effects == before
    assert _git(repo, "rev-parse", "refs/tags/preview-v0.52.0") == tag_object
    assert _git(repo, "rev-parse", "master") == advanced
    assert _git(repo, "status", "--porcelain") == ""
    assert _git(remote, "rev-parse", "refs/tags/preview-v0.52.0") == tag_object

    # Even a valid immutable subject cannot recover outside the currently
    # allowed reconstruction ancestry.
    unrelated = _git(repo, "commit-tree", "HEAD^{tree}", "-m", "unrelated root")
    _git(repo, "update-ref", "refs/remotes/origin/master", unrelated)
    monkeypatch.setattr(helper, "_fetch_reconstruction_ref", lambda **kw: "refs/remotes/origin/master")
    with pytest.raises(SystemExit, match="not reachable"):
        helper.create_preview_subject(**arguments, source_ref=None)
    assert effects == before


def test_preview_version_reservation_survives_package_topology_changes(tmp_path, monkeypatch):
    import copy

    import pytest

    module = _load_module()
    ownership = _fixture(tmp_path)
    _git(tmp_path, "init", "-b", "master")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "source")
    source = _git(tmp_path, "rev-parse", "HEAD")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    _git(tmp_path, "switch", "--detach", source)
    module.prepare_preview_release(ownership, tag="preview-v0.52.0", source_commit=source)
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "published preview")
    _git(tmp_path, "tag", "preview-v0.52.0")
    _git(tmp_path, "switch", "master")

    added = copy.deepcopy(ownership)
    path = tmp_path / "packages/new/pyproject.toml"
    path.parent.mkdir()
    path.write_text('[project]\nname = "agentic-workspace-new"\nversion = "0.51.0"\n')
    added["packages"].append({"name": "agentic-workspace-new", "pyproject": "packages/new/pyproject.toml"})
    moved = copy.deepcopy(ownership)
    moved["packages"][1]["pyproject"] = "packages/new/moved.toml"
    (path.parent / "moved.toml").write_text((tmp_path / "packages/memory/pyproject.toml").read_text())
    removed = copy.deepcopy(ownership)
    removed["packages"].pop()
    removed["typescript_packages"] = []
    for changed in (added, moved, removed):
        assert module.Version.parse("0.52.0") in module.existing_release_versions(changed)
        assert module.plan_release(changed)["version"] == "0.52.1"
        with pytest.raises(SystemExit, match="must be greater than"):
            module.prepare_preview_release(changed, tag="preview-v0.52.0", source_commit=source)

    # A forged canonical preview still burns the identity; reservation never
    # legitimizes its mismatched subject. Stable tag admission stays unchanged.
    _git(tmp_path, "tag", "preview-v0.60.0")
    _git(tmp_path, "tag", "v0.70.0")
    assert module.plan_release(added)["version"] == "0.60.1"
    assert module.Version.parse("0.70.0") not in module.existing_release_versions(added)
    with pytest.raises(SystemExit, match="requires workspace version"):
        module.verify_preview_release(ownership, tag="preview-v0.60.0")
    with pytest.raises(SystemExit, match="must be greater than"):
        module.prepare_preview_release(ownership, tag="preview-v0.60.0", source_commit=source)
    for malformed in ("preview-v0.060.0", "preview-v0.60.0-extra"):
        with pytest.raises(ValueError):
            module.parse_release_tag(malformed)


def test_preview_creation_consumer_reuses_native_terminal_lifecycle(tmp_path, shared_core_binary, native_cli, monkeypatch):
    import os

    import pytest
    from tests.test_native_resources import git, repository, resource

    helper = _load_helper()
    repository(tmp_path)
    runner_ref = Path("scripts/check/run_compact_command.py")
    (tmp_path / runner_ref).parent.mkdir(parents=True)
    (tmp_path / runner_ref).write_bytes((ROOT / runner_ref).read_bytes())
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "validation runner")
    monkeypatch.setattr(helper, "ROOT", tmp_path)
    monkeypatch.setenv("AGENTIC_WORKSPACE_CORE_BINARY", str(shared_core_binary))
    commit = git(tmp_path, "rev-parse", "HEAD")
    with pytest.raises(SystemExit, match="current policy judgment"):
        helper._preview_isolation("preview-v1.2.3", commit, None)
    proposal = resource(
        "json",
        shared_core_binary,
        native_cli,
        {"target": str(tmp_path), "task": "Prepare immutable preview preview-v1.2.3", "request": {"operation": "worktree-create"}},
    )
    action = helper._preview_isolation("preview-v1.2.3", commit, proposal["policy_revision"])
    path = Path(action["request"]["path"])
    environment = {**os.environ, **action["build_environment"]}
    # Exercise the actual hook runner in a fresh process, including retained
    # failure diagnostics, under the consumer's creation-leased output lifetime.
    for exit_code in (0, 1):
        executed = helper._run(
            [
                sys.executable,
                str(path / runner_ref),
                "--label",
                "preview hook",
                "--run-id",
                f"preview-{exit_code}",
                "--",
                sys.executable,
                "-c",
                f"print('hook evidence'); raise SystemExit({exit_code})",
            ],
            cwd=path,
            environment=environment,
            check=False,
        )
        assert executed.returncode == exit_code, executed.stdout + executed.stderr
    output = Path(environment["AW_VALIDATION_OUTPUT_ROOT"])
    assert output.is_relative_to(path / "target")
    assert list((output / "command-logs").glob("*.log"))
    assert list((output / "validation-results").rglob("*.json"))
    assert not (path / "scratch").exists()
    for variable in ("UV_CACHE_DIR", "RUFF_CACHE_DIR"):
        cache = Path(environment[variable])
        assert cache.is_relative_to(path / "target")
        cache.mkdir(parents=True, exist_ok=True)
        (cache / "disposable-cache").write_text("tool output")
    original_head = git(tmp_path, "rev-parse", "HEAD")
    original_status = git(tmp_path, "status", "--porcelain")
    (path / "untracked-result.txt").write_text("failed normalization evidence")
    with pytest.raises(SystemExit, match="work preserved"):
        helper._finish_preview_isolation(action)
    assert path.exists()
    assert list((output / "command-logs").glob("*.log")), "blocked cleanup preserves diagnostics"
    (path / "untracked-result.txt").unlink()
    helper._finish_preview_isolation(action)
    assert not path.exists()
    assert "aw-resource" not in git(tmp_path, "worktree", "list", "--porcelain")
    assert git(tmp_path, "rev-parse", "HEAD") == original_head
    assert git(tmp_path, "status", "--porcelain") == original_status


def test_preview_creation_preserves_primary_failure_and_reports_cleanup(tmp_path, monkeypatch, capsys):
    import pytest

    helper = _load_helper()
    monkeypatch.setattr(helper, "_fetch_reconstruction_ref", lambda **kw: "fetched")
    monkeypatch.setattr(helper, "_tag_commit", lambda tag: None)
    monkeypatch.setattr(helper, "_resolve_commit", lambda *a, **kw: "a" * 40)
    monkeypatch.setattr(helper, "_assert_source_is_reconstruction_candidate", lambda *a, **kw: None)
    monkeypatch.setattr(
        helper,
        "_preview_isolation",
        lambda *a: {
            "target": str(tmp_path),
            "task": "preview",
            "changed": [],
            "request": {"path": str(tmp_path)},
            "build_environment": {},
        },
    )
    monkeypatch.setattr(helper, "_load_ownership", lambda *a: {})
    monkeypatch.setattr(helper, "_verify_release_only_paths", lambda *a: ["pyproject.toml"])
    monkeypatch.setattr(helper, "_git", lambda *a, **kw: subprocess.CompletedProcess(a, 0, "pyproject.toml\n", ""))
    cleanup_calls = []

    def cleanup(context):
        cleanup_calls.append(context)
        raise SystemExit("work preserved: exact resource path")

    monkeypatch.setattr(helper, "_finish_preview_isolation", cleanup)
    # Admission exits and subprocess failures must both survive a blocked
    # cleanup. A successful publication must retain its result despite cleanup.
    for primary in (SystemExit("non-release-only paths"), subprocess.CalledProcessError(1, ["generator"])):

        def run(*a, **kw):
            if primary is not None:
                raise primary
            return subprocess.CompletedProcess(a, 0, "{}", "")

        monkeypatch.setattr(helper, "_run", run)
        with pytest.raises(type(primary)) as raised:
            helper.create_preview_subject(version="0.53.0", source_ref="a" * 40, remote="origin", reconstruction_ref="master", push=False)
        assert raised.value is primary
        assert "work preserved: exact resource path" in capsys.readouterr().err

    verified = {"tag": "preview-v0.53.0", "artifact_commit": "b" * 40, "reconstruction_source_commit": "a" * 40}
    monkeypatch.setattr(helper, "_run", lambda *a, **kw: subprocess.CompletedProcess(a, 0, json.dumps(verified), ""))
    monkeypatch.setattr(helper, "_recover_publisher", lambda **kw: {"publication_status": "publisher-dispatch-requested"})
    for push in (False, True):
        code = helper.main(["--version", "0.53.0", "--source-commit", "a" * 40, *(["--push"] if push else [])])
        result = json.loads(capsys.readouterr().out)
        assert code == 2
        assert result["artifact_commit"] == verified["artifact_commit"]
        assert result["tag"] == verified["tag"] and result["pushed"] is push
        assert result["cleanup"]["status"] == "reentry-required"
        assert result["cleanup"]["resource_context"] == {"target": str(tmp_path), "task": "preview", "changed": [], "path": str(tmp_path)}
        if push:
            assert result["publication_status"] == "publisher-dispatch-requested"
    assert len(cleanup_calls) == 4
    monkeypatch.setattr(helper, "_finish_preview_isolation", lambda context: None)
    assert helper.main(["--version", "0.53.0", "--source-commit", "a" * 40]) == 0
    assert json.loads(capsys.readouterr().out)["cleanup"] == {"status": "removed"}
