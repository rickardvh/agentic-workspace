"""Read-only evidence collection; load these bytes from a selected trusted Git baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tomllib
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

HELPER = "tools/skills/pr-review-recheck/prepare.py"
PROCEDURE = "tools/skills/pr-review-recheck/SKILL.md"


def digest(value):
    data = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True).encode()
    return "sha256:" + hashlib.sha256(data).hexdigest()


def command(args):
    result = subprocess.run(args, capture_output=True, check=False)
    if result.returncode:
        raise ValueError(result.stderr.decode("utf-8", errors="replace").strip() or "command failed")
    return result.stdout


def git(*args):
    return command(["git", "--no-pager", *args])


def api(endpoint, *, collection=None):
    """All remote operations are GETs. Pagination is mandatory for collections."""
    args = ["gh", "api", "--method", "GET", endpoint]
    if collection is not None:
        args.extend(["--paginate", "--slurp"])
    data = json.loads(command(args))
    if collection is None:
        return data
    if not isinstance(data, list):
        raise ValueError("transport did not return paginated pages")
    rows = []
    for page in data:
        entries = page if collection == "list" else page[collection]
        if not isinstance(entries, list):
            raise ValueError("transport returned a malformed collection")
        rows.extend(entries)
    return rows


def observe(endpoint, *, collection=None, fields=None):
    try:
        data = api(endpoint, collection=collection)
        if fields is not None:

            def select(row):
                selected = {key: row.get(key) for key in fields}
                if isinstance(selected.get("user"), dict):
                    selected["user"] = selected["user"].get("login")
                return selected

            data = [select(row) for row in data] if collection is not None else select(data)
        return {"status": "observed", "source": endpoint, "revision": digest(data), "value": data}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {"status": "unavailable", "source": endpoint, "reason": str(exc)}


def guidance(baseline, files):
    paths = {"AGENTS.md", PROCEDURE, "docs/maintainer/testing-strategy.md", ".agentic-workspace/instructions/github-pr-review.md"}
    for file in files:
        for name in [file["filename"], file.get("previous_filename")]:
            if name:
                paths.update(str(parent / "AGENTS.md") for parent in PurePosixPath(name).parents)
    # Read exact Git objects only; no checkout, source helper import, or head execution.
    tree = set(git("ls-tree", "-r", "--name-only", baseline).decode().splitlines())
    refs = []
    for path in sorted(paths):
        if path not in tree:
            if path in {PROCEDURE, "docs/maintainer/testing-strategy.md"}:
                refs.append({"path": path, "baseline": baseline, "status": "unavailable", "reason": "required trusted guidance missing"})
            continue
        content = git("show", f"{baseline}:{path}")
        refs.append({"path": path, "baseline": baseline, "revision": digest(content), "source": "trusted-git-object", "status": "observed"})
    return refs


def references(body, repo):
    refs = {(repo, int(number)) for number in re.findall(r"(?<![\w/])#(\d+)\b", body)}
    refs.update((owner, int(number)) for owner, number in re.findall(r"\b([\w.-]+/[\w.-]+)#(\d+)\b", body))
    refs.update((owner, int(number)) for owner, number in re.findall(r"https://github\.com/([\w.-]+/[\w.-]+)/issues/(\d+)\b", body))
    return sorted(refs)


def followup(prefix, previous_head, head):
    """Bounded exact-head patches; never mistake a merge-base diff for a tree diff."""
    endpoint = f"{prefix}/compare/{previous_head}...{head}?per_page=1&page=1"
    result = {"source": endpoint, "from_head": previous_head, "to_head": head}
    try:
        if previous_head == head:
            files = []
        else:
            comparison = api(endpoint)
            if comparison["base_commit"]["sha"] != previous_head or comparison["merge_base_commit"]["sha"] != previous_head:
                raise ValueError("prior head is not the merge base; exact tree delta unavailable after divergent history")
            # GitHub returns all comparison files on page one, capped at 300,
            # independently of commit pagination. At the cap completeness is unknown.
            files = comparison["files"]
            if not isinstance(files, list) or len(files) >= 300 or len({row["filename"] for row in files}) != len(files):
                raise ValueError("comparison file inventory is incomplete or at the transport cap")
            for row in files:
                patch = row.get("patch", "")
                if (
                    sum(line.startswith("+") for line in patch.splitlines()) != row["additions"]
                    or sum(line.startswith("-") for line in patch.splitlines()) != row["deletions"]
                ):
                    raise ValueError(f"missing or incomplete text patch: {row['filename']}")
                if "patch" not in row:
                    raise ValueError(f"patch unavailable (possibly binary): {row['filename']}")
            files = [
                {key: row.get(key) for key in ["filename", "previous_filename", "sha", "status", "additions", "deletions", "patch"]}
                for row in files
            ]
        result.update(status="observed", value=files, revision=digest(files))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result.update(
            status="unavailable",
            reason=str(exc),
            recovery="Inspect an exact prior-head to current-head tree diff manually; do not infer an empty follow-up delta.",
        )
    return result


def layer_currentness(base, head, files, declarations, owner_evidence=()):
    """Bind reported owner evidence to this PR, never to a downstream stack head.

    Declarations select checks; this collector does not interpret domain state.
    Evidence is supplied by the independent reviewer after the existing owner
    check, and remains reported evidence rather than a review verdict.
    """
    changed = {name for row in files for name in (row["filename"], row.get("previous_filename")) if name}
    obligations = []
    for declaration in declarations:
        touched = sorted(changed.intersection(declaration["sources"]))
        if not touched:
            continue
        matching = [
            row
            for row in owner_evidence
            if row.get("base") == base
            and row.get("head") == head
            and row.get("owner") == declaration["owner"]
            and row.get("check") == declaration["check"]
        ]
        evidence = matching[0] if len(matching) == 1 else None
        status = evidence.get("status") if evidence else "unknown"
        if status not in {"current", "stale"} or not (evidence or {}).get("evidence_ref"):
            status = "unknown"
        obligations.append(
            {
                "owner": declaration["owner"],
                "check": declaration["check"],
                "base": base,
                "head": head,
                "paths": touched,
                "status": status,
                "evidence": evidence,
                "boundary": "reported owner result for this PR only; not independent review or integration proof",
            }
        )
    return obligations


def currentness_declarations(baseline):
    # The trusted repository's existing System Intent source declaration selects
    # the check. Additional owners are admitted as explicit reviewer obligations.
    path = ".agentic-workspace/system-intent/intent.toml"
    tree = set(git("ls-tree", "-r", "--name-only", baseline).decode().splitlines())
    if path not in tree:
        return []
    source = tomllib.loads(git("show", f"{baseline}:{path}").decode("utf-8"))
    return [
        {
            "owner": "system_intent",
            "check": "system_intent current source reconciliation",
            "sources": [row["path"] for row in source.get("source_records", []) if "path" in row] + [path],
        }
    ]


def prepare(repo, number, baseline, *, previous=None, owner_evidence=(), owner_obligations=()):
    started = datetime.now(timezone.utc).isoformat()
    prefix = f"repos/{repo}"
    subject = observe(f"{prefix}/pulls/{number}")
    packet = {
        "kind": "agentic-workspace/review-preparation/v1",
        "status": "unavailable",
        "authority": "evidence only; eligibility, correctness, proof sufficiency and verdict remain reviewer judgments",
        "delta_scope": "REVIEW_ONLY",
        "repository": repo,
        "number": number,
        "trusted_baseline": baseline,
        "observed_from": started,
        "subject": subject,
        "obligations": [],
        "evidence": {},
    }
    if subject["status"] != "observed":
        return packet
    pr = subject["value"]
    head, base = pr["head"]["sha"], pr["base"]["sha"]
    if pr["base"]["repo"]["full_name"].lower() != repo.lower() or pr["number"] != number:
        raise ValueError("remote subject does not match the requested repository/PR")
    subject["value"] = {
        "repository": repo,
        "number": number,
        "base": base,
        "head": head,
        "head_repository": (pr["head"].get("repo") or {}).get("full_name"),
        "title": pr["title"],
        "body": pr.get("body") or "",
        "state": pr["state"],
        "draft": pr.get("draft"),
        "merged": pr.get("merged"),
        "url": pr["html_url"],
        "changed_files": pr["changed_files"],
    }
    subject["revision"] = digest(subject["value"])
    evidence = packet["evidence"]
    usable_previous = (
        isinstance(previous, dict)
        and previous.get("kind") == packet["kind"]
        and previous.get("repository") == repo
        and previous.get("number") == number
        and isinstance(previous.get("identities"), dict)
        and isinstance(previous.get("obligations"), list)
        and isinstance(previous.get("file_identities"), dict)
        and isinstance(previous.get("subject"), dict)
        and isinstance(previous["subject"].get("value"), dict)
        and re.fullmatch(r"[0-9a-f]{40}", str(previous["subject"]["value"].get("head", ""))) is not None
    )
    if usable_previous:
        evidence["followup_patch"] = followup(prefix, previous["subject"]["value"]["head"], head)
    evidence["files"] = observe(
        f"{prefix}/pulls/{number}/files?per_page=100",
        collection="list",
        fields=["filename", "previous_filename", "sha", "status", "additions", "deletions", "changes"],
    )
    evidence["reviews"] = observe(
        f"{prefix}/pulls/{number}/reviews?per_page=100",
        collection="list",
        fields=["id", "user", "body", "state", "commit_id", "submitted_at", "html_url"],
    )
    evidence["inline_comments"] = observe(
        f"{prefix}/pulls/{number}/comments?per_page=100",
        collection="list",
        fields=["id", "user", "body", "path", "line", "original_line", "commit_id", "updated_at", "in_reply_to_id", "html_url"],
    )
    evidence["comments"] = observe(
        f"{prefix}/issues/{number}/comments?per_page=100", collection="list", fields=["id", "user", "body", "updated_at", "html_url"]
    )
    evidence["checks"] = observe(
        f"{prefix}/commits/{head}/check-runs?per_page=100&filter=all",
        collection="check_runs",
        fields=["id", "name", "head_sha", "status", "conclusion", "started_at", "completed_at", "details_url", "output"],
    )
    evidence["statuses"] = observe(
        f"{prefix}/commits/{head}/statuses?per_page=100",
        collection="list",
        fields=["id", "context", "state", "description", "updated_at", "target_url"],
    )
    files = evidence["files"].get("value", [])
    if evidence["files"]["status"] == "observed" and (
        len(files) != pr["changed_files"] or len({row["filename"] for row in files}) != len(files)
    ):
        evidence["files"]["status"] = "unavailable"
        evidence["files"]["reason"] = "incomplete or duplicate changed-file set; transport limit or moved subject"
    packet["guidance"] = guidance(baseline, files)
    packet["owner_currentness"] = layer_currentness(
        base, head, files, [*currentness_declarations(baseline), *owner_obligations], owner_evidence
    )
    packet["helper"] = {"path": HELPER, "baseline": baseline, "revision": digest(git("show", f"{baseline}:{HELPER}"))}
    packet["linked_references"] = [{"repository": owner, "number": issue} for owner, issue in references(pr.get("body") or "", repo)]
    for owner, issue in references(pr.get("body") or "", repo):
        evidence[f"issue:{owner}#{issue}"] = observe(
            f"repos/{owner}/issues/{issue}", fields=["number", "title", "body", "state", "updated_at", "html_url", "labels"]
        )
    # Bracket collection with a fresh subject read. This is an observation interval,
    # not an atomic GitHub snapshot or a reusable external-state admission.
    final = observe(f"{prefix}/pulls/{number}")
    packet["status"] = "observed" if all(item["status"] == "observed" for item in evidence.values()) else "partial"
    if any(item["status"] != "observed" for item in packet["guidance"]):
        packet["status"] = "partial"
    packet["subject_unavailable_fields"] = [key for key in ["draft", "merged"] if not isinstance(pr.get(key), bool)]
    if packet["subject_unavailable_fields"]:
        packet["status"] = "partial"
    if final["status"] != "observed":
        packet["status"] = "partial"
    elif any(
        final["value"].get(key) != pr.get(key) for key in ["head", "base", "body", "title", "state", "draft", "merged", "changed_files"]
    ):
        packet["status"] = "stale"
    packet["subject_recheck"] = {key: value for key, value in final.items() if key != "value"}
    packet["observed_until"] = datetime.now(timezone.utc).isoformat()
    identities = {key: digest(value) for key, value in evidence.items()}
    identities.update(subject=subject["revision"], guidance=digest(packet["guidance"]), helper=packet["helper"]["revision"])
    packet["identities"] = identities
    packet["file_identities"] = {row["filename"]: digest(row) for row in files}
    packet["delta"] = {"mode": "full", "reason": "no usable prior comparison"}
    if usable_previous:
        prior = previous["identities"]
        packet["obligations"] = previous["obligations"]
        packet["delta"] = {
            "mode": "recheck",
            "prior_subject": previous.get("subject"),
            "changed": [key for key in identities if key in prior and identities[key] != prior[key]],
            "added": sorted(identities.keys() - prior.keys()),
            "removed": sorted(prior.keys() - identities.keys()),
            "obligation_boundary": "preserved comparison input; only the independent reviewer can resolve obligations",
        }
        old_files = previous["file_identities"]
        new_files = packet["file_identities"]
        packet["delta"]["files"] = {
            "added": sorted(new_files.keys() - old_files.keys()),
            "removed": sorted(old_files.keys() - new_files.keys()),
            "changed": sorted(key for key in new_files.keys() & old_files.keys() if new_files[key] != old_files[key]),
        }
        for key, observation in evidence.items():
            if key in prior and identities[key] == prior[key] and observation["status"] == "observed":
                observation.pop("value", None)
                observation["unchanged_from"] = prior[key]
    return packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", help="Exact trusted full Git commit identity, explicitly selected by the reviewer")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--eligibility", choices=["independent", "ineligible", "unknown"], default="unknown")
    parser.add_argument("--previous", type=Path)
    parser.add_argument(
        "--owner-evidence", type=Path, help="Reviewer-observed owner results with exact base/head/check and evidence_ref; never a verdict"
    )
    parser.add_argument(
        "--owner-obligations", type=Path, help="Named currentness-sensitive source/check obligations discovered by the independent reviewer"
    )
    args = parser.parse_args()
    try:
        if args.eligibility != "independent":
            raise ValueError("independent review eligibility must be established outside preparation; stop at the skill gate")
        if not re.fullmatch(r"[0-9a-f]{40}", args.baseline) or not re.fullmatch(r"[\w.-]+/[\w.-]+", args.repo) or args.pr < 1:
            raise ValueError("supply exact baseline SHA, owner/repository and positive PR number")
        trusted = git("show", f"{args.baseline}:{HELPER}")
        if globals().get("TRUSTED_HELPER_BYTES") != trusted:
            raise ValueError("use the trusted Git-object loader documented in the baseline skill, never the PR-head script")
        previous = json.loads(args.previous.read_text(encoding="utf-8")) if args.previous else None
        owner_evidence = json.loads(args.owner_evidence.read_text(encoding="utf-8")) if args.owner_evidence else []
        owner_obligations = json.loads(args.owner_obligations.read_text(encoding="utf-8")) if args.owner_obligations else []
        result = prepare(
            args.repo, args.pr, args.baseline, previous=previous, owner_evidence=owner_evidence, owner_obligations=owner_obligations
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {
            "status": "unavailable",
            "reason": str(exc),
            "recovery": "Use the trusted skill's manual read-only preparation; no review authority is implied.",
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "observed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
