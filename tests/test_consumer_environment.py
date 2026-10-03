"""Consumer identity, contamination and lifecycle failures must precede success."""

import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/tooling/release"))
from consumer_environment import DockerConsumer, Subject, private_native_environment, safe_native_archive  # noqa: E402


@pytest.mark.parametrize("fault", [None, "target", "version", "source", "digest", "dirty"])
def test_archive_identity_is_checked_before_execution(tmp_path, fault):
    data = b"not executed"
    digest = hashlib.sha256(data).hexdigest()
    identity = dict(
        rust_host="x86_64-unknown-linux-gnu",
        source_head="a" * 40,
        source_dirty=False,
        package_version="1.3.2",
        cli_sha256=digest,
        sha256=digest,
    )
    field = {"target": "rust_host", "version": "package_version", "source": "source_head", "digest": "sha256", "dirty": "source_dirty"}
    if fault:
        identity[field[fault]] = True if fault == "dirty" else "different"
    archive = tmp_path / "native.zip"
    with zipfile.ZipFile(archive, "w") as packed:
        packed.writestr("artifact.json", json.dumps(identity))
        packed.writestr("agentic-workspace", data)
        packed.writestr("agentic-workspace-core", data)
        packed.writestr("../../escape", b"untrusted member")
    subject = Subject("candidate", tmp_path, {"version": "1.3.2", "source_commit": "a" * 40})
    if fault:
        with pytest.raises(ValueError):
            safe_native_archive(archive, tmp_path / "installed", subject, "x86_64-unknown-linux-gnu")
    else:
        safe_native_archive(archive, tmp_path / "installed", subject, "x86_64-unknown-linux-gnu")
        assert sorted(p.name for p in (tmp_path / "installed").iterdir()) == [
            "agentic-workspace",
            "agentic-workspace-core",
            "artifact.json",
        ]


def test_private_state_does_not_borrow_host_credentials_or_python(monkeypatch, tmp_path):
    for key in ("PYTHONPATH", "AGENTIC_WORKSPACE_CORE_BINARY", "GITHUB_TOKEN", "OPENAI_API_KEY", "NPM_TOKEN", "VIRTUAL_ENV"):
        monkeypatch.setenv(key, "must not enter consumer")
    environments = [private_native_environment(tmp_path / name, []) for name in ("first", "second")]
    assert environments[0]["HOME"] != environments[1]["HOME"]
    assert all(key not in environments[0] for key in ("PYTHONPATH", "GITHUB_TOKEN", "OPENAI_API_KEY", "NPM_TOKEN", "VIRTUAL_ENV"))
    assert environments[0]["GIT_CONFIG_GLOBAL"] == os.devnull


def test_global_executable_is_not_repository_local_proof(tmp_path):
    binary = tmp_path / ("agentic-workspace.exe" if os.name == "nt" else "agentic-workspace")
    binary.write_bytes(b"wrong global version")
    binary.chmod(0o755)
    with pytest.raises(ValueError, match="Global AW"):
        private_native_environment(tmp_path / "consumer", [tmp_path])


def test_partial_preparation_and_interruption_remove_only_owned_container(monkeypatch, tmp_path):
    import consumer_environment as environment

    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        if argv[:2] == ["docker", "start"]:
            raise KeyboardInterrupt()

    monkeypatch.setattr(environment, "run", fake_run)
    subject = Subject("candidate", tmp_path, {"platforms": [{"target": "linux", "node_platform": "linux"}]})
    consumer = DockerConsumer(subject, "standalone", "linux", "sha256:" + "a" * 64)
    with pytest.raises(KeyboardInterrupt):
        consumer.__enter__()
    assert calls[-1] == ["docker", "rm", "--force", consumer.name]
    assert consumer.cleanup == "removed"
    assert not any("--volume" in call or "--mount" in call for call in calls)


def test_public_subject_rejects_alias_before_network(tmp_path):
    for alias in ("latest", "v1.3.2", "1.3.2rc1", "../1.3.2"):
        with pytest.raises(ValueError, match="exact stable"):
            Subject.public(alias, tmp_path / "subject")


@pytest.mark.parametrize(
    "entry", ["release/consumer_environment.py", "model-cli-harness/run_model_cli_harness.py", "model-cli-harness/consumer_schedule.py"]
)
def test_documented_consumer_entry_points_import_in_a_fresh_process(entry):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, str(root / "src/tooling" / entry), "--help"], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "tag",
        "draft",
        "prerelease",
        "promotion",
        "source",
        "receipt",
        "receipt-version",
        "receipt-digest",
        "install-url",
        "install-digest",
        "missing-asset",
        "manifest-source",
        "manifest-digest",
        "artifact-digest",
        "cargo-digest",
        "crate-digest",
        "missing-receipt",
    ],
)
def test_public_subject_freezes_exact_admitted_bytes_or_fails(tmp_path, monkeypatch, fault):
    import consumer_environment as environment
    import platform_release

    version, source = "1.3.2", "a" * 40
    base = f"https://github.com/{environment.REPOSITORY}/releases/download/v{version}/"
    assets = {}

    def item(name):
        assets[name] = name.encode()
        return {"asset": name, "sha256": hashlib.sha256(assets[name]).hexdigest()}

    inventory = {
        "kind": "agentic-workspace/platform-release/v1",
        "version": version,
        "source_commit": source,
        "platforms": [
            {**row, "wheel": item(row["target"] + ".whl"), "native_archive": item(row["target"] + ".zip")}
            for row in platform_release.platforms()
        ],
        "npm": item("package.tgz"),
    }
    artifact = inventory["platforms"][0]["wheel"]
    receipt = {
        "kind": "agentic-workspace/distribution-install-readiness/v1",
        "status": "passed",
        "version": version,
        "artifact": {"name": artifact["asset"], "sha256": artifact["sha256"], "url": base + artifact["asset"]},
    }
    if fault == "receipt":
        receipt["status"] = "failed"
    if fault == "receipt-version":
        receipt["version"] = "1.2.0"
    if fault == "install-url":
        receipt["artifact"]["url"] = "https://example.invalid/unadmitted"
    if fault == "install-digest":
        receipt["artifact"]["sha256"] = "0" * 64
    if fault == "manifest-source":
        inventory["source_commit"] = "b" * 40
    assets[platform_release.MANIFEST] = json.dumps(inventory).encode()
    assets["distribution-install-readiness.json"] = json.dumps(receipt).encode()
    assets["cargo-release-manifest.json"] = json.dumps({"packages": [item("package.crate")]}).encode()
    promotion = {
        "kind": "agentic-workspace/support-bearing-promotion/v1",
        "status": "passed",
        "source_commit": source,
        "artifacts": {name: "sha256:" + hashlib.sha256(data).hexdigest() for name, data in assets.items()},
    }
    if fault == "promotion":
        promotion["status"] = "blocked"
    if fault == "source":
        promotion["source_commit"] = "b" * 40
    for name, selected_fault in [
        ("distribution-install-readiness.json", "receipt-digest"),
        (platform_release.MANIFEST, "manifest-digest"),
        ("cargo-release-manifest.json", "cargo-digest"),
    ]:
        if fault == selected_fault:
            promotion["artifacts"][name] = "sha256:" + "0" * 64
    for name, selected_fault in [(artifact["asset"], "artifact-digest"), ("package.crate", "crate-digest")]:
        if fault == selected_fault:
            assets[name] = b"changed public bytes"
    release = {"tag_name": f"v{version}", "draft": False, "prerelease": False, "assets": [{"name": name} for name in assets]}
    if fault in {"draft", "prerelease"}:
        release[fault] = True
    if fault == "tag":
        release["tag_name"] = "v1.2.0"
    if fault == "missing-asset":
        release["assets"] = []
    assets["support-bearing-promotion.json"] = json.dumps(promotion).encode()
    if fault == "missing-receipt":
        del assets["distribution-install-readiness.json"]

    def fetch(url):
        if url == f"https://api.github.com/repos/{environment.REPOSITORY}/releases/tags/v{version}":
            return json.dumps(release).encode()
        if url == f"https://api.github.com/repos/{environment.REPOSITORY}/commits/v{version}":
            return json.dumps({"sha": source}).encode()
        assert url.startswith(base), "Subject followed an unselected release or checkout route"
        name = url.removeprefix(base)
        if name not in assets:
            raise FileNotFoundError(name)
        return assets[name]

    monkeypatch.setattr(environment, "fetch", fetch)
    destination = tmp_path / "frozen"
    if fault:
        with pytest.raises((ValueError, FileNotFoundError)):
            Subject.public(version, destination)
    else:
        subject = Subject.public(version, destination)
        assert subject.identity() == {
            "mode": "public",
            "version": version,
            "source_commit": source,
            "inventory_sha256": hashlib.sha256(assets[platform_release.MANIFEST]).hexdigest(),
        }
        subject.revalidate("standalone")
        assert all(
            (destination / name).read_bytes() == data
            for name, data in assets.items()
            if name not in {"support-bearing-promotion.json", "distribution-install-readiness.json"}
        )
        (destination / artifact["asset"]).write_bytes(b"changed frozen bytes")
        with pytest.raises(ValueError, match="digest"):
            subject.revalidate("standalone")


@pytest.mark.parametrize("profile", ["node", "python"])
def test_native_registry_wrapper_mismatch_fails_before_install(tmp_path, monkeypatch, profile):
    from types import SimpleNamespace

    import consumer_environment as environment

    item = {"asset": "admitted.whl", "sha256": hashlib.sha256(b"admitted package").hexdigest()}
    row = {"target": "fixture", "native_archive": {"asset": "native.zip"}, "wheel": item}
    subject = Subject("public", tmp_path, {"version": "1.3.2", "npm": item, "platforms": [row]})
    monkeypatch.setattr(Subject, "identity", lambda _: {"inventory_sha256": "a" * 64})
    monkeypatch.setattr(environment.platform_release, "current_platform", lambda: {"target": "fixture"})
    monkeypatch.setattr(environment.platform_release, "load", lambda _: subject.inventory)
    monkeypatch.setattr(environment, "safe_native_archive", lambda *a: {})
    responses = iter(
        [json.dumps({"dist": {"tarball": "registry-asset"}}).encode(), b"same native bytes but changed wrapper"]
        if profile == "node"
        else [json.dumps({"urls": [{"filename": item["asset"], "digests": {"sha256": "different"}, "url": "registry-asset"}]}).encode()]
    )
    monkeypatch.setattr(environment, "fetch", lambda _: next(responses))
    consumer = environment.NativeConsumer(subject, profile, "fixture", tmp_path)
    consumer.root = consumer.repo = tmp_path
    consumer.tools = {"npm": "npm", "uv": "uv"}

    def execute(command):
        assert "install" not in command, "Mismatched package reached the package manager"
        return SimpleNamespace(stdout="")

    consumer.exec = execute
    with pytest.raises(ValueError, match="Public"):
        consumer.install()


def test_target_candidate_is_standalone_scoped_and_revalidated(tmp_path):
    import platform_release

    archive = tmp_path / "native.zip"
    archive.write_bytes(b"bounded candidate bytes")
    row = {
        **platform_release.platforms()[0],
        "native_archive": {"asset": archive.name, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()},
    }
    manifest = tmp_path / platform_release.MANIFEST
    manifest.write_text(
        json.dumps(
            {"kind": "agentic-workspace/target-consumer-candidate/v1", "version": "1.3.2", "source_commit": "a" * 40, "platforms": [row]}
        )
    )
    selected = Subject.candidate(tmp_path)
    assert selected.mode == "target-candidate"
    selected.revalidate("standalone")
    with pytest.raises(ValueError, match="standalone"):
        selected.revalidate("python")
    with pytest.raises(ValueError, match="Unsupported"):
        platform_release.load(tmp_path)
    archive.write_bytes(b"changed")
    with pytest.raises(ValueError, match="digest"):
        selected.revalidate("standalone")
