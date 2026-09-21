"""Semver admission distinguishes new work from unchanged admitted stack trees."""

from __future__ import annotations

import copy
import importlib.util
import json
import re
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pr_semver_integration", ROOT / "scripts/release/pr_semver_integration.py")
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


@pytest.fixture
def stack(tmp_path, monkeypatch):
    def git(*args):
        return checker.git(tmp_path, *args)

    git("init", "-q", "-b", "master")
    git("config", "user.name", "Fixture")
    git("config", "user.email", "fixture@example.invalid")
    ownership = tmp_path / ".github/release-ownership.json"
    ownership.parent.mkdir()
    ownership.write_bytes((ROOT / ".github/release-ownership.json").read_bytes())
    git("add", ".")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    git("switch", "-qc", "stack")
    git("remote", "add", "origin", str(tmp_path))
    paths = {}
    prs = []
    for number, bump in enumerate(("patch", "minor"), 1):
        source_base = git("rev-parse", "HEAD")
        path = f".release/changes/{number}.toml"
        destination = tmp_path / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(f'schema_version="agentic-workspace/release-change/v1"\nbump="{bump}"\nsummary="Fix {number}"\n')
        git("add", ".")
        git("commit", "-qm", bump)
        sha = git("rev-parse", "HEAD")
        paths[path] = bump
        prs.append(
            {
                "number": number,
                "merged_at": "2026-09-19T16:00:00Z",
                "head": {"sha": sha, "repo": {"full_name": "owner/repo"}},
                "base": {"sha": source_base, "repo": {"full_name": "owner/repo"}},
            }
        )
    # Same accepted tree with a distinct aggregate commit, as in stack integration.
    git("commit", "--allow-empty", "-qm", "aggregate")
    event = {
        "pull_request": {
            "number": 3,
            "base": {"sha": base, "repo": {"full_name": "owner/repo"}},
            "head": {"sha": git("rev-parse", "HEAD")},
            "labels": [{"name": "semver:minor"}],
        }
    }

    def api(endpoint):
        if "/pulls?" in endpoint:
            return copy.deepcopy(prs)
        if "/runs?" in endpoint:
            sha = endpoint.split("head_sha=")[1].split("&")[0]
            return {
                "workflow_runs": [
                    {
                        "conclusion": "success",
                        "event": "pull_request",
                        "path": checker.WORKFLOW,
                        "head_sha": sha,
                        "head_repository": {"full_name": "owner/repo"},
                        "updated_at": "2026-09-19T15:00:00Z",
                        "pull_requests": [
                            {"number": pr["number"], "head": {"sha": sha}, "base": {"sha": pr["base"]["sha"]}}
                            for pr in prs
                            if pr["head"]["sha"] == sha
                        ],
                    }
                ]
            }
        number = int(re.search(r"/pulls/(\d+)/files", endpoint)[1])
        return [{"filename": f".release/changes/{number}.toml", "status": "added"}]

    monkeypatch.chdir(tmp_path)
    return tmp_path, git, event, paths, prs, api


def test_exact_tree_mixed_changesets_need_real_prior_admission(stack):
    root, git, event, paths, _, api = stack
    before = git("status", "--porcelain")
    result = checker.admit_exact_tree_integration(root=root, event=event, changesets=paths, expected_bump="minor", api=api)
    assert result["source_pr"] == 2
    assert result["highest_bump"] == "minor"
    assert result["changeset_admissions"] == {".release/changes/1.toml": 1, ".release/changes/2.toml": 2}
    assert git("status", "--porcelain") == before


@pytest.mark.parametrize(
    "defect",
    [
        "unmerged",
        "missing-admission",
        "wrong-workflow",
        "after-merge",
        "foreign-repo",
        "understated",
        "new-delta",
        "merge-delta",
        "changed-changeset",
        "different-pr",
        "different-base",
        "different-head",
        "missing-pr-association",
        "empty-pr-associations",
        "split-pr-association",
    ],
)
def test_integration_exception_fails_closed(stack, defect):
    root, git, event, paths, prs, api = stack
    expected = "minor"
    if defect == "unmerged":
        prs[1]["merged_at"] = None
    if defect == "understated":
        expected = "patch"
    if defect in {"new-delta", "merge-delta", "changed-changeset"}:
        path = root / (".release/changes/1.toml" if defect == "changed-changeset" else "smuggled.txt")
        path.write_text(path.read_text() + "# changed\n" if path.exists() else "New product content")
        git("add", ".")
        git("commit", "-qm", defect)
        if defect != "merge-delta":
            event["pull_request"]["head"]["sha"] = git("rev-parse", "HEAD")

    def altered(endpoint):
        result = api(endpoint)
        if "/runs?" in endpoint:
            run = result["workflow_runs"][0]
            if defect == "missing-admission":
                run["conclusion"] = "failure"
            elif defect == "wrong-workflow":
                run["path"] = ".github/workflows/unrelated.yml"
            elif defect == "after-merge":
                run["updated_at"] = "2026-09-20T00:00:00Z"
            elif defect == "foreign-repo":
                run["head_repository"]["full_name"] = "untrusted/repo"
            elif defect == "different-pr":
                # Same successful head, but the admitted diff belongs to a
                # different PR. It cannot authorize this candidate's files.
                run["pull_requests"][0]["number"] = 999
            elif defect == "different-base":
                run["pull_requests"][0]["base"]["sha"] = "0" * 40
            elif defect == "different-head":
                run["pull_requests"][0]["head"]["sha"] = "0" * 40
            elif defect == "missing-pr-association":
                del run["pull_requests"]
            elif defect == "empty-pr-associations":
                run["pull_requests"] = []
            elif defect == "split-pr-association":
                other = copy.deepcopy(run["pull_requests"][0])
                other["number"] = 999
                run["pull_requests"][0]["base"]["sha"] = "0" * 40
                run["pull_requests"].append(other)
        return result

    with pytest.raises(ValueError):
        checker.admit_exact_tree_integration(root=root, event=event, changesets=paths, expected_bump=expected, api=altered)


@pytest.mark.parametrize("mode", ["ordinary", "mixed-ordinary", "integration", "missing-label", "multiple-labels"])
def test_workflow_preserves_ordinary_semver_discipline(stack, monkeypatch, mode):
    monkeypatch.syspath_prepend(str(ROOT))
    monkeypatch.setitem(sys.modules, "scripts.release.pr_semver_integration", checker)
    root, git, event, _, prs, api = stack
    if mode == "ordinary":
        git("checkout", "--detach", prs[0]["head"]["sha"])
        event["pull_request"]["head"]["sha"] = git("rev-parse", "HEAD")
        event["pull_request"]["labels"] = [{"name": "semver:patch"}]
    elif mode == "missing-label":
        event["pull_request"]["labels"] = []
    elif mode == "multiple-labels":
        event["pull_request"]["labels"].append({"name": "semver:patch"})
    event_path = root / "event.json"
    event_path.write_text(json.dumps(event))
    monkeypatch.setenv("EVENT_PATH", str(event_path))
    monkeypatch.setenv("BASE_REF", "master")
    monkeypatch.setenv("HEAD_REF", "claimed-integration")

    def observed(endpoint):
        assert mode not in {"ordinary", "missing-label", "multiple-labels"}, "Ordinary admission must remain local."
        return api(endpoint) if mode == "integration" else []

    monkeypatch.setattr(checker, "github", observed)
    workflow = (ROOT / ".github/workflows/pr-semver-label.yml").read_text()
    code = textwrap.dedent(workflow.split("python - <<'PY'\n", 1)[1].rsplit("          PY", 1)[0])
    if mode in {"ordinary", "integration"}:
        exec(compile(code, "pr-semver-label", "exec"), {})
    else:
        with pytest.raises(SystemExit) as error:
            exec(compile(code, "pr-semver-label", "exec"), {})
        assert error.value.code == 1
