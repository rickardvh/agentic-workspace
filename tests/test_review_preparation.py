import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "tools/skills/pr-review-recheck/prepare.py"
SPEC = importlib.util.spec_from_file_location("review_preparation", PATH)
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)
BASELINE = "a" * 40


def test_two_layer_currentness_uses_the_owner_at_each_subject(tmp_path, shared_core_binary, native_cli):
    """One native owner scenario: upper repair cannot discharge lower source drift."""
    mirror = ".agentic-workspace/system-intent/intent.toml"
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text('[system_intent]\nsources=["SYSTEM_INTENT.md"]\npreferred_source="SYSTEM_INTENT.md"\n')
    source = tmp_path / "SYSTEM_INTENT.md"
    source.write_text("Keep tools quiet.\n")
    record = tmp_path / mirror
    record.parent.mkdir()

    def reconcile():
        record.write_text(
            'schema_version=1\nkind="agentic-workspace/system-intent/v1"\nsummary="Keep tools quiet"\nneeds_review=false\npreferred_source="SYSTEM_INTENT.md"\n[[source_records]]\npath="SYSTEM_INTENT.md"\npresent=true\nsha256="'
            + hashlib.sha256(source.read_text().encode()).hexdigest()
            + '"\n'
        )

    def observe(base, head):
        owner = consume("native", shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Check layer owner currentness"})[
            "system_intent"
        ]
        return {
            "owner": "system_intent",
            "check": "current source",
            "base": base,
            "head": head,
            "status": "current" if owner["interpretation"]["source_currentness"] == "matched" else "stale",
            "evidence_ref": owner["revision"],
        }

    declaration = [{"owner": "system_intent", "check": "current source", "sources": ["SYSTEM_INTENT.md", mirror]}]
    changed = [{"filename": "SYSTEM_INTENT.md"}]
    reconcile()
    assert observe("root", "base")["status"] == "current"
    source.write_text("Keep tools quiet; preserve human intent.\n")
    lower = observe("base", "A")
    assert lower["status"] == "stale"
    reconcile()
    upper = observe("A", "B")
    assert upper["status"] == "current"
    assert review.layer_currentness("base", "A", changed, declaration, [lower, upper])[0]["status"] == "stale"
    assert review.layer_currentness("base", "A", changed, declaration, [upper])[0]["status"] == "unknown"
    # Move the same reconciliation into A; rebased B adds no owner delta.
    repaired = observe("base", "A-fixed")
    assert review.layer_currentness("base", "A-fixed", changed, declaration, [repaired])[0]["status"] == "current"
    assert review.layer_currentness("A-fixed", "B-rebased", [], declaration, []) == []
    assert review.layer_currentness("base", "unrelated", [{"filename": "unrelated.txt"}], declaration, []) == []


@pytest.fixture
def remote(monkeypatch):
    pr = {
        "number": 17,
        "head": {"sha": "b" * 40, "repo": {"full_name": "fork/repo"}},
        "base": {"sha": "c" * 40, "repo": {"full_name": "owner/repo"}},
        "title": "Change",
        "body": "Closes #12",
        "state": "open",
        "draft": False,
        "merged": False,
        "html_url": "https://github.com/owner/repo/pull/17",
        "changed_files": 101,
    }
    files = [{"filename": f"src/file{n}.py", "sha": str(n), "status": "modified"} for n in range(101)]
    state = {"pr": pr, "files": files, "comments": [], "issue": {"number": 12, "body": "Outcome"}, "calls": []}

    def api(endpoint, *, collection=None):
        state["calls"].append(endpoint)
        if "/compare/" in endpoint:
            if state.get("compare_unavailable"):
                raise OSError("compare unavailable")
            return copy.deepcopy(state["comparison"])
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
    assert packet["subject"]["value"]["draft"] is False
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
    remote["comparison"] = {
        "base_commit": {"sha": "b" * 40},
        "merge_base_commit": {"sha": "b" * 40},
        "files": [
            {
                "filename": "src/file0.py",
                "sha": "new blob",
                "status": "modified",
                "additions": 1,
                "deletions": 1,
                "patch": "@@ -1 +1 @@\n-old code\n+fixed code",
            }
        ],
    }
    changed = review.prepare("owner/repo", 17, BASELINE, previous=first)
    patch = changed["evidence"]["followup_patch"]
    assert changed["status"] == "observed"
    assert patch["from_head"] == "b" * 40 and patch["to_head"] == "e" * 40
    assert patch["value"][0]["patch"] == "@@ -1 +1 @@\n-old code\n+fixed code"
    assert f"repos/owner/repo/compare/{'b' * 40}...{'e' * 40}?per_page=1&page=1" in remote["calls"]
    assert changed["obligations"] == first["obligations"]
    assert "issue:owner/repo#12" in changed["delta"]["changed"]
    assert changed["delta"]["files"] == {"added": [], "removed": [], "changed": ["src/file0.py"]}
    assert "guidance" not in changed["delta"]["changed"]
    remote["guidance"] = "Changed trusted procedure"
    assert "guidance" in review.prepare("owner/repo", 17, BASELINE, previous=changed)["delta"]["changed"]
    assert review.prepare("owner/repo", 17, BASELINE, previous={})["delta"]["mode"] == "full"
    remote["compare_unavailable"] = True
    unavailable = review.prepare("owner/repo", 17, BASELINE, previous=first)
    assert unavailable["status"] == "partial"
    assert unavailable["obligations"] == first["obligations"]
    assert unavailable["evidence"]["followup_patch"]["status"] == "unavailable"
    remote["compare_unavailable"] = False
    for mutation in [
        {"merge_base_commit": {"sha": "c" * 40}},
        {"files": remote["comparison"]["files"] * 300},
        {"files": [{**remote["comparison"]["files"][0], "patch": "@@ -1 +1 @@\n-old code"}]},
        {"files": [{"filename": "binary", "status": "modified", "additions": 0, "deletions": 0}]},
    ]:
        original = copy.deepcopy(remote["comparison"])
        remote["comparison"].update(mutation)
        assert review.prepare("owner/repo", 17, BASELINE, previous=first)["status"] == "partial"
        remote["comparison"] = original
    remote["move"] = True
    remote["calls"].clear()
    assert review.prepare("owner/repo", 17, BASELINE, previous=first)["status"] == "stale"


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


def test_review_owner_identity_uses_native_planning_selection(tmp_path, shared_core_binary, monkeypatch):
    from aw_maintainer.review_topology import current_review_owner_identity

    monkeypatch.setenv("AGENTIC_WORKSPACE_CORE_BINARY", str(shared_core_binary))
    assert current_review_owner_identity(tmp_path) == {}
    ref = ".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json"
    plan = tmp_path / ref
    plan.parent.mkdir(parents=True)
    plan.write_bytes((ROOT / ref).read_bytes())
    (plan.parent.parent / "state.toml").write_text(
        f'[[active.execplans]]\nid="delegation-lane-sweep"\npath="{ref}"\nstatus="active"\n', encoding="utf-8"
    )
    assert current_review_owner_identity(tmp_path) == {
        "owner_ref": ref,
        "owner_revision": "sha256:" + hashlib.sha256(plan.read_bytes()).hexdigest(),
    }
