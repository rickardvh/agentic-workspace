"""Read-only admission of unchanged, previously merged stack trees.

GitHub merge records and successful semver workflow runs supply prior admission;
branch names, labels and PR prose cannot grant the exception. Discovery is bounded
to the 500 most recently updated closed PRs and fails closed outside that window.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

BUMP_ORDER = {"patch": 0, "minor": 1, "major": 2}
WORKFLOW = ".github/workflows/pr-semver-label.yml"


def github(endpoint: str) -> Any:
    result = subprocess.run(["gh", "api", endpoint], check=True, capture_output=True, encoding="utf-8", timeout=60)
    return json.loads(result.stdout)


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, encoding="utf-8", timeout=30).stdout.strip()


def ancestor(root: Path, commit: str, descendant: str) -> bool:
    return (
        subprocess.run(["git", "merge-base", "--is-ancestor", commit, descendant], cwd=root, capture_output=True, timeout=30).returncode
        == 0
    )


def admit_exact_tree_integration(
    *, root: Path, event: dict, changesets: dict[str, str], expected_bump: str, api: Callable[[str], Any] | None = None
) -> dict:
    """Return bounded evidence or reject; never mutate Git, PRs or changesets."""
    api = api or github
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
                or not ancestor(root, sha, head)
                or ancestor(root, sha, base)
            ):
                continue
            runs = api(f"{prefix}/actions/workflows/pr-semver-label.yml/runs?head_sha={sha}&event=pull_request&per_page=100")
            # A label today is not proof that the original changeset was admitted.
            # Require a successful repository-owned workflow for that exact head
            # before its recorded merge; this also works for deleted stack refs.
            if not any(
                run.get("conclusion") == "success"
                and run.get("event") == "pull_request"
                and run.get("path") == WORKFLOW
                and run.get("head_sha") == sha
                and (run.get("head_repository") or {}).get("full_name") == repository
                and run.get("updated_at", "~") <= candidate["merged_at"]
                for run in runs["workflow_runs"]
            ):
                continue
            if git(root, "rev-parse", f"{sha}^{{tree}}") == tree:
                source_pr = candidate["number"]
            for file_page in range(1, 31):
                files = api(f"{prefix}/pulls/{candidate['number']}/files?per_page=100&page={file_page}")
                for file in files:
                    path = file["filename"]
                    if path in changesets and file["status"] in {"added", "modified", "renamed"}:
                        # Full Git object identity includes mode as well as blob;
                        # no rewriting accepted bump strings or summaries.
                        if git(root, "ls-tree", sha, "--", path) == git(root, "ls-tree", head, "--", path):
                            admitted[path] = candidate["number"]
                if len(files) < 100:
                    break
            if source_pr is not None and set(admitted) == set(changesets):
                return {"source_pr": source_pr, "tree": tree, "changeset_admissions": admitted, "highest_bump": highest}
        if len(candidates) < 100:
            break
    raise ValueError("Mixed changesets require an exact merged source tree and prior semver admission for every retained changeset.")
