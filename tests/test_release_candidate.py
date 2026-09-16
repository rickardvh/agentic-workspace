"""One first-stable RC identity through shared release admission and promotion."""

from __future__ import annotations

import json
import subprocess
import tomllib

import pytest
from packaging.utils import parse_wheel_filename
from packaging.version import Version
from tests.test_native_npm_routes import packed as packed
from tests.test_preview_release import _fixture, _git, _load_helper, _load_module


@pytest.mark.parametrize(
    "tag",
    [
        "v1.0.0-rc.0",
        "v1.0.0-rc.01",
        "v1.0.0rc1",
        "v1.0.0-RC.1",
        "v1.0.0-rc.1+build",
        "v1.0.1-rc.1",
        "v2.0.0-rc.1",
        "preview-v1.0.0-rc.1",
        "v1.0.0-rc.1\n",
        "v-1.0.0",
    ],
)
def test_only_canonical_first_stable_rc(tag):
    with pytest.raises(ValueError):
        _load_module().parse_release_tag(tag)


def repository(tmp_path, monkeypatch):
    module = _load_module()
    ownership = _fixture(tmp_path)
    # A real lock includes both a local version and an immutable external resolution.
    (tmp_path / "uv.lock").write_text(
        'version=1\n[[package]]\nname="agentic-workspace"\nversion="0.51.0"\nsource={editable="."}\n[[package]]\nname="external"\nversion="2.0.0"\nsource={registry="https://pypi.org/simple"}\n'
    )
    ownership["preview_release_commit_allowed_paths"].append("uv.lock")
    ownership["cargo_packages"] = [
        {"name": "agentic-workspace-core", "path": "crates/agentic-workspace-core"},
        {"name": "agentic-workspace-cli", "path": "crates/agentic-workspace-cli"},
    ]
    for crate in ownership["cargo_packages"]:
        manifest = tmp_path / crate["path"] / "Cargo.toml"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(f'[package]\nname = "{crate["name"]}"\nversion = "0.51.0"\n')
        ownership["preview_release_commit_allowed_paths"].append(f"{crate['path']}/Cargo.toml")
    (tmp_path / "Cargo.lock").write_text(
        "version = 4\n"
        + "".join(f'[[package]]\nname = "{crate["name"]}"\nversion = "0.51.0"\n' for crate in ownership["cargo_packages"])
        + '[[package]]\nname = "external"\nversion = "2.0.0"\nsource = "registry+https://github.com/rust-lang/crates.io-index"\n'
    )
    ownership["preview_release_commit_allowed_paths"].append("Cargo.lock")
    ownership["cargo_lockfiles"] = ["Cargo.lock", "tests/fixture/Cargo.lock"]
    fixture_lock = tmp_path / ownership["cargo_lockfiles"][1]
    fixture_lock.parent.mkdir(parents=True)
    fixture_lock.write_text('version = 4\n[[package]]\nname = "agentic-workspace-core"\nversion = "0.51.0"\n')
    ownership["preview_release_commit_allowed_paths"].append(ownership["cargo_lockfiles"][1])
    (tmp_path / ".github/release-ownership.json").write_text(json.dumps(ownership))
    _git(tmp_path, "init", "-b", "master")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "candidate source")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    return module, ownership, _git(tmp_path, "rev-parse", "HEAD")


def candidate(module, ownership, root, source, number=1):
    tag = f"v1.0.0-rc.{number}"
    _git(root, "switch", "--detach", source)
    result = module.prepare_preview_release(ownership, tag=tag, source_commit=source)
    lock = root / "uv.lock"
    lock.write_text(lock.read_text().replace('version="0.51.0"', f'version="1.0.0rc{number}"'))
    _git(root, "add", ".")
    _git(root, "commit", "-m", tag)
    _git(root, "tag", tag)
    artifact = _git(root, "rev-parse", "HEAD")
    return result, module.verify_preview_release(ownership, tag=tag, artifact_commit=artifact)


def test_rc_progression_immutable_recovery_and_ecosystem_mapping(tmp_path, monkeypatch):
    module, ownership, source = repository(tmp_path, monkeypatch)
    result, verified = candidate(module, ownership, tmp_path, source)
    assert result["release_class"] == "release-candidate"
    assert result["support_bearing"] is False
    assert result["target_stable_tag"] == "v1.0.0"
    assert result["package_versions"] == {"python": "1.0.0rc1", "npm": "1.0.0-rc.1", "cargo": "1.0.0-rc.1"}
    assert Version(result["version"]) < Version("1.0.0")
    assert parse_wheel_filename("agentic_workspace-1.0.0rc1-py3-none-any.whl")[1] == Version("1.0.0rc1")
    assert tomllib.loads((tmp_path / "pyproject.toml").read_text())["project"]["version"] == "1.0.0rc1"
    assert json.loads((tmp_path / "generated/workspace/typescript/package.json").read_text())["version"] == "1.0.0-rc.1"
    assert module.Version(1, 0, 0) not in module.existing_release_versions(ownership)
    with pytest.raises((ValueError, SystemExit)):
        module.verify_workspace_versions(ownership, tag="v1.0.0-rc.1")

    _git(tmp_path, "switch", "master")
    with pytest.raises(SystemExit, match="new candidate source"):
        module.prepare_preview_release(ownership, tag="v1.0.0-rc.2", source_commit=source)
    with pytest.raises(SystemExit, match="contiguous"):
        module.prepare_preview_release(ownership, tag="v1.0.0-rc.3", source_commit=source)

    helper = _load_helper()
    monkeypatch.setattr(helper, "coordinated_release", module)
    monkeypatch.setattr(
        helper,
        "_git",
        lambda *args, **kw: subprocess.run(["git", *args], cwd=tmp_path, capture_output=True, text=True, check=kw.get("check", True)),
    )
    _git(tmp_path, "update-ref", "refs/remotes/origin/master", source)
    monkeypatch.setattr(helper, "_fetch_reconstruction_ref", lambda **kw: "refs/remotes/origin/master")
    monkeypatch.setattr(helper, "_preview_isolation", lambda *args: pytest.fail("Recovery must not renormalize or allocate a checkout"))
    recovered = helper.create_preview_subject(
        version="", rc_tag="v1.0.0-rc.1", source_ref=None, remote="origin", reconstruction_ref="master", push=False
    )
    assert recovered["status"] == "existing-current"
    assert recovered["artifact_commit"] == verified["artifact_commit"]
    (tmp_path / "product.txt").write_text("New product source after candidate feedback")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "new source")
    new_source = _git(tmp_path, "rev-parse", "HEAD")
    _, second = candidate(module, ownership, tmp_path, new_source, 2)
    assert second["reconstruction_source_commit"] == new_source
    assert _git(tmp_path, "rev-list", "-n", "1", "refs/tags/v1.0.0-rc.1") == verified["artifact_commit"]


def test_exact_rc_to_stable_promotion_rejects_product_and_lock_deltas(tmp_path, monkeypatch):
    module, ownership, source = repository(tmp_path, monkeypatch)
    (tmp_path / ".release/changes/major.toml").write_text(
        'schema_version="agentic-workspace/release-change/v1"\nbump="major"\nsummary="Reconstruction compatibility changes"\n'
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "major changeset")
    source = _git(tmp_path, "rev-parse", "HEAD")
    _, rc = candidate(module, ownership, tmp_path, source)
    _git(tmp_path, "switch", "master")
    record = module.prepare_rc_promotion(ownership, rc_tag=rc["tag"])
    assert record["rc_artifact_commit"] == rc["artifact_commit"]
    assert record["rc_package_versions"]["cargo"] == "1.0.0-rc.1"
    note = module.release_note_path(ownership, "1.0.0").read_text(encoding="utf-8")
    assert f"Promotes {rc['tag']} from exact source `{source}`" in note
    assert "- Pending product change" in note
    assert "- Reconstruction compatibility changes" in note
    assert not list((tmp_path / ".release/changes").glob("*.toml"))
    lock = tmp_path / "uv.lock"
    lock.write_text(lock.read_text().replace('version="0.51.0"', 'version="1.0.0"'))
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "stable normalization")
    stable = _git(tmp_path, "rev-parse", "HEAD")
    assert module.verify_rc_promotion(ownership)["support_bearing_admission"] == "required-separately"
    for path, content in [
        ("product.txt", "changed"),
        ("uv.lock", lock.read_text().replace('version="2.0.0"', 'version="2.0.1"')),
        ("Cargo.lock", (tmp_path / "Cargo.lock").read_text().replace('version = "2.0.0"', 'version = "2.0.1"')),
    ]:
        _git(tmp_path, "switch", "--detach", stable)
        (tmp_path / path).write_text(content)
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "forged product delta")
        with pytest.raises(SystemExit, match="delta|custody"):
            module.verify_rc_promotion(ownership)
    _git(tmp_path, "switch", "--detach", stable)
    path = tmp_path / module.PROMOTION_RECORD
    forged = json.loads(path.read_text())
    forged["rc_artifact_commit"] = "f" * 40
    path.write_text(json.dumps(forged))
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "forged rc")
    with pytest.raises(SystemExit, match="immutable RC"):
        module.verify_rc_promotion(ownership)


def test_rc_receipts_use_release_tag_url_and_never_stable_support(tmp_path, monkeypatch):
    import importlib.util
    from pathlib import Path

    helper = _load_helper()  # exposes the same release import directory as its CLI
    spec = importlib.util.spec_from_file_location(
        "rc_manifest", Path(__file__).resolve().parents[1] / "scripts/release/preview_manifest.py"
    )
    manifest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manifest)
    monkeypatch.setattr(manifest, "ROOT", tmp_path)
    owner_path = tmp_path / "ownership.json"
    owner_path.write_text("{}")
    monkeypatch.setattr(manifest, "OWNERSHIP_PATH", owner_path)
    ownership = {
        "distribution_identity": {
            "canonical_root_distribution": "agentic-workspace",
            "canonical_install_receipt": "install.json",
            "redistributable_receipt": "redistribution.json",
            "release_candidate_base_url_template": "https://example.test/releases/download/{tag}",
        },
        "project_identity": {"license_spdx": "MIT"},
    }
    packages = [
        {
            "ecosystem": "python",
            "name": "agentic-workspace",
            "wheel": {"asset": "agentic_workspace-1.0.0rc1-py3-none-any.whl", "sha256": "a" * 64},
            "sdist": {"asset": "agentic_workspace-1.0.0rc1.tar.gz", "sha256": "b" * 64},
        }
    ]
    manifest._write_preview_readiness_receipts(
        ownership=ownership,
        dist=tmp_path,
        tag="v1.0.0-rc.1",
        version="1.0.0rc1",
        package_entries=packages,
        subject={"artifact_commit": "a" * 40, "reconstruction_source_commit": "b" * 40},
    )
    install = json.loads((tmp_path / "install.json").read_text())
    assert install["release_class"] == "release-candidate" and install["support_bearing"] is False
    assert install["target_stable_tag"] == "v1.0.0"
    assert install["package_versions"] == helper.coordinated_release.release_identity("v1.0.0-rc.1")["package_versions"]
    assert "/v1.0.0-rc.1/agentic_workspace-1.0.0rc1-" in install["artifact"]["url"]
    assert not (tmp_path / "support-bearing-promotion.json").exists()
    assert helper.coordinated_release.release_identity("preview-v0.56.0")["release_class"] == "preview"


def test_rc_ecosystems_build_the_declared_artifact_identities(tmp_path):
    import shutil
    import tarfile
    import zipfile

    module = _load_module()
    identity = module.release_identity("v1.0.0-rc.1")
    declaration = json.loads((module.ROOT / ".github/release-ownership.json").read_text(encoding="utf-8"))["release_candidate"]
    assert identity["package_versions"] == {
        ecosystem: declaration[f"{ecosystem}_version"].replace("N", "1") for ecosystem in ("python", "npm", "cargo")
    }
    python = tmp_path / "python"
    python.mkdir()
    (python / "candidate_fixture.py").write_text('VALUE = "candidate"\n')
    (python / "pyproject.toml").write_text(
        '[build-system]\nrequires=["hatchling>=1.27"]\nbuild-backend="hatchling.build"\n[project]\nname="candidate-fixture"\nversion="'
        + identity["package_versions"]["python"]
        + '"\n[tool.hatch.build.targets.wheel]\nonly-include=["candidate_fixture.py"]\n'
    )
    dist = tmp_path / "dist"
    subprocess.run(["uv", "build", "--project", str(python), "--wheel", "--sdist", "--out-dir", str(dist)], check=True, capture_output=True)
    wheel = dist / "candidate_fixture-1.0.0rc1-py2.py3-none-any.whl"
    assert parse_wheel_filename(wheel.name)[1] == Version("1.0.0rc1")
    with zipfile.ZipFile(wheel) as archive:
        metadata = archive.read("candidate_fixture-1.0.0rc1.dist-info/METADATA").decode()
        assert "Version: 1.0.0rc1" in metadata
    assert (dist / "candidate_fixture-1.0.0rc1.tar.gz").is_file()
    node = tmp_path / "node"
    node.mkdir()
    (node / "package.json").write_text(
        json.dumps({"name": "candidate-fixture", "version": identity["package_versions"]["npm"], "private": True})
    )
    subprocess.run(
        [shutil.which("npm"), "pack", "--ignore-scripts", "--pack-destination", str(dist)], cwd=node, check=True, capture_output=True
    )
    with tarfile.open(dist / "candidate-fixture-1.0.0-rc.1.tgz") as archive:
        assert json.load(archive.extractfile("package/package.json"))["version"] == "1.0.0-rc.1"

    # Registry consumers use the owner mapping directly, without parsing the tag.
    cargo = tmp_path / "cargo"
    (cargo / "src").mkdir(parents=True)
    (cargo / "src/lib.rs").write_text("pub fn candidate() {}\n")
    (cargo / "Cargo.toml").write_text(
        '[package]\nname="candidate-fixture"\nversion="' + identity["package_versions"]["cargo"] + '"\nedition="2021"\n'
    )
    subprocess.run(["cargo", "package", "--offline", "--allow-dirty"], cwd=cargo, check=True, capture_output=True)
    with tarfile.open(cargo / "target/package/candidate-fixture-1.0.0-rc.1.crate") as archive:
        metadata = tomllib.loads(archive.extractfile("candidate-fixture-1.0.0-rc.1/Cargo.toml").read().decode())
        assert metadata["package"]["version"] == identity["package_versions"]["cargo"]


def test_packed_node_consumer_preserves_exact_rc_native_mapping(packed, tmp_path):
    import os
    import shutil

    package = tmp_path / "package"
    shutil.copytree(packed, package)
    metadata_path = package / "package.json"
    native_path = package / "src/native/bin/artifact.json"
    metadata = json.loads(metadata_path.read_text())
    native = json.loads(native_path.read_text())
    metadata["version"] = "1.0.0-rc.1"
    native["package_version"] = "1.0.0rc1"
    metadata_path.write_text(json.dumps(metadata))
    native_path.write_text(json.dumps(native))
    # Exercise manifest admission using already-proven binary bytes; this does
    # not claim those source-test binaries were compiled as an RC release.
    script = "import {start} from './src/native/operating.mjs'; console.log(JSON.stringify(start({target:process.cwd(),task:'Inspect'})));"
    env = {k: v for k, v in os.environ.items() if k != "AGENTIC_WORKSPACE_CORE_BINARY"}
    result = subprocess.run(
        [shutil.which("node"), "--input-type=module", "-e", script], cwd=package, env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    native["package_version"] = "1.0.0rc2"
    native_path.write_text(json.dumps(native))
    rejected = subprocess.run(
        [shutil.which("node"), "--input-type=module", "-e", script], cwd=package, env=env, capture_output=True, text=True
    )
    assert rejected.returncode != 0 and "platform/version mismatch" in rejected.stderr


@pytest.mark.parametrize("tag,label", [("preview-v0.52.0", "Preview"), ("v1.0.0-rc.1", "Release candidate")])
def test_prerelease_public_wording_matches_class(tmp_path, monkeypatch, tag, label):
    module = _load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    note = module.write_preview_release_note({}, tag=tag, source_commit="a" * 40).read_text(encoding="utf-8")
    assert module.prerelease_label(tag) == label
    assert note.startswith(f"# {label} {tag}\n")
    assert f"Non-support-bearing {label.lower()}" in note
    assert f"Stability/support: {label.lower()} only" in note
    if label == "Release candidate":
        assert "preview" not in note.lower()


@pytest.mark.parametrize("tag,label", [("preview-v0.52.0", "Preview"), ("v1.0.0-rc.1", "Release candidate")])
def test_prerelease_helper_creates_truthful_annotated_tag(tmp_path, monkeypatch, tag, label):
    helper = _load_helper()
    monkeypatch.setattr(helper, "_fetch_reconstruction_ref", lambda **kw: "fetched")
    monkeypatch.setattr(helper, "_tag_commit", lambda tag: None)
    monkeypatch.setattr(helper, "_resolve_commit", lambda *a, **kw: "a" * 40)
    monkeypatch.setattr(helper, "_assert_source_is_reconstruction_candidate", lambda *a, **kw: None)
    monkeypatch.setattr(helper, "_preview_isolation", lambda *a: {"request": {"path": str(tmp_path)}, "build_environment": {}})
    monkeypatch.setattr(helper, "_finish_preview_isolation", lambda *a: None)
    monkeypatch.setattr(helper, "_load_ownership", lambda *a: {})
    monkeypatch.setattr(helper, "_verify_release_only_paths", lambda *a: ["pyproject.toml"])
    calls = []

    def git(*args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "pyproject.toml\n", "")

    monkeypatch.setattr(helper, "_git", git)
    monkeypatch.setattr(helper, "_run", lambda *a, **kw: subprocess.CompletedProcess(a, 0, json.dumps({"tag": tag}), ""))
    result = helper.create_preview_subject(
        version="0.52.0",
        rc_tag=tag if label == "Release candidate" else None,
        source_ref=None,
        remote="origin",
        reconstruction_ref="master",
        push=False,
    )
    assert result["status"] == "created"
    assert next(args for args in calls if args[:2] == ("tag", "-a")) == ("tag", "-a", tag, "a" * 40, "-m", f"{label} {tag}")
