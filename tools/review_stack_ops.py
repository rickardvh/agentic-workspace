from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

RECEIPT_KIND = "agentic-workspace/review-stack-restack-receipt/v1"
DECLARATION_KIND = "agentic-workspace/review-stack-restack/v1"
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
    parser.add_argument("--declaration", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--update-pr-bodies", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None, *, runner: CommandRunner | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.target.resolve()
    declaration_path = args.declaration if args.declaration.is_absolute() else root / args.declaration
    default_name = f"restack-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    receipt_path = args.receipt or Path(".agentic-workspace/local/review-stack-receipts") / default_name
    receipt_path = receipt_path if receipt_path.is_absolute() else root / receipt_path
    try:
        receipt = restack(
            root,
            declaration_path=declaration_path,
            receipt_path=receipt_path,
            runner=runner or CommandRunner(),
            publish=args.publish,
            update_pr_bodies=args.update_pr_bodies,
        )
    except StackError as exc:
        print(json.dumps({"kind": RECEIPT_KIND, "status": "error", "code": exc.code, "message": str(exc)}, indent=2))
        return 2
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt.get("status") in {"planned", "published"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
