"""Semver admission distinguishes new work from unchanged admitted stack trees."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import re
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pr_semver_integration", ROOT / "src/tooling/release/pr_semver_integration.py")
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

    records, runs, artifacts, archives = {}, {}, {}, {}

    def package(number):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(checker.ADMISSION_FILE, json.dumps(records[number]))
        archives[number] = buffer.getvalue()
        artifacts[number] = {
            "id": number,
            "name": f"semver-admission-{number}-1",
            "expired": False,
            "size_in_bytes": len(archives[number]),
            "digest": "sha256:" + hashlib.sha256(archives[number]).hexdigest(),
            "created_at": "2026-09-19T15:00:00Z",
        }

    for pr in prs:
        number = pr["number"]
        records[number] = checker.make_admission(
            root=tmp_path,
            event={"pull_request": pr},
            payloads={f".release/changes/{number}.toml": {"bump": paths[f".release/changes/{number}.toml"]}},
            label=f"semver:{paths[f'.release/changes/{number}.toml']}",
            mode="ordinary",
            run_id=number,
            attempt=1,
        )
        runs[number] = {
            "id": number,
            "run_attempt": 1,
            "conclusion": "success",
            "event": "pull_request",
            "path": checker.WORKFLOW,
            "head_sha": pr["head"]["sha"],
            "head_repository": {"full_name": "owner/repo"},
            "updated_at": "2026-09-19T15:00:00Z",
            "pull_requests": [],
        }
        package(number)

    def api(endpoint):
        if "/pulls?" in endpoint:
            return copy.deepcopy(prs)
        if "/runs?" in endpoint:
            sha = endpoint.split("head_sha=")[1].split("&")[0]
            return {"workflow_runs": copy.deepcopy([run for run in runs.values() if run["head_sha"] == sha])}
        number = int(re.search(r"/runs/(\d+)/artifacts", endpoint)[1])
        return {"artifacts": [copy.deepcopy(artifacts[number])] if number in artifacts else []}

    def download(endpoint):
        return archives[int(re.search(r"/artifacts/(\d+)/zip", endpoint)[1])]

    monkeypatch.chdir(tmp_path)
    return (
        tmp_path,
        git,
        event,
        paths,
        prs,
        {
            "api": api,
            "download": download,
            "records": records,
            "runs": runs,
            "artifacts": artifacts,
            "archives": archives,
            "package": package,
        },
    )


@pytest.mark.parametrize("associations", ["empty", "missing"])
@pytest.mark.parametrize("workflow", checker.ADMISSION_WORKFLOWS)
def test_exact_tree_mixed_changesets_reuse_admission_after_merge(stack, associations, workflow):
    root, git, event, paths, _, provider = stack
    for number, run in provider["runs"].items():
        run["path"] = workflow
        provider["records"][number]["producer"]["workflow"] = workflow
        provider["package"](number)
    # Reproduce GitHub's observed lifetime: merged PRs no longer have run links.
    if associations == "missing":
        for run in provider["runs"].values():
            del run["pull_requests"]
    before = git("status", "--porcelain")
    result = checker.admit_exact_tree_integration(
        root=root, event=event, changesets=paths, expected_bump="minor", api=provider["api"], download=provider["download"]
    )
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
        "missing-artifact",
        "expired-artifact",
        "late-artifact",
        "wrong-producer-run",
        "wrong-producer-attempt",
        "wrong-artifact-digest",
        "wrong-tree",
        "unadmitted-changeset",
        "wrong-git-object",
    ],
)
def test_integration_exception_fails_closed(stack, defect):
    root, git, event, paths, prs, provider = stack
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

    for number in (1, 2):
        run = provider["runs"][number]
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
            provider["records"][number]["pull_request"]["number"] = 999
        elif defect == "different-base":
            provider["records"][number]["pull_request"]["base_sha"] = "0" * 40
        elif defect == "different-head":
            provider["records"][number]["pull_request"]["head_sha"] = "0" * 40
        elif defect == "wrong-producer-run":
            provider["records"][number]["producer"]["run_id"] = 999
        elif defect == "wrong-producer-attempt":
            provider["records"][number]["producer"]["attempt"] = 2
        elif defect == "wrong-tree":
            provider["records"][number]["head_tree"] = "0" * 40
        elif defect == "unadmitted-changeset":
            provider["records"][number]["changesets"] = {}
        elif defect == "wrong-git-object":
            provider["records"][number]["changesets"][f".release/changes/{number}.toml"]["git_entry"] = "forged"
        provider["package"](number)
        if defect == "missing-artifact":
            del provider["artifacts"][number]
        elif defect == "expired-artifact":
            provider["artifacts"][number]["expired"] = True
        elif defect == "late-artifact":
            provider["artifacts"][number]["created_at"] = "2026-09-20T00:00:00Z"
        elif defect == "wrong-artifact-digest":
            provider["artifacts"][number]["digest"] = "sha256:" + "0" * 64

    with pytest.raises(ValueError):
        checker.admit_exact_tree_integration(
            root=root, event=event, changesets=paths, expected_bump=expected, api=provider["api"], download=provider["download"]
        )


@pytest.mark.parametrize(
    "mode", ["ordinary", "base-advanced", "non-package", "mixed-ordinary", "integration", "missing-label", "multiple-labels"]
)
def test_workflow_preserves_ordinary_semver_discipline(stack, monkeypatch, mode):
    monkeypatch.syspath_prepend(str(ROOT / "src/tooling"))
    monkeypatch.setitem(sys.modules, "release.pr_semver_integration", checker)
    root, git, event, _, prs, provider = stack
    if mode in {"ordinary", "base-advanced"}:
        git("checkout", "--detach", prs[0]["head"]["sha"])
        event["pull_request"]["head"]["sha"] = git("rev-parse", "HEAD")
        event["pull_request"]["labels"] = [{"name": "semver:patch"}]
        if mode == "base-advanced":
            git("update-ref", "refs/heads/master", event["pull_request"]["head"]["sha"])
    elif mode == "non-package":
        event["pull_request"]["base"]["sha"] = git("rev-parse", "HEAD")
        (root / "note.md").write_text("Documentation only.")
        git("add", "note.md")
        git("commit", "-qm", "documentation")
        event["pull_request"]["head"]["sha"] = git("rev-parse", "HEAD")
    elif mode == "missing-label":
        event["pull_request"]["labels"] = []
    elif mode == "multiple-labels":
        event["pull_request"]["labels"].append({"name": "semver:patch"})
    event_path = root / "event.json"
    event_path.write_text(json.dumps(event))
    monkeypatch.setenv("EVENT_PATH", str(event_path))
    monkeypatch.setenv("BASE_REF", "master")
    monkeypatch.setenv("HEAD_REF", "claimed-integration")
    monkeypatch.setenv("SEMVER_ADMISSION_PATH", str(root / "semver-admission.json"))
    monkeypatch.setenv("GITHUB_RUN_ID", "3")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")

    def observed(endpoint):
        assert mode not in {"ordinary", "base-advanced", "non-package", "missing-label", "multiple-labels"}, (
            "Ordinary admission must remain local."
        )
        return provider["api"](endpoint) if mode == "integration" else []

    monkeypatch.setattr(checker, "github", observed)
    monkeypatch.setattr(checker, "github_bytes", provider["download"])
    workflow = (ROOT / ".github/workflows/pr-semver-label.yml").read_text()
    code = (ROOT / "src/tooling/release/pr_semver_admission.py").read_text()
    assert "if-no-files-found: error" in workflow
    assert "retention-days: 90" in workflow
    assert "overwrite: false" in workflow
    assert "semver-admission-${{ github.run_id }}-${{ github.run_attempt }}" in workflow
    if mode in {"ordinary", "integration", "base-advanced"}:
        exec(compile(code, "pr-semver-admission", "exec"), {"__name__": "__main__"})
        admission = json.loads((root / "semver-admission.json").read_text())
        assert admission["pull_request"] == {
            "number": 3,
            "head_sha": event["pull_request"]["head"]["sha"],
            "base_sha": event["pull_request"]["base"]["sha"],
        }
        assert admission["mode"] == ("ordinary" if mode == "base-advanced" else mode)
        assert admission["producer"] == {"workflow": checker.WORKFLOW, "run_id": 3, "attempt": 1}
        assert admission["changesets"]
    elif mode == "non-package":
        with pytest.raises(SystemExit) as error:
            exec(compile(code, "pr-semver-admission", "exec"), {"__name__": "__main__"})
        assert error.value.code == 0
        admission = json.loads((root / "semver-admission.json").read_text())
        assert admission["mode"] == "not-required"
        assert admission["changesets"] == {}
        assert admission["pull_request"]["head_sha"] == event["pull_request"]["head"]["sha"]
    else:
        with pytest.raises(SystemExit) as error:
            exec(compile(code, "pr-semver-admission", "exec"), {"__name__": "__main__"})
        assert error.value.code == 1
        assert not (root / "semver-admission.json").exists()
