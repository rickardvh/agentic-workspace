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
        base_status = (evidence or {}).get("base_status", "unknown")
        if base_status not in {"current", "stale"} or not (evidence or {}).get("base_evidence_ref"):
            base_status = "unknown"
        obligations.append(
            {
                "owner": declaration["owner"],
                "check": declaration["check"],
                "base": base,
                "head": head,
                "paths": touched,
                "status": status,
                "evidence": evidence,
                "base_status": base_status,
                "attribution": "resolved"
                if status == "current"
                else "inherited"
                if base_status == "stale"
                else "introduced"
                if base_status == "current"
                else "unknown",
                "declaration": declaration.get("declaration"),
                "relation_id": declaration.get("relation_id"),
                "trigger": "policy-source-change" if declaration.get("relation_id") in touched else "governing-source-change",
                "boundary": "reported owner result for this PR only; not independent review or integration proof",
            }
        )
    return obligations


def currentness_declarations(baseline):
    # Trusted source declarations nominate existing owners; the reviewer supplies
    # their exact observations. No domain state is inferred here.
    path = ".agentic-workspace/system-intent/intent.toml"
    tree = set(
        git("ls-tree", "-r", "--name-only", baseline, "--", path, ".agentic-workspace/config.toml", ".agentic-workspace/instructions")
        .decode()
        .splitlines()
    )
    declarations = []
    if path in tree:
        source = tomllib.loads(git("show", f"{baseline}:{path}").decode("utf-8"))
        declarations.append(
            {
                "owner": "system_intent",
                "check": "system_intent current source reconciliation",
                "sources": [row["path"] for row in source.get("source_records", []) if "path" in row] + [path],
            }
        )
    config_path = ".agentic-workspace/config.toml"
    config = tomllib.loads(git("show", f"{baseline}:{config_path}").decode("utf-8")) if config_path in tree else {}
    admitted = config.get("assurance", {}).get("instruction_revision")
    # Only repository instruction objects from the trusted snapshot and its
    # existing source-owner admission. No worktree scan or head helper executes.
    instruction_paths = sorted(
        name for name in tree if name.startswith(".agentic-workspace/instructions/") and name.endswith(".md") and name.count("/") == 2
    )
    if admitted:
        admitted_tree = set(git("ls-tree", "-r", "--name-only", admitted, "--", ".agentic-workspace/instructions").decode().splitlines())
        instruction_paths = sorted(
            set(instruction_paths)
            | {
                name
                for name in admitted_tree
                if name.startswith(".agentic-workspace/instructions/") and name.endswith(".md") and name.count("/") == 2
            }
        )
    for instruction in instruction_paths:
        current = git("show", f"{baseline}:{instruction}") if instruction in tree else None
        content = git("show", f"{admitted}:{instruction}") if admitted and instruction in admitted_tree else current
        if content is None:
            continue
        sources = governing_sources(content)
        if not sources:
            continue
        declarations.append(
            {
                "owner": "verification",
                "check": f"Verification source reconciliation: {instruction}",
                "relation_id": instruction,
                "sources": [*sources, instruction],
                "declaration": {
                    "path": instruction,
                    "baseline": baseline,
                    "revision": digest(content),
                    "admitted_revision": admitted,
                    "baseline_revision": digest(current) if current is not None else None,
                    "snapshot": "admitted" if admitted else "trusted-baseline-only",
                    "matches_baseline": content == current,
                },
            }
        )
    return declarations


def governing_sources(content):
    """Nominate existing relations from the scoped instruction list syntax.

    This reads source names only; Verification interprets currentness, scope and
    semantic reconciliation. Unsupported metadata is a collection gap.
    """
    lines = content.decode("utf-8").splitlines()
    if not lines or lines[0] != "---":
        return []
    fields, field = {}, None
    for line in lines[1:]:
        if line == "---":
            return fields.get("governed_by", [])
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        if not line.startswith((" ", "-")) and ":" in value:
            field, rest = value.split(":", 1)
            if field in fields or field not in {"paths", "routes", "read", "reconcile", "governed_by", "use", "checks", "protect"}:
                raise ValueError("unsupported trusted scoped instruction metadata")
            fields[field] = []
            rest = rest.strip()
            if not rest:
                continue
            if not (rest.startswith("[") and rest.endswith("]")):
                raise ValueError("unsupported trusted scoped instruction list")
            values = [item.strip() for item in rest[1:-1].split(",") if item.strip()]
        else:
            if field is None or not value.startswith("-"):
                raise ValueError("unsupported trusted scoped instruction item")
            values = [value[1:].strip()]
        for value in values:
            value = value.strip("'\"")
            if field == "governed_by" and (
                not value
                or value.startswith(("/", "~"))
                or any(char in value for char in "\\:*?[]")
                or any(part in {"", ".", ".."} for part in value.split("/"))
            ):
                raise ValueError("invalid trusted governing source reference")
            fields[field].append(value)
    raise ValueError("unterminated trusted scoped instruction metadata")


def implementation_scope(repo, *, number=None, base_ref=None, head_ref="HEAD", cumulative=False):
    """Observe the same direct PR subject as review without conducting a review.

    Before publication, the caller supplies the explicitly established parent.
    There is no inferred default branch, cached topology or evidence admission.
    """
    packet = {
        "kind": "agentic-workspace/implementation-scope/v1",
        "status": "unavailable",
        "authority": "changed-path observation only; no proof, currentness, review or completion authority",
        "scope_kind": "cumulative-integration" if cumulative else "layer",
        "repository": repo,
        "observed_from": datetime.now(timezone.utc).isoformat(),
    }
    if number is not None:
        if base_ref is not None or cumulative:
            raise ValueError("a PR layer uses its provider base; cumulative integration requires an explicit base instead")
        endpoint = f"repos/{repo}/pulls/{number}"
        subject = observe(endpoint)
        packet["subject"] = subject
        if subject["status"] != "observed":
            return packet
        pr = subject["value"]
        if pr["base"]["repo"]["full_name"].lower() != repo.lower() or pr["number"] != number:
            raise ValueError("remote subject does not match the requested repository/PR")
        identity = {
            "repository": repo,
            "number": number,
            "base": pr["base"]["sha"],
            "head": pr["head"]["sha"],
            "base_branch": pr["base"]["ref"],
            "head_branch": pr["head"]["ref"],
        }
        subject["value"] = identity
        subject["revision"] = digest(identity)
        files = observe(f"{endpoint}/files?per_page=100", collection="list", fields=["filename", "previous_filename"])
        packet["files"] = files
        rows = files.get("value", [])
        if files["status"] == "observed" and (len(rows) != pr["changed_files"] or len({row["filename"] for row in rows}) != len(rows)):
            files.update(status="unavailable", reason="incomplete or duplicate changed-file set; transport limit or moved subject")
        final = observe(endpoint)
        packet["subject_recheck"] = {key: value for key, value in final.items() if key != "value"}
        packet["status"] = "observed" if files["status"] == final["status"] == "observed" else "unavailable"
        if final["status"] == "observed" and any(final["value"].get(key) != pr.get(key) for key in ["base", "head", "changed_files"]):
            packet["status"] = "stale"
        paths = {name for row in rows for name in (row["filename"], row.get("previous_filename")) if name}
    else:
        if not base_ref:
            raise ValueError("layer base is unknown; supply its live PR or explicitly established parent, never infer master")

        def commit(ref):
            return git("rev-parse", "--verify", f"{ref}^{{commit}}").decode().strip()

        base, head = commit(base_ref), commit(head_ref)
        packet["subject"] = {
            "source": "explicit-established-parent",
            "value": {"repository": repo, "base": base, "head": head, "base_ref": base_ref, "head_ref": head_ref},
        }
        # Match PR changed-file semantics: direct parent identity, merge-base delta.
        # Renames expose both affected paths to existing source/proof routing.
        paths = set(git("diff", "--name-only", "--no-renames", "-z", f"{base}...{head}").decode().split("\0")) - {""}
        packet["status"] = "observed" if (commit(base_ref), commit(head_ref)) == (base, head) else "stale"
    if packet["status"] == "observed":
        packet["changed"] = sorted(paths)
    packet["observed_until"] = datetime.now(timezone.utc).isoformat()
    return packet


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
    try:
        declarations = currentness_declarations(baseline)
        packet["owner_currentness_discovery"] = {"status": "observed", "baseline": baseline}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        declarations = []
        packet["owner_currentness_discovery"] = {"status": "unavailable", "reason": str(exc), "baseline": baseline}
    packet["owner_currentness"] = layer_currentness(base, head, files, [*declarations, *owner_obligations], owner_evidence)
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
    if packet["owner_currentness_discovery"]["status"] != "observed":
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
    identities.update(
        subject=subject["revision"],
        guidance=digest(packet["guidance"]),
        helper=packet["helper"]["revision"],
        owner_currentness=digest([packet["owner_currentness_discovery"], packet["owner_currentness"]]),
    )
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
    parser.add_argument("--pr", type=int)
    parser.add_argument("--implementation-scope", action="store_true", help="Read-only layer paths; does not invoke review")
    parser.add_argument("--base", help="Explicitly established parent before PR publication; never inferred")
    parser.add_argument("--head", default="HEAD", help="Local head for an explicit-parent subject")
    parser.add_argument("--cumulative-integration", action="store_true", help="Name a deliberate aggregate subject with --base")
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
        if not args.implementation_scope and args.eligibility != "independent":
            raise ValueError("independent review eligibility must be established outside preparation; stop at the skill gate")
        if (
            not re.fullmatch(r"[0-9a-f]{40}", args.baseline)
            or not re.fullmatch(r"[\w.-]+/[\w.-]+", args.repo)
            or (args.pr is not None and args.pr < 1)
        ):
            raise ValueError("supply exact baseline SHA, owner/repository and positive PR number")
        trusted = git("show", f"{args.baseline}:{HELPER}")
        if globals().get("TRUSTED_HELPER_BYTES") != trusted:
            raise ValueError("use the trusted Git-object loader documented in the baseline skill, never the PR-head script")
        if args.implementation_scope:
            result = implementation_scope(
                args.repo, number=args.pr, base_ref=args.base, head_ref=args.head, cumulative=args.cumulative_integration
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["status"] == "observed" else 2
        if args.pr is None or args.base is not None or args.cumulative_integration:
            raise ValueError("review requires --pr and uses its provider base/head")
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
