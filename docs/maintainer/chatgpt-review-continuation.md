# ChatGPT Review to Codex Continuation

This repo-local maintainer loop transports external ChatGPT PR review findings back to the exact Codex session that handed off the reviewed head. It does not review code, invoke a model while polling, reinterpret review decisions, mark a PR ready, or merge.

The implementation is intentionally outside shipped Agentic Workspace runtime and payload surfaces:

- `.codex/hooks.json` records later handoffs from Codex `Stop` events;
- `tools/chatgpt_review_loop.py` owns local handoff, polling, resume, inspection, and cleanup;
- `.agentic-workspace/local/chatgpt-review-loop/` owns gitignored runtime state;
- `tools/skills/pr-review-recheck/SKILL.md` remains the independent external review policy.

## Requirements and trust

Install `git`, an authenticated `gh`, and a `codex` CLI that can resume the originating local session. No OpenAI API key is used by the controller. The external scheduled ChatGPT reviewer is configured separately.

Project hooks run only after the repository `.codex` layer and the exact hook definition are trusted. Inspect and trust it with `/hooks` in Codex. Codex hashes hook definitions, so review the hook again after it changes. The hook receives the exact `session_id` and `cwd` on standard input; the script does not inspect transcripts or store credentials.

Persistent `/hooks` trust is preferred. For bounded unattended automation after all active hook sources have been reviewed, `poll --bypass-hook-trust` passes Codex's explicit `--dangerously-bypass-hook-trust` only to the exact resumed invocation and records `hook_trust_mode: automation-bypass` in local state. The flag authorizes every enabled hook in that invocation, so do not use it before checking user, project, and enabled-plugin hook sources.

The Stop hook is dormant until a loop is explicitly enabled. It only updates an existing state record for the same branch and exact session, returns within 30 seconds, and never waits for review or starts the poller.

## Start a loop

1. Work in the exact Codex session that owns the PR.
2. Push the current branch so local `HEAD` equals the open PR head.
3. Run:

   ```powershell
   uv run python tools/chatgpt_review_loop.py handoff
   ```

   `CODEX_THREAD_ID` supplies the exact session identity. Outside Codex, pass `--session-id <uuid>` explicitly. The command fails rather than deriving an identity from branch, recency, PID, or timestamps.

The handoff verifies repository, branch, open PR, and pushed full SHA; tolerates a bounded three-read GitHub head-propagation window; adds `<!-- aw-chatgpt-review:enabled -->` as an idempotent top-level comment; and writes local state. It still fails closed when the remote head does not converge. Use `--max-cycles` and `--max-repeated-blockers` to lower or raise the default limits of three blocked cycles and two repetitions of identical findings.

If another session already owns the PR, inspect it first. `--replace-session` is an explicit human decision to supersede that owner; it is never automatic.

## Poll or watch

Run one cheap deterministic poll:

```powershell
uv run python tools/chatgpt_review_loop.py poll
```

Or keep the local controller running for a bounded number of polls:

```powershell
uv run python tools/chatgpt_review_loop.py poll --watch --interval 60 --max-polls 60 --bypass-hook-trust
```

Polling uses `gh` only. The owner checkout may move to another branch after handoff: blocked-review work runs by default in a disposable detached Git worktree created at the exact reviewed SHA, so unrelated local implementation is not disturbed. Pass `--in-place` only for explicit debugging when the owner checkout is still on the recorded PR branch.

A review is eligible only when its comment contains exactly one well-formed marker whose PR number and 40-character lowercase SHA equal the recorded handoff:

```text
<!-- aw-chatgpt-review pr=<number> head=<full-sha> policy=pr-review-recheck-v1 decision=<blocked|merge-ready> -->
```

For `blocked`, the controller records `(PR, reviewed SHA, comment ID)` as attempted, creates a detached worktree beside the owner checkout, and starts `codex -C <worktree> exec resume <exact-session> <verbatim-findings>`. The prompt tells the resumed session to push its detached corrective commit to the recorded PR branch with `git push origin HEAD:<branch>`. Inherited owner-root and owner-branch bindings let the worktree's Stop hook update the original gitignored loop state without reading or changing the owner checkout.

After the resumed CLI exits, the controller removes the temporary worktree even when the resume fails. A cleanup failure is retained in state and requires explicit recovery. That exact review cannot automatically resume twice, including after a resume or worktree failure. The resumed Codex process inherits a transport guard, while its Stop hook only records a newly pushed handoff; neither termination path starts another poller. A successful cycle therefore requires a corrective push with a new head.

For `merge-ready`, the controller records readiness and stops. It never invokes `gh pr merge` or changes ready/draft state; the human retains merge authority.

After a successful blocked-review continuation records a new handoff head, the same bounded watcher keeps running and polls that head. It exits only on merge-ready, recovery, explicit stop/cleanup, or the configured poll limit; no manual watcher restart is needed between review cycles.
The watcher may also be started while an exact-session resume is already in progress. It waits for that resume's Stop handoff instead of treating the transient `resume-in-progress` state as terminal.
Automatic Stop-hook handoffs preserve the loop's configured cycle and repeated-blocker limits. Change those limits only with an explicit maintainer `handoff`; hook parser defaults never replace an enabled loop's budget.

## Inspect, stop, recover, and clean up

```powershell
uv run python tools/chatgpt_review_loop.py status
uv run python tools/chatgpt_review_loop.py status --pr 123
uv run python tools/chatgpt_review_loop.py stop --pr 123
uv run python tools/chatgpt_review_loop.py recover --pr 123 --action continue-waiting
uv run python tools/chatgpt_review_loop.py cleanup --pr 123
```

Use `recover` only after a human has fixed the reported malformed or ambiguous GitHub state. It does not remove a handled-review key or retry a failed exact review. After a resume failure or a session that ended without a corrective push, inspect the exact session, push a new head, and run a new handoff. `stop` or `cleanup` also ends a bounded watcher on its next poll; `cleanup` removes only the gitignored local state record and does not change the PR or its comments.

The controller reports explicit recovery for a closed PR, an in-place local branch change, a changed remote branch, an unrecorded remote head, a missing/ambiguous session, malformed or multiple matching markers, missing blocked findings, worktree creation or cleanup failure, resume failure, no new handoff, maximum cycles, and repeated identical blockers. Stale-SHA reviews are visible no-ops and never resume Codex.

## Validation and current evidence boundary

Run the focused deterministic suite with:

```powershell
uv run pytest tests/test_chatgpt_review_loop.py -q
uv run ruff check tools/chatgpt_review_loop.py tests/test_chatgpt_review_loop.py
```

The current dogfooding record is [aw-chatgpt-review-continuation-dogfood-2026-07-14.md](../reviews/aw-chatgpt-review-continuation-dogfood-2026-07-14.md). Do not close issue #2290 or consider automatic merge until that record contains representative live external-review cycles rather than deterministic fixtures alone.
