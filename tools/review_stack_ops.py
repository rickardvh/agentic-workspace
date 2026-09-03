from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

RECEIPT_KIND = "agentic-workspace/review-stack-restack-receipt/v1"
DECLARATION_KIND = "agentic-workspace/review-stack-restack/v1"
MERGE_RECEIPT_KIND = "agentic-workspace/review-stack-merge-receipt/v1"
FULL_SHA = re.compile(r"[0-9a-f]{40}")
BRANCH = re.compile(r"(?!-)(?!.*\.\.)(?!.*[~^:?*\\\[])\S+")


class StackError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class CommandRunner:
    def run(self, command: Sequence[str], *, cwd: Path, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(command),
            cwd=cwd,
            input=input_text,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )


def _run(
    runner: CommandRunner,
    command: Sequence[str],
    *,
    cwd: Path,
    code: str,
    input_text: str | None = None,
) -> str:
    completed = runner.run(command, cwd=cwd, input_text=input_text)
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}"
        raise StackError(code, f"{' '.join(command)} failed: {detail}")
    return completed.stdout.strip()


def _write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt["updated_at"] = datetime.now(timezone.utc).isoformat()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _require_sha(value: Any, field: str) -> str:
    text = str(value or "")
    if not FULL_SHA.fullmatch(text):
        raise StackError("invalid-declaration", f"{field} must be an explicit lowercase full SHA")
    return text


def _require_branch(value: Any, field: str) -> str:
    text = str(value or "")
    if not BRANCH.fullmatch(text) or text.endswith(("/", ".")) or text.startswith("refs/"):
        raise StackError("invalid-declaration", f"{field} is not a safe branch name")
    return text


def _load_declaration(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise StackError("declaration-unavailable", f"could not read stack declaration {path}: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("kind") != DECLARATION_KIND:
        raise StackError("invalid-declaration", f"stack declaration kind must be {DECLARATION_KIND}")
    base = payload.get("base")
    descendants = payload.get("descendants")
    if not isinstance(base, dict) or not isinstance(descendants, list) or not descendants:
        raise StackError("invalid-declaration", "a declared stack requires one base and at least one descendant")
    _require_sha(base.get("head"), "base.head")
    _require_branch(base.get("branch"), "base.branch")
    if int(base.get("pr_number", 0)) < 1:
        raise StackError("invalid-declaration", "base.pr_number must be positive")
    seen: set[str] = {str(base["branch"])}
    for index, raw in enumerate(descendants):
        if not isinstance(raw, dict):
            raise StackError("invalid-declaration", f"descendants[{index}] must be an object")
        branch = _require_branch(raw.get("branch"), f"descendants[{index}].branch")
        if branch in seen:
            raise StackError("invalid-declaration", f"branch {branch!r} is declared more than once")
        seen.add(branch)
        if int(raw.get("pr_number", 0)) < 1:
            raise StackError("invalid-declaration", f"descendants[{index}].pr_number must be positive")
        for field in ("old_base", "new_base", "old_remote_head"):
            _require_sha(raw.get(field), f"descendants[{index}].{field}")
    return payload


def _remote_head(root: Path, runner: CommandRunner, branch: str) -> str:
    output = _run(
        runner,
        ["git", "ls-remote", "--heads", "origin", f"refs/heads/{branch}"],
        cwd=root,
        code="remote-inspection-failed",
    )
    rows = [line.split() for line in output.splitlines() if line.strip()]
    if len(rows) != 1 or len(rows[0]) < 2 or not FULL_SHA.fullmatch(rows[0][0]):
        raise StackError("remote-head-ambiguous", f"origin branch {branch!r} did not resolve to exactly one full SHA")
    return rows[0][0]


def _patch_id(root: Path, runner: CommandRunner, base: str, head: str) -> str:
    patch = _run(runner, ["git", "diff", "--binary", base, head], cwd=root, code="patch-read-failed")
    if not patch:
        return hashlib.sha256(b"").hexdigest()
    output = _run(runner, ["git", "patch-id", "--stable"], cwd=root, code="patch-id-failed", input_text=patch)
    ids = [line.split()[0] for line in output.splitlines() if line.strip()]
    if not ids:
        raise StackError("patch-id-failed", "git patch-id returned no identity for a non-empty patch")
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def _update_pr_body(root: Path, runner: CommandRunner, *, pr: int, head: str) -> dict[str, Any]:
    raw = _run(runner, ["gh", "pr", "view", str(pr), "--json", "body,headRefOid"], cwd=root, code="pr-read-failed")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise StackError("pr-read-failed", f"GitHub returned invalid PR metadata for #{pr}") from exc
    if str(payload.get("headRefOid", "")) != head:
        raise StackError("pr-head-mismatch", f"PR #{pr} does not expose published head {head}")
    body = str(payload.get("body", ""))
    marker = f"<!-- aw-exact-head {head} -->"
    pattern = re.compile(r"<!-- aw-exact-head [0-9a-f]{40} -->")
    updated = pattern.sub(marker, body) if pattern.search(body) else f"{body.rstrip()}\n\n{marker}\n"
    if updated == body:
        return {"status": "unchanged", "pr_number": pr, "head": head}
    _run(runner, ["gh", "pr", "edit", str(pr), "--body", updated], cwd=root, code="pr-update-failed")
    return {"status": "updated", "pr_number": pr, "head": head}


def _json_result(completed: subprocess.CompletedProcess[str], *, code: str) -> dict[str, Any]:
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise StackError(code, "GitHub returned an invalid JSON response") from exc
    if not isinstance(payload, dict):
        raise StackError(code, "GitHub returned a non-object JSON response")
    return payload


def _pr_merge_state(root: Path, runner: CommandRunner, *, pr: int) -> dict[str, Any]:
    completed = runner.run(
        ["gh", "pr", "view", str(pr), "--json", "headRefOid,state,isDraft,mergeable,statusCheckRollup,mergedAt,mergeCommit"],
        cwd=root,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise StackError("pr-read-failed", f"could not inspect PR #{pr}: {detail}")
    return _json_result(completed, code="pr-read-failed")


def _require_merge_ready(state: dict[str, Any], *, pr: int, reviewed_head: str) -> None:
    if state.get("headRefOid") != reviewed_head:
        raise StackError("pr-head-mismatch", f"PR #{pr} head changed after review")
    if state.get("state") != "OPEN" or state.get("isDraft") is True:
        raise StackError("pr-not-open", f"PR #{pr} is not an open non-draft pull request")
    if state.get("mergeable") == "CONFLICTING":
        raise StackError("pr-not-mergeable", f"PR #{pr} has merge conflicts")
    checks = [item for item in state.get("statusCheckRollup", []) if isinstance(item, dict)]
    review_checks = [item for item in checks if item.get("name") == "Review approval"]
    if not review_checks or any(item.get("conclusion") != "SUCCESS" for item in review_checks):
        raise StackError("review-not-current", f"PR #{pr} lacks the successful Review approval check for {reviewed_head}")
    unsuccessful = [
        str(item.get("name") or item.get("context") or "unnamed-check")
        for item in checks
        if str(item.get("status") or "COMPLETED") != "COMPLETED"
        or str(item.get("conclusion") or item.get("state") or "SUCCESS") not in {"SUCCESS", "NEUTRAL", "SKIPPED"}
    ]
    if unsuccessful:
        raise StackError("checks-not-ready", f"PR #{pr} has non-successful checks: {', '.join(unsuccessful)}")


def _observe_terminal_merge(root: Path, runner: CommandRunner, *, pr: int, reviewed_head: str) -> dict[str, Any]:
    state = _pr_merge_state(root, runner, pr=pr)
    if state.get("headRefOid") != reviewed_head:
        raise StackError("pr-head-mismatch", f"PR #{pr} head changed while merge completion was being observed")
    if state.get("state") != "MERGED" or not state.get("mergedAt"):
        raise StackError("merge-not-observed", f"PR #{pr} was not observed in terminal merged state")
    return state


def merge_ready_pr(
    root: Path,
    *,
    pr: int,
    reviewed_head: str,
    merge_method: str,
    receipt_path: Path,
    runner: CommandRunner,
    max_polls: int = 30,
    poll_interval_seconds: float = 2.0,
) -> dict[str, Any]:
    """Merge one independently approved exact head through the supported GitHub transport."""

    _require_sha(reviewed_head, "reviewed_head")
    if merge_method not in {"merge", "squash", "rebase"}:
        raise StackError("invalid-merge-method", "merge_method must be merge, squash, or rebase")
    receipt: dict[str, Any] = {
        "kind": MERGE_RECEIPT_KIND,
        "status": "preflight",
        "pr_number": pr,
        "reviewed_head": reviewed_head,
        "merge_method": merge_method,
        "transport": "",
        "async_request": {},
        "terminal_observation": {},
    }
    _write_receipt(receipt_path, receipt)
    try:
        state = _pr_merge_state(root, runner, pr=pr)
        _require_merge_ready(state, pr=pr, reviewed_head=reviewed_head)
        repo = _run(runner, ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"], cwd=root, code="repo-read-failed")
        stack_payload = runner.run(["gh", "api", f"repos/{repo}/pulls/{pr}", "--jq", ".stack // empty"], cwd=root)
        stacked = stack_payload.returncode == 0 and bool(stack_payload.stdout.strip())

        if not stacked:
            receipt["transport"] = "gh-pr-merge"
            _write_receipt(receipt_path, receipt)
            ordinary = runner.run(["gh", "pr", "merge", str(pr), f"--{merge_method}", "--match-head-commit", reviewed_head], cwd=root)
            if ordinary.returncode == 0:
                receipt["terminal_observation"] = _observe_terminal_merge(root, runner, pr=pr, reviewed_head=reviewed_head)
                receipt["status"] = "merged"
                _write_receipt(receipt_path, receipt)
                return receipt
            diagnostic = (ordinary.stderr or ordinary.stdout).strip()
            if "asynchronous" not in diagnostic.lower() or "merge" not in diagnostic.lower():
                raise StackError("ordinary-merge-failed", diagnostic or "ordinary GitHub merge transport failed")
            receipt["ordinary_transport_refusal"] = diagnostic[-2000:]

        receipt["transport"] = "github-merge-async"
        request_body = {"sha": reviewed_head, "merge_method": merge_method, "merge_action": "default"}
        requested = runner.run(
            ["gh", "api", "--method", "PUT", f"repos/{repo}/pulls/{pr}/merge-async", "--input", "-"],
            cwd=root,
            input_text=json.dumps(request_body),
        )
        request_payload = _json_result(requested, code="async-merge-request-failed")
        request_status = str(request_payload.get("status") or "")
        details = request_payload.get("details") if isinstance(request_payload.get("details"), dict) else {}
        if requested.returncode and requested.returncode != 1:
            raise StackError("async-merge-request-failed", requested.stderr.strip() or "asynchronous merge request failed")
        receipt["async_request"] = request_payload
        _write_receipt(receipt_path, receipt)
        if request_status == "merged":
            receipt["terminal_observation"] = _observe_terminal_merge(root, runner, pr=pr, reviewed_head=reviewed_head)
            receipt["status"] = "merged"
            _write_receipt(receipt_path, receipt)
            return receipt
        request_id = str(request_payload.get("uuid") or details.get("uuid") or "")
        if not request_id:
            raise StackError("async-merge-request-failed", "asynchronous merge response did not include a request UUID")

        for poll_index in range(max_polls):
            if poll_index and poll_interval_seconds:
                time.sleep(poll_interval_seconds)
            result = _run(
                runner,
                ["gh", "api", f"repos/{repo}/pulls/{pr}/merge-async/{request_id}"],
                cwd=root,
                code="async-merge-poll-failed",
            )
            result_payload = json.loads(result)
            receipt["async_result"] = result_payload
            _write_receipt(receipt_path, receipt)
            status = str(result_payload.get("status") or "")
            if status == "pending":
                continue
            if status != "merged":
                raise StackError("async-merge-failed", str(_as_message(result_payload) or f"asynchronous merge ended as {status}"))
            receipt["terminal_observation"] = _observe_terminal_merge(root, runner, pr=pr, reviewed_head=reviewed_head)
            receipt["status"] = "merged"
            _write_receipt(receipt_path, receipt)
            return receipt
        raise StackError("async-merge-timeout", f"PR #{pr} merge remained pending after {max_polls} observations")
    except StackError as exc:
        receipt.update(status="failed", error={"code": exc.code, "message": str(exc)})
        _write_receipt(receipt_path, receipt)
        return receipt


def _as_message(payload: dict[str, Any]) -> str:
    details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
    return str(details.get("message") or payload.get("message") or "")


def restack(
    root: Path,
    *,
    declaration_path: Path,
    receipt_path: Path,
    runner: CommandRunner,
    publish: bool,
    update_pr_bodies: bool,
) -> dict[str, Any]:
    declaration = _load_declaration(declaration_path)
    base = declaration["base"]
    descendants = declaration["descendants"]
    receipt: dict[str, Any] = {
        "kind": RECEIPT_KIND,
        "status": "preflight",
        "declaration": declaration_path.as_posix(),
        "receipt_path": receipt_path.as_posix(),
        "publish_requested": publish,
        "base": {
            "pr_number": int(base["pr_number"]),
            "branch": str(base["branch"]),
            "declared_head": str(base["head"]),
        },
        "rewrites": [],
        "remote_updates": [],
        "pr_metadata_updates": [],
    }
    _write_receipt(receipt_path, receipt)
    try:
        observed_base = _remote_head(root, runner, str(base["branch"]))
        if observed_base != str(base["head"]):
            raise StackError("base-head-mismatch", f"base branch {base['branch']} is {observed_base}, not declared {base['head']}")

        remote_states: list[str] = []
        for item in descendants:
            observed = _remote_head(root, runner, str(item["branch"]))
            remote_states.append(observed)
            if observed != str(item["old_remote_head"]):
                raise StackError(
                    "lease-preflight-failed",
                    f"branch {item['branch']} is {observed}, not declared old remote head {item['old_remote_head']}",
                )

        explicit_objects = {str(base["head"])}
        for item in descendants:
            explicit_objects.update(str(item[field]) for field in ("old_base", "new_base", "old_remote_head"))
        for object_id in sorted(explicit_objects):
            _run(runner, ["git", "fetch", "--no-tags", "origin", object_id], cwd=root, code="object-fetch-failed")

        with tempfile.TemporaryDirectory(prefix="aw-review-stack-") as temporary_root:
            for index, item in enumerate(descendants):
                worktree = Path(temporary_root) / f"member-{index}"
                old_head = str(item["old_remote_head"])
                old_base = str(item["old_base"])
                new_base = str(item["new_base"])
                _run(runner, ["git", "worktree", "add", "--detach", str(worktree), old_head], cwd=root, code="worktree-add-failed")
                try:
                    old_patch_id = _patch_id(root, runner, old_base, old_head)
                    _run(
                        runner,
                        ["git", "rebase", "--onto", new_base, old_base],
                        cwd=worktree,
                        code="rebase-failed",
                    )
                    new_head = _run(runner, ["git", "rev-parse", "HEAD"], cwd=worktree, code="new-head-unavailable")
                    _require_sha(new_head, "rewritten head")
                    new_patch_id = _patch_id(root, runner, new_base, new_head)
                    ancestry = runner.run(["git", "merge-base", "--is-ancestor", new_base, new_head], cwd=root)
                    if ancestry.returncode:
                        raise StackError("ancestry-not-preserved", f"rewritten {item['branch']} does not descend from {new_base}")
                    if old_patch_id != new_patch_id:
                        raise StackError("patch-not-preserved", f"rewritten {item['branch']} changed its aggregate patch identity")
                    receipt["rewrites"].append(
                        {
                            "pr_number": int(item["pr_number"]),
                            "branch": str(item["branch"]),
                            "old_base": old_base,
                            "new_base": new_base,
                            "old_remote_head": old_head,
                            "new_head": new_head,
                            "ancestry_preserved": True,
                            "patch_preserved": True,
                            "old_patch_id": old_patch_id,
                            "new_patch_id": new_patch_id,
                        }
                    )
                finally:
                    runner.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=root)

        receipt["status"] = "planned"
        _write_receipt(receipt_path, receipt)
        if not publish:
            return receipt

        for rewrite in receipt["rewrites"]:
            branch = str(rewrite["branch"])
            old_head = str(rewrite["old_remote_head"])
            new_head = str(rewrite["new_head"])
            completed = runner.run(
                [
                    "git",
                    "push",
                    "origin",
                    f"--force-with-lease=refs/heads/{branch}:{old_head}",
                    f"{new_head}:refs/heads/{branch}",
                ],
                cwd=root,
            )
            update = {
                "branch": branch,
                "expected_old_head": old_head,
                "requested_new_head": new_head,
                "exit_code": completed.returncode,
                "status": "published" if completed.returncode == 0 else "lease-or-push-failed",
                "diagnostic": (completed.stderr or completed.stdout).strip()[-2000:],
            }
            receipt["remote_updates"].append(update)
            _write_receipt(receipt_path, receipt)
            if completed.returncode:
                receipt.update(status="publication-partial" if len(receipt["remote_updates"]) > 1 else "publication-failed")
                _write_receipt(receipt_path, receipt)
                return receipt
            observed = _remote_head(root, runner, branch)
            update["observed_new_head"] = observed
            if observed != new_head:
                update["status"] = "publication-not-observed"
                receipt["status"] = "publication-partial"
                _write_receipt(receipt_path, receipt)
                return receipt

        if update_pr_bodies:
            for rewrite in receipt["rewrites"]:
                try:
                    metadata = _update_pr_body(
                        root,
                        runner,
                        pr=int(rewrite["pr_number"]),
                        head=str(rewrite["new_head"]),
                    )
                except StackError as exc:
                    metadata = {"status": "failed", "pr_number": int(rewrite["pr_number"]), "code": exc.code, "message": str(exc)}
                    receipt["pr_metadata_updates"].append(metadata)
                    receipt["status"] = "published-metadata-partial"
                    _write_receipt(receipt_path, receipt)
                    return receipt
                receipt["pr_metadata_updates"].append(metadata)
                _write_receipt(receipt_path, receipt)
        receipt["status"] = "published"
        _write_receipt(receipt_path, receipt)
        return receipt
    except StackError as exc:
        receipt.update(
            status="preflight-failed" if not receipt["remote_updates"] else "publication-partial",
            error={"code": exc.code, "message": str(exc)},
        )
        _write_receipt(receipt_path, receipt)
        return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Restack explicitly declared PR descendants with auditable CAS publication.")
    parser.add_argument("--target", type=Path, default=Path.cwd())
    parser.add_argument("--declaration", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--update-pr-bodies", action="store_true")
    parser.add_argument("--merge-pr", type=int)
    parser.add_argument("--reviewed-head")
    parser.add_argument("--merge-method", choices=("merge", "squash", "rebase"), default="merge")
    parser.add_argument("--max-polls", type=int, default=30)
    parser.add_argument("--poll-interval-seconds", type=float, default=2.0)
    return parser


def main(argv: Sequence[str] | None = None, *, runner: CommandRunner | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.target.resolve()
    if bool(args.merge_pr) == bool(args.declaration):
        _parser().error("select exactly one operation with --declaration or --merge-pr")
    operation = "merge" if args.merge_pr else "restack"
    default_name = f"{operation}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    receipt_path = args.receipt or Path(".agentic-workspace/local/review-stack-receipts") / default_name
    receipt_path = receipt_path if receipt_path.is_absolute() else root / receipt_path
    try:
        if args.merge_pr:
            receipt = merge_ready_pr(
                root,
                pr=args.merge_pr,
                reviewed_head=str(args.reviewed_head or ""),
                merge_method=args.merge_method,
                receipt_path=receipt_path,
                runner=runner or CommandRunner(),
                max_polls=args.max_polls,
                poll_interval_seconds=args.poll_interval_seconds,
            )
        else:
            assert args.declaration is not None
            declaration_path = args.declaration if args.declaration.is_absolute() else root / args.declaration
            receipt = restack(
                root,
                declaration_path=declaration_path,
                receipt_path=receipt_path,
                runner=runner or CommandRunner(),
                publish=args.publish,
                update_pr_bodies=args.update_pr_bodies,
            )
    except StackError as exc:
        kind = MERGE_RECEIPT_KIND if args.merge_pr else RECEIPT_KIND
        print(json.dumps({"kind": kind, "status": "error", "code": exc.code, "message": str(exc)}, indent=2))
        return 2
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt.get("status") in {"planned", "published", "merged"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
