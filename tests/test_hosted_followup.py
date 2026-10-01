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
