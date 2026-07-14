# AW ChatGPT Review Continuation Dogfood — 2026-07-14

## Decision

The deterministic repo-local transport is implemented and suitable for an opted-in live trial. Final issue #2290 satisfaction is not yet claimed: no existing repository PR contained an `aw-chatgpt-review` marker when checked on 2026-07-14, so review latency and a real external ChatGPT-to-Codex resumption could not be measured without creating or mutating a PR.

Automatic merge remains out of scope and unauthorized.

## Evidence collected

Live trial PR [#2292](https://github.com/rickardvh/agentic-workspace/pull/2292) was created as a draft at `2026-07-14T09:37:04Z`. The controller bound the exact originating Codex session to head `b5cae38c54d0f2563a24fbfc160af4df24ccdad3`, added the opt-in marker, and returned `review-pending` on its first poll. Before starting the background watcher, local capability inspection showed that interactive `codex resume` was the wrong unattended surface; the controller was corrected to use `codex exec resume`. The same readiness pass found that a watcher would continue sleeping after `stop`; the exit condition was narrowed to genuine review-waiting states. These are successful manual interventions before any review was consumed, not yet a successful automatic resumption.

| Scenario | Evidence | Result |
| --- | --- | --- |
| Blocked review, exact-session resume, corrective head | `test_blocked_review_resumes_exact_session_once_and_requires_new_handoff` simulates PR #12 at head `aaaa…`, records exact session `1111…`, transports one blocker, launches non-interactive `codex exec resume` with that exact ID, and observes the Stop-side state move to head `bbbb…` | Passed; one automatic resumption and one new handoff |
| Already attempted review | `test_resume_failure_is_not_retried_for_same_comment` persists the `(PR, SHA, comment ID)` attempt before a failing resume and polls again | Passed; one invocation, then explicit recovery/no-op |
| Stale review | `test_stale_review_is_a_visible_noop` supplies a valid marker for a different full SHA | Passed; visible `stale-review-rejected`, zero resumes |
| Malformed and wrong-PR markers | `test_marker_parser_accepts_only_exact_pr_and_full_sha` covers truncated SHA, PR mismatch, and exact-match parsing | Passed; only the exact PR/full-SHA marker is eligible |
| Merge-ready | `test_merge_ready_records_readiness_without_merging` | Passed; readiness recorded, no merge command |
| Branch/head/closed-PR safety | `test_unsafe_repository_states_require_explicit_recovery` | Passed; all require bounded human recovery |
| Repeated blocker and maximum cycle limits | `test_repeated_blocker_and_cycle_limits_escalate_without_resume` | Passed; both stop before Codex invocation |
| Dormant Stop hook | `test_hook_mode_is_quiet_until_an_exact_loop_is_explicitly_enabled` | Passed; no GitHub query or opt-in before explicit enablement |
| Windows Stop-hook invocation | Piped a real Stop payload through the checked-in `commandWindows` using the repository `uv run python` runtime | Passed; returned `{\"continue\": true}` and made no GitHub query while disabled |
| Hook portability | `test_project_stop_hook_uses_repo_runtime_and_has_no_machine_local_path` | Passed; repo-root resolution, bounded timeout, and no checked-in machine path |

Focused run: `uv run pytest tests/test_chatgpt_review_loop.py -q` → 14 passed. Ruff passed after formatting. Runtime state is below `.agentic-workspace/local/`, which is already covered by `.gitignore` and was confirmed with `git check-ignore`.

Read-only GitHub search used `repo:rickardvh/agentic-workspace is:pr "aw-chatgpt-review"` and returned no PRs. Therefore:

- review latency: not yet measurable;
- successful live automatic resumptions: 0;
- manual interventions in live trials: not yet measurable;
- stale/duplicate prevention: deterministic fixtures passed;
- missed or false blockers: cannot be assessed before live reviewer output exists.

## Required live follow-through

On the next representative maintainer PR, enable the loop from its exact Codex session, leave the bounded poller running, and append:

1. handoff and review timestamps (latency);
2. reviewed and corrective full SHAs;
3. review comment ID and decision;
4. whether the exact session resumed successfully;
5. any manual intervention;
6. stale/duplicate events;
7. any missed or false blocker.

Repeat across several representative AW PRs before evaluating automatic merge in a separate issue. Until then, a PR may land this transport but must not auto-close #2290.
