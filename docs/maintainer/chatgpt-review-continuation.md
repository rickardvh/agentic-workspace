# ChatGPT Review to Codex Continuation

This repo-local maintainer loop transports actionable external PR review findings, failed CI checks, and merge conflicts back to the exact Codex session that handed off the reviewed head. It does not review code, invoke a model while polling, reinterpret review decisions, mark a PR ready, or merge.

The implementation is intentionally outside shipped Agentic Workspace runtime and payload surfaces:

- `tools/chatgpt_review_loop.py` owns explicit local handoff, polling, resume, inspection, and cleanup;
- `.agentic-workspace/local/chatgpt-review-loop/` owns gitignored runtime state;
- `tools/skills/pr-review-recheck/SKILL.md` remains the independent external review policy.

## Requirements and trust

Install `git`, an authenticated `gh`, and a `codex` CLI that can resume the originating local session. No OpenAI API key is used by the controller. The external scheduled ChatGPT reviewer is configured separately.

The repository does not install a project `Stop` hook. Each initial or resumed continuation must explicitly run `handoff --pr <number> --existing-only` after proof and push; `CODEX_THREAD_ID` supplies the exact session identity. This avoids repository-wide lifecycle work on unrelated Codex stops while preserving exact-session and exact-head binding.

For bounded unattended automation after all active user and plugin hook sources have been reviewed, `poll --bypass-hook-trust` passes Codex's explicit `--dangerously-bypass-hook-trust` only to the exact resumed invocation and records `hook_trust_mode: automation-bypass` in local state. The flag authorizes every enabled hook in that invocation, so do not use it before checking those external hook sources.

`handoff --existing-only` updates only an existing state record for the same branch and exact session; for a fresh all-open dispatch, it may bind the one pre-created `fresh-session-in-progress` record. It never creates a new opt-in or starts the poller.

## Global serial dispatcher

Use the opt-in global mode to scan every open PR and dispatch at most one eligible blocked review:

```powershell
uv run python tools/chatgpt_review_loop.py poll --all-open --watch
```

It retains one Codex session per PR and uses the main checkout serially. A first eligible review fetches the PR branch into an explicit `origin/<branch>` ref, verifies the fetched SHA equals the reviewed SHA, requires a clean checkout, switches to the PR branch, and fast-forwards it to that exact commit; a later eligible review switches back to the same branch and resumes the recorded session. Any pre-launch switch failure restores the checkout that the maintainer started from. A local exclusive lock keeps two poller invocations from starting concurrent jobs. The watcher stays active after empty scans and dispatches, and retires registry entries when their PR closes. The dispatcher preserves the exact-head marker, duplicate-review, branch-ownership, and bounded-recovery checks; stale comments never become jobs. Existing `poll` behaviour remains scoped to explicit local handoffs.

## Start a loop

1. Work in the exact Codex session that owns the PR.
2. Push the current branch so local `HEAD` equals the open PR head.
3. Run:

   ```powershell
   uv run python tools/chatgpt_review_loop.py handoff
   ```

   `CODEX_THREAD_ID` supplies the exact session identity. Outside Codex, pass `--session-id <uuid>` explicitly. The command fails rather than deriving an identity from branch, recency, PID, or timestamps.

The handoff verifies repository, branch, open PR, and pushed full SHA; tolerates a bounded three-read GitHub head-propagation window; and records the opt-in only in local dispatcher state. It does not post an enablement comment on the PR. It still fails closed when the remote head does not converge. Use `--max-cycles` and `--max-repeated-blockers` to lower or raise the default limits of three blocked cycles and two repetitions of identical findings.

If another session already owns the PR, inspect it first. `--replace-session` is an explicit human decision to supersede that owner; it is never automatic.

The all-open dispatcher normally runs on a branch checkout, so continuations push with `git push origin <PR branch>`. Legacy/manual detached sessions are still accepted only when explicitly named. After pushing `HEAD:<PR branch>`, record the handoff by naming the PR:

```powershell
uv run python tools/chatgpt_review_loop.py handoff --pr <number>
```

The command resolves the branch only from that open PR and still requires the detached `HEAD` to equal its remote head; without `--pr`, detached handoff remains fail-closed.

## Poll or watch

## Declared stack restacking

Use `tools/review_stack_ops.py` for descendants that must move after a reviewed base changes. It requires a JSON declaration with every PR, branch, old base, new base, and expected remote head written as a full SHA; it never discovers a rewrite target from branch ordering or abbreviated IDs:

```json
{
  "kind": "agentic-workspace/review-stack-restack/v1",
  "base": {"pr_number": 100, "branch": "base-fix", "head": "<full-sha>"},
  "descendants": [
    {
      "pr_number": 101,
      "branch": "dependent-change",
      "old_base": "<full-sha>",
      "new_base": "<full-sha>",
      "old_remote_head": "<full-sha>"
    }
  ]
}
```

Plan and verify ancestry plus stable aggregate patch identity without publishing:

```powershell
uv run python tools/review_stack_ops.py --declaration stack.json --receipt restack-receipt.json
```

After inspecting that receipt, add `--publish` to use an exact `--force-with-lease=<ref>:<old-head>` for every declared descendant. Add `--update-pr-bodies` only when the PR bodies should receive an `aw-exact-head` marker from the observed published heads. All rewrites are prepared before the first push. A pre-publication failure leaves branches and PR bodies unchanged; a later failure records precisely which pushes or metadata edits succeeded, because multi-ref GitHub publication is bounded but not atomic.

Run one cheap deterministic poll:

```powershell
uv run python tools/chatgpt_review_loop.py poll
```

Or keep the local controller running for a bounded number of polls:

```powershell
uv run python tools/chatgpt_review_loop.py poll --watch --interval 60 --max-polls 60 --bypass-hook-trust
```

For the serial all-open controller, use `make start-review-poller REVIEW_MAX_CYCLES=10`. It starts at most one job at a time, stores the cycle budget per PR, and is idempotent while its recorded process is alive.

Polling uses `gh` only. A review is eligible only when its comment contains exactly one well-formed marker whose PR number and 40-character lowercase SHA equal the recorded handoff:

```text
<!-- aw-chatgpt-review pr=<number> head=<full-sha> policy=pr-review-recheck-v1 decision=<blocked|merge-ready> -->
```

For `blocked`, the controller records `(PR, reviewed SHA, comment ID)` as attempted before starting the non-interactive continuation `codex -C <repo> exec resume <exact-session> <verbatim-findings>`. That exact review cannot automatically resume twice, including after a resume failure. The resumed Codex process inherits a transport guard and must explicitly record its newly pushed handoff; neither termination path starts another poller. A successful cycle therefore requires a corrective push with a new head plus the prompted `handoff --existing-only` command.

The all-open controller fetches and verifies the reviewed SHA before fresh execution, then runs fresh and later resume jobs from the serial checkout after switching to the PR branch. Owner-local state is created before fresh execution, and the prompted explicit handoff binds the exact session after its first corrective push. A fresh job that exits nonzero or never records that binding remains in terminal local recovery and suppresses redispatch of the same review until a human explicitly recovers or cleans it up. On startup, legacy registry entries with a `worktree` field are migrated by verifying the path against `git worktree list --porcelain` and the configured `--worktree-root`, removing only dispatcher-owned `pr-<number>` worktrees, and rewriting the entry to `checkout`. Closing a tracked PR also retires its local state.

For `merge-ready`, the controller records readiness and stops. It never invokes `gh pr merge` or changes ready/draft state; the human retains merge authority.

When the maintainer chooses to merge that exact reviewed head, use the repository-owned guarded merge operation:

```powershell
uv run python tools/review_stack_ops.py --merge-pr 123 --reviewed-head <full-sha> --merge-method merge --receipt merge-receipt.json
```

The operation consumes the existing successful `Review approval` check and current CI; it does not create review authority. Standalone PRs keep the ordinary `gh pr merge --match-head-commit` transport. A GitHub stack, or an ordinary transport refusal requiring asynchronous merge, uses GitHub's `merge-async` endpoint with the same head and merge method. Accepted or pending responses are not completion: the operation polls the request and then observes the PR in terminal merged state before returning success. A changed head, failed check, rejection, failure, or timeout leaves descendant branches untouched and records one exact failure in the receipt.

After a successful blocked-review continuation records a new handoff head, the same bounded watcher keeps running and polls that head. It exits only on merge-ready, recovery, explicit stop/cleanup, or the configured poll limit; no manual watcher restart is needed between review cycles.
The watcher may also be started while an exact-session resume is already in progress. It waits for that resume's explicit handoff instead of treating the transient `resume-in-progress` state as terminal.
Explicit `--existing-only` continuation handoffs preserve the loop's configured cycle and repeated-blocker limits. Change those limits only with a new maintainer opt-in handoff.

## Inspect, stop, recover, and clean up

```powershell
uv run python tools/chatgpt_review_loop.py status
uv run python tools/chatgpt_review_loop.py status --pr 123
uv run python tools/chatgpt_review_loop.py stop --pr 123
uv run python tools/chatgpt_review_loop.py recover --pr 123 --action continue-waiting
uv run python tools/chatgpt_review_loop.py cleanup --pr 123
```

Use `recover` only after a human has fixed the reported malformed or ambiguous GitHub state. It does not remove a handled-review key or retry a failed exact review. After a resume failure or a session that ended without a corrective push, inspect the exact session, push a new head, and run a new handoff. `stop` or `cleanup` also ends a bounded watcher on its next poll; `cleanup` removes only the gitignored local state record and does not change the PR or its comments.

`recover --action replace-worktree` remains as a deprecated alias for older state. It still verifies and removes a legacy dispatcher-owned worktree before retiring the state; if the recorded path is outside the configured worktree root or is not a registered Git worktree, it fails with a manual recovery route instead of deleting an unrelated checkout. Automatic legacy migration first preflights every candidate and rolls back removed worktrees plus dispatch state if an apply or save boundary fails, so one unsafe entry cannot leave another removed worktree referenced by durable state.

The controller reports explicit recovery for a closed PR, changed local or remote branch, an unrecorded remote head, a missing/ambiguous session, malformed or multiple matching markers, missing blocked findings, resume failure, no new handoff, maximum cycles, and repeated identical blockers. Stale-SHA reviews are visible no-ops and never resume Codex.

If the exact same Codex launch has already recorded `job-result`, but a rebase and later successful push produce the final head, record the correction explicitly from that checkout:

```powershell
uv run python tools/chatgpt_review_loop.py job-result --session-id $env:CODEX_THREAD_ID --proof-status passed --proof-command "<proof command>" --proof-exit-code 0 --push-status passed --supersede
```

`--supersede` is not a general duplicate override: it requires the same bound launch and session, a changed `HEAD`, and a successful push. It preserves the prior head in correction history and updates the result's final head for later exact-head validation. An unchanged or unverified duplicate remains fail-closed.

## Validation and current evidence boundary

Run the focused deterministic suite with:

```powershell
uv run pytest tests/test_chatgpt_review_loop.py -q
uv run pytest tests/test_review_stack_ops.py -q
uv run ruff check tools/chatgpt_review_loop.py tests/test_chatgpt_review_loop.py
uv run ruff check tools/review_stack_ops.py tests/test_review_stack_ops.py
```

The current dogfooding record is [aw-chatgpt-review-continuation-dogfood-2026-07-14.md](../reviews/aw-chatgpt-review-continuation-dogfood-2026-07-14.md). Do not close issue #2290 or consider automatic merge until that record contains representative live external-review cycles rather than deterministic fixtures alone.
