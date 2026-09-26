"""Expected release follow-ups stay green while invalid subjects fail closed."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"src/tooling/release/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("invalid", [False, True])
def test_projection_observation_reports_valid_drift_but_rejects_invalid_release(tmp_path, monkeypatch, invalid):
    current = load("current_install")
    checked = tmp_path / "projection.json"
    checked.write_text('{"version":"1.0.0"}')
    monkeypatch.setattr(current, "PROJECTION", checked)
    monkeypatch.setattr(current.subprocess, "check_output", lambda *_: b'{"tag_name":"v1.0.1","sha":"source"}')
    monkeypatch.setattr(current, "fetch", lambda *_: b"{}")

    def projection(*_):
        if invalid:
            raise ValueError("Public release identity mismatch")
        return {"version": "1.0.1"}

    monkeypatch.setattr(current, "projection", projection)
    monkeypatch.setattr("sys.argv", ["current_install.py", "--observe"])
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    if invalid:
        with pytest.raises(ValueError, match="identity mismatch"):
            current.main()
        assert not summary.exists()
    else:
        current.main()
        assert "refresh needed" in summary.read_text() and "--refresh" in summary.read_text()
    assert json.loads(checked.read_text()) == {"version": "1.0.0"}


@pytest.mark.parametrize("head", ["matching", "mismatched"])
def test_generated_pr_semver_dispatch_binds_the_open_exact_head(tmp_path, monkeypatch, head):
    monkeypatch.syspath_prepend(str(ROOT / "src/tooling"))
    semver = load("pr_semver_admission")
    source = "a" * 40
    pr = {
        "state": "open",
        "base": {"repo": {"full_name": "owner/repo"}, "ref": "master"},
        "head": {"sha": source if head == "matching" else "b" * 40, "ref": "candidate"},
    }
    monkeypatch.setattr(semver.subprocess, "check_output", lambda *_: json.dumps(pr).encode())
    for key, value in {
        "EVENT_PATH": "unused",
        "BASE_REF": "",
        "HEAD_REF": "",
        "DISPATCH_PR": "1",
        "EXPECTED_HEAD_SHA": source,
        "GITHUB_SHA": source,
        "GITHUB_REPOSITORY": "owner/repo",
        "SEMVER_ADMISSION_PATH": str(tmp_path / "admission.json"),
        "GITHUB_RUN_ID": "7",
        "GITHUB_RUN_ATTEMPT": "1",
    }.items():
        monkeypatch.setenv(key, value)
    admitted = []
    monkeypatch.setattr(semver, "admit", lambda **kwargs: admitted.append(kwargs))
    if head == "mismatched":
        with pytest.raises(ValueError, match="exact open PR head"):
            semver.main()
        assert admitted == []
    else:
        semver.main()
        assert admitted[0]["head_ref"] == "candidate"
        assert json.loads(Path(admitted[0]["event_path"]).read_text())["pull_request"] == pr
