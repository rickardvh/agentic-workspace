"""Consumer identity, contamination and lifecycle failures must precede success."""

import hashlib
import json
import os
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
