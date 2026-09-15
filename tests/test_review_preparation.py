import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "tools/skills/pr-review-recheck/prepare.py"
SPEC = importlib.util.spec_from_file_location("review_preparation", PATH)
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)
BASELINE = "a" * 40


@pytest.fixture
def remote(monkeypatch):
    pr = {
        "number": 17,
        "head": {"sha": "b" * 40, "repo": {"full_name": "fork/repo"}},
        "base": {"sha": "c" * 40, "repo": {"full_name": "owner/repo"}},
        "title": "Change",
        "body": "Closes #12",
        "state": "open",
        "html_url": "https://github.com/owner/repo/pull/17",
        "changed_files": 101,
    }
    files = [{"filename": f"src/file{n}.py", "sha": str(n), "status": "modified"} for n in range(101)]
    state = {"pr": pr, "files": files, "comments": [], "issue": {"number": 12, "body": "Outcome"}, "calls": []}

    def api(endpoint, *, collection=None):
        state["calls"].append(endpoint)
        if endpoint == "repos/owner/repo/pulls/17":
            result = copy.deepcopy(state["pr"])
            if state.get("move") and state["calls"].count(endpoint) > 1:
                result["head"]["sha"] = "d" * 40
            return result
        if "/files?" in endpoint:
            return copy.deepcopy(state["files"])
        if endpoint.endswith("issues/12"):
            return copy.deepcopy(state["issue"])
        if "/comments?" in endpoint:
            if state.get("unavailable"):
                raise OSError("transport unavailable")
            return copy.deepcopy(state["comments"])
        return []

    def git(*args):
        if args[0] == "ls-tree":
            return b"AGENTS.md\ntools/skills/pr-review-recheck/SKILL.md\ndocs/maintainer/testing-strategy.md\nsrc/AGENTS.md\nunrelated.md\n"
        if args[-1].endswith("unrelated.md"):
            raise AssertionError("unrelated source must not be read")
        return state.get("guidance", "trusted procedure").encode()

    monkeypatch.setattr(review, "api", api)
    monkeypatch.setattr(review, "git", git)
    return state


def test_first_preparation_exact_subject_complete_files_and_unknowns(remote):
    packet = review.prepare("owner/repo", 17, BASELINE)
    assert packet["status"] == "observed"
    assert packet["subject"]["value"]["head"] == "b" * 40
    assert len(packet["evidence"]["files"]["value"]) == 101
    assert packet["linked_references"] == [{"repository": "owner/repo", "number": 12}]
    assert {entry["path"] for entry in packet["guidance"]} == {
        "AGENTS.md",
        "src/AGENTS.md",
        review.PROCEDURE,
        "docs/maintainer/testing-strategy.md",
    }
    assert packet["delta_scope"] == "REVIEW_ONLY"
    assert "verdict" in packet["authority"]
    remote["unavailable"] = True
    partial = review.prepare("owner/repo", 17, BASELINE)
    assert partial["status"] == "partial"
    assert partial["evidence"]["comments"]["status"] == "unavailable"
    remote["files"].pop()
    assert review.prepare("owner/repo", 17, BASELINE)["evidence"]["files"]["status"] == "unavailable"


def test_recheck_fresh_evidence_preserves_obligations_and_bounds_delta(remote):
    first = review.prepare("owner/repo", 17, BASELINE)
    first["obligations"] = [{"id": "blocker-1", "body": "Must preserve code blocks", "head": "b" * 40}]
    unchanged = review.prepare("owner/repo", 17, BASELINE, previous=first)
    assert unchanged["delta"]["changed"] == []
    assert len(json.dumps(unchanged)) < len(json.dumps(first))
    print(f"review preparation bytes: first={len(json.dumps(first))} recheck={len(json.dumps(unchanged))}; remote calls=9 each")
    remote["issue"]["body"] = "Changed acceptance"
    remote["files"][0]["sha"] = "new blob"
    remote["pr"]["head"]["sha"] = "e" * 40
    changed = review.prepare("owner/repo", 17, BASELINE, previous=first)
    assert changed["obligations"] == first["obligations"]
    assert "issue:owner/repo#12" in changed["delta"]["changed"]
    assert changed["delta"]["files"] == {"added": [], "removed": [], "changed": ["src/file0.py"]}
    assert "guidance" not in changed["delta"]["changed"]
    remote["guidance"] = "Changed trusted procedure"
    assert "guidance" in review.prepare("owner/repo", 17, BASELINE, previous=changed)["delta"]["changed"]
    assert review.prepare("owner/repo", 17, BASELINE, previous={})["delta"]["mode"] == "full"
    remote["move"] = True
    remote["calls"].clear()
    assert review.prepare("owner/repo", 17, BASELINE)["status"] == "stale"


def test_transport_reads_every_page_and_never_requests_mutation(monkeypatch):
    calls = []

    def command(args):
        calls.append(args)
        return json.dumps([[{"filename": "first"}] * 100, [{"filename": "last"}]]).encode()

    monkeypatch.setattr(review, "command", command)
    assert len(review.api("repos/o/r/pulls/1/files?per_page=100", collection="list")) == 101
    assert calls == [["gh", "api", "--method", "GET", "repos/o/r/pulls/1/files?per_page=100", "--paginate", "--slurp"]]


def test_trusted_loader_never_executes_worktree_replacement_and_eligibility_stays_external(tmp_path):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(tmp_path), *args])

    git("init", "-q")
    helper = tmp_path / review.HELPER
    helper.parent.mkdir(parents=True)
    helper.write_bytes(PATH.read_bytes())
    git("add", ".")
    git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", "commit", "-qm", "trusted")
    baseline = git("rev-parse", "HEAD").decode().strip()
    helper.write_text("raise RuntimeError('unreviewed replacement executed')", encoding="utf-8")
    loader = f"import subprocess,sys; s=subprocess.check_output(['git','show',sys.argv[1]+':{review.HELPER}']); exec(compile(s,'trusted-review-preparation','exec'),{{'__name__':'__main__','TRUSTED_HELPER_BYTES':s}})"
    result = subprocess.run(
        [sys.executable, "-I", "-c", loader, baseline, "--repo", "owner/repo", "--pr", "17"], cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode == 2
    assert "unreviewed replacement" not in result.stderr
    assert "eligibility must be established" in json.loads(result.stdout)["reason"]
