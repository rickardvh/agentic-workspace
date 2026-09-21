"""Read-only admission of unchanged, previously merged stack trees.

GitHub merge records and successful semver workflow runs supply prior admission;
branch names, labels and PR prose cannot grant the exception. Discovery is bounded
to the 500 most recently updated closed PRs and fails closed outside that window.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
import zipfile
from pathlib import Path
from typing import Any, Callable

BUMP_ORDER = {"patch": 0, "minor": 1, "major": 2}
WORKFLOW = ".github/workflows/pr-semver-label.yml"
ADMISSION_KIND = "agentic-workspace/pr-semver-admission/v1"
ADMISSION_FILE = "semver-admission.json"
MAX_ARTIFACT_BYTES = 1024 * 1024


def github(endpoint: str) -> Any:
    return json.loads(github_bytes(endpoint))


def github_bytes(endpoint: str) -> bytes:
    return subprocess.run(["gh", "api", endpoint], check=True, capture_output=True, timeout=60).stdout


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, encoding="utf-8", timeout=30).stdout.strip()


def ancestor(root: Path, commit: str, descendant: str) -> bool:
    return (
        subprocess.run(["git", "merge-base", "--is-ancestor", commit, descendant], cwd=root, capture_output=True, timeout=30).returncode
        == 0
    )


def make_admission(*, root: Path, event: dict, payloads: dict, label: str | None, mode: str, run_id: int, attempt: int) -> dict:
    """Snapshot the semver owner's successful decision, before provider PR links disappear.

    The workflow calls this only after validation and uploads it in the same run.
    A local JSON file alone has no publication or prior-admission authority.
    """
    pr = event["pull_request"]
    head, base = pr["head"]["sha"], pr["base"]["sha"]
    return {
        "kind": ADMISSION_KIND,
        "repository": pr["base"]["repo"]["full_name"],
        "pull_request": {"number": pr["number"], "head_sha": head, "base_sha": base},
        "producer": {"workflow": WORKFLOW, "run_id": run_id, "attempt": attempt},
        "head_tree": git(root, "rev-parse", f"{head}^{{tree}}"),
        "merge_base": git(root, "merge-base", base, head),
        "mode": mode,
        "label": label,
        "changesets": {
            path: {"bump": payload["bump"], "git_entry": git(root, "ls-tree", head, "--", path)} for path, payload in payloads.items()
        },
    }


def retained_admission(*, root: Path, repository: str, candidate: dict, run: dict, api: Callable, download: Callable) -> dict | None:
    """Read one immutable run artifact, never mutable post-merge PR associations."""
    run_id, attempt = run["id"], run["run_attempt"]
    artifacts = api(f"repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100")["artifacts"]
    matching = [a for a in artifacts if a["name"] == f"semver-admission-{run_id}-{attempt}"]
    if len(matching) != 1:
        return None
    artifact = matching[0]
    if (
        artifact.get("expired") is not False
        or not 0 < artifact.get("size_in_bytes", 0) <= MAX_ARTIFACT_BYTES
        or artifact.get("created_at", "~") > candidate["merged_at"]
        or not re.fullmatch(r"sha256:[0-9a-f]{64}", artifact.get("digest", ""))
    ):
        return None
    raw = download(f"repos/{repository}/actions/artifacts/{artifact['id']}/zip")
    if len(raw) > MAX_ARTIFACT_BYTES or "sha256:" + hashlib.sha256(raw).hexdigest() != artifact["digest"]:
        raise ValueError("Semver admission artifact digest mismatch or oversized archive.")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        files = archive.infolist()
        if len(files) != 1 or files[0].filename != ADMISSION_FILE or files[0].file_size > MAX_ARTIFACT_BYTES:
            raise ValueError("Semver admission archive must contain one bounded admission file.")
        record = json.loads(archive.read(files[0]))
    head, base = candidate["head"]["sha"], candidate["base"]["sha"]
    if (
        record.get("kind") != ADMISSION_KIND
        or record.get("repository") != repository
        or record.get("producer") != {"workflow": WORKFLOW, "run_id": run_id, "attempt": attempt}
        or record.get("pull_request") != {"number": candidate["number"], "head_sha": head, "base_sha": base}
        or record.get("head_tree") != git(root, "rev-parse", f"{head}^{{tree}}")
        or record.get("merge_base") != git(root, "merge-base", base, head)
        or record.get("mode") not in {"ordinary", "integration", "not-required", "release"}
        or not isinstance(record.get("changesets"), dict)
    ):
        return None
    if record["mode"] in {"not-required", "release"}:
        return record if not record["changesets"] else None
    bump = str(record.get("label", "")).removeprefix("semver:")
    if bump not in BUMP_ORDER or not record["changesets"]:
        return None
    for entry in record["changesets"].values():
        if not isinstance(entry, dict) or entry.get("bump") not in BUMP_ORDER:
            return None
        if (record["mode"] == "ordinary" and entry["bump"] != bump) or BUMP_ORDER[entry["bump"]] > BUMP_ORDER[bump]:
            return None
    return record


def admit_exact_tree_integration(
    *,
    root: Path,
    event: dict,
    changesets: dict[str, str],
    expected_bump: str,
    api: Callable[[str], Any] | None = None,
    download: Callable[[str], bytes] | None = None,
) -> dict:
    """Return bounded evidence or reject; never mutate Git, PRs or changesets."""
    api = api or github
    download = download or github_bytes
    if not changesets or any(bump not in BUMP_ORDER for bump in changesets.values()):
        raise ValueError("Integration requires valid retained release changesets.")
    highest = max(changesets.values(), key=BUMP_ORDER.__getitem__)
    if expected_bump not in BUMP_ORDER or BUMP_ORDER[expected_bump] < BUMP_ORDER[highest]:
        raise ValueError("Integration semver label is lower than the highest retained changeset bump.")
    pr = event["pull_request"]
    repository = pr["base"]["repo"]["full_name"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid repository identity.")
    head, base = pr["head"]["sha"], pr["base"]["sha"]
    if not all(re.fullmatch(r"[0-9a-f]{40}", sha) for sha in (head, base)):
        raise ValueError("Exact GitHub head and base commits are required.")
    tree = git(root, "rev-parse", f"{head}^{{tree}}")
    # The workflow checks out GitHub's synthetic merge. Base-side changes and
    # conflict resolution must not introduce even a non-product tree delta.
    if git(root, "rev-parse", "HEAD^{tree}") != tree or git(root, "merge-tree", "--write-tree", base, head).splitlines()[0] != tree:
        raise ValueError("Integration merge result differs from the proposed source tree.")
    prefix = f"repos/{repository}"
    admitted: dict[str, int] = {}
    source_pr = None
    for page in range(1, 6):
        candidates = api(f"{prefix}/pulls?state=closed&sort=updated&direction=desc&per_page=100&page={page}")
        for candidate in candidates:
            sha = candidate["head"]["sha"]
            if (
                candidate["number"] == pr["number"]
                or not candidate.get("merged_at")
                or candidate["base"]["repo"]["full_name"] != repository
                or (candidate["head"].get("repo") or {}).get("full_name") != repository
                or not re.fullmatch(r"[0-9a-f]{40}", sha)
                or not re.fullmatch(r"[0-9a-f]{40}", candidate["base"].get("sha", ""))
                or not ancestor(root, sha, head)
                or ancestor(root, sha, base)
            ):
                continue
            runs = api(f"{prefix}/actions/workflows/pr-semver-label.yml/runs?head_sha={sha}&event=pull_request&per_page=100")
            for run in runs["workflow_runs"]:
                if not (
                    run.get("conclusion") == "success"
                    and run.get("event") == "pull_request"
                    and run.get("path") == WORKFLOW
                    and run.get("head_sha") == sha
                    and (run.get("head_repository") or {}).get("full_name") == repository
                    and run.get("updated_at", "~") <= candidate["merged_at"]
                ):
                    continue
                record = retained_admission(root=root, repository=repository, candidate=candidate, run=run, api=api, download=download)
                if record is None:
                    continue
                if record["head_tree"] == tree:
                    source_pr = candidate["number"]
                for path, entry in record["changesets"].items():
                    if (
                        path in changesets
                        and entry["bump"] == changesets[path]
                        and entry["git_entry"] == git(root, "ls-tree", sha, "--", path)
                        and entry["git_entry"] == git(root, "ls-tree", head, "--", path)
                    ):
                        admitted[path] = candidate["number"]
                if source_pr is not None and set(admitted) == set(changesets):
                    return {"source_pr": source_pr, "tree": tree, "changeset_admissions": admitted, "highest_bump": highest}
        if len(candidates) < 100:
            break
    raise ValueError("Mixed changesets require an exact merged source tree and prior semver admission for every retained changeset.")
