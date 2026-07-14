# AW ChatGPT Review Continuation Dogfood — 2026-07-14

## Decision

The deterministic repo-local transport is implemented and active on draft PR #2292. A live exact-session resume and project Stop-hook completion are now proven, but final issue #2290 satisfaction is not yet claimed: the successful Stop event was a manual recovery after the automatic invocation exposed a broken Windows hook wrapper. The next external review must still prove the complete unattended review-to-corrective-head cycle.

Automatic merge remains out of scope and unauthorized.

## Evidence collected

Live trial PR [#2292](https://github.com/rickardvh/agentic-workspace/pull/2292) was created as a draft at `2026-07-14T09:37:04Z`. The controller bound the exact originating Codex session to head `b5cae38c54d0f2563a24fbfc160af4df24ccdad3`, added the opt-in marker, and returned `review-pending` on its first poll. Before starting the background watcher, local capability inspection showed that interactive `codex resume` was the wrong unattended surface; the controller was corrected to use `codex exec resume`. The same readiness pass found that a watcher would continue sleeping after `stop`; the exit condition was narrowed to genuine review-waiting states. An immediate handoff after pushing `cb9a1fde` then observed GitHub's prior head and failed safely; the handoff gained a bounded three-read propagation retry. The live watcher was then explicitly activated with Codex's automation-only hook-trust bypass after confirming that no user-level or enabled-plugin hook source would also be authorized. These are recorded manual interventions in the live trial; automatic resumption is not yet proven.

At `2026-07-14T10:02:10Z`, the external reviewer posted the first real blocked result for head `ad37e10d`. The pre-activation watcher recorded that exact review as handled and attempted the exact session once, but Codex exited 1 before the hook-trust activation. The review also found that a successful `resumed` result would terminate the watcher before reviewing the newly handed-off head. That blocker is now covered by the two-head unattended watch test; the next live reviewed head must prove both activated Stop-hook execution and continued polling.

At `2026-07-14T10:12:19Z`, the reviewer posted a blocked result for head `67c3cce4`. The activated watcher detected it on poll 7 and attempted the exact session, but the process exited 2 and entered bounded recovery. A direct exact-session diagnostic then reached `hook: Stop` and reported `hook: Stop Failed`. Replaying a real Stop payload isolated the fault to `commandWindows`: the nested PowerShell wrapper treated Codex's JSON stdin as pipeline input while evaluating `Join-Path`, corrupting the Python script path. Commit `adeda425` replaced the wrapper with the repo-relative command `uv run python tools/chatgpt_review_loop.py handoff --hook` and preserved bounded resume stderr in local state. A manual exact-session recovery with hook-trust bypass then completed `hook: Stop` successfully and recorded pushed head `adeda425783085561cd034e03f7286b0afcd68f7` at `2026-07-14T10:41:50Z`. This proves the exact-session and Stop-hook path, but the manual recovery is not counted as an automatic resumption.

At `2026-07-14T11:11:12Z`, the reviewer posted blocked comment `IC_kwDOR6cWrs8AAAABKCV0JQ` for exact head `c0da56018db186b3d2007022ac0931e82ddb9c44`, 27 minutes 39 seconds after handoff. The same watcher remained alive, detected the marker on poll 29, and recorded the third bounded attempt without manual review copying. The retained diagnostic showed that the controller constructed `codex --dangerously-bypass-hook-trust -C ... exec resume`, but Codex CLI 0.144.3 accepts this flag on the `exec resume` subcommand. The invocation exited 2 before session startup. The controller and focused assertion now place the flag after `exec resume`; this review cannot be retried automatically because its attempt key was correctly persisted before launch.

At `2026-07-14T12:08:53Z`, the reviewer posted blocked comment `IC_kwDOR6cWrs8AAAABKCyeEQ` for exact head `8570580e57eca13697ddd024ccea2dcf4e780e92`, 25 minutes 52 seconds after handoff. The background watcher had disappeared after its last state write at `2026-07-14T11:46:33Z`, without a terminal state or any flushed redirected output, so a human restarted one foreground poll. That poll detected and deduplicated the review but still exited 2. The retained diagnostic and an executable-resolution probe found a Windows PATH split: interactive PowerShell resolved `codex` to the Node-installed `codex.ps1` shim (CLI 0.144.3), while Python `subprocess.run(["codex", ...])` bypassed the PATHEXT shim and launched a later desktop `codex.exe` (CLI 0.130.0-alpha.5) that does not support hook-trust bypass. The runner now resolves bare Windows executables with `shutil.which` before launch, selecting the same `codex.CMD` shim and 0.144.3 package as the shell. Controller output is also flushed so a normally running or exiting watcher leaves immediate poll evidence. The review cannot be retried because its attempt was correctly persisted before process launch.

After pushing the executable-resolution fix, a manual exact-session handoff probe started Codex CLI 0.144.3 and loaded the recorded session, but the account usage limit rejected the model turn before `Stop` could run. This is an external proof blocker rather than another transport defect. The pushed head can be recorded without model execution, but no further blocked review should be consumed until exact-session usage is available again.

At `2026-07-14T13:02:55Z`, the reviewer posted blocked comment `IC_kwDOR6cWrs8AAAABKDPBtw` for exact head `31f6924443b3ba4b071f920541f4fcc6f0cdcc6f`, 17 minutes 3 seconds after handoff. The loop was deliberately stopped at review time. When the user explicitly restarted it, the first re-arm failed before changing state because Python decoded `gh`'s UTF-8 review JSON with the Windows CP-1252 default. Explicit UTF-8 decoding with replacement for undecodable diagnostic bytes fixed the boundary and 19 focused tests passed. The next controller poll persisted the review attempt and successfully started this exact Codex session through the resolved CLI 0.144.3 shim at `2026-07-14T13:07:44Z`. No review text was copied manually. This is the first successful controller-triggered live exact-session resumption, but it followed a manual loop restart and in-place decoding repair, so it does not prove uninterrupted watcher continuity.

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
| Two-head unattended watch | `test_watch_loop_resumes_head_a_then_reviews_head_b_without_restart` | Passed; head A blocker resumes once, Stop-side handoff records head B, and the same watcher consumes head B merge-ready |
| Windows Stop-hook invocation | Piped a real Stop payload through the direct repo-relative command and then ran an exact-session Codex turn with the reviewed hook enabled | Passed after fixing the PowerShell stdin bug; Codex reported `hook: Stop Completed` and local state recorded corrective head `adeda425…` |
| Hook portability | `test_project_stop_hook_uses_repo_runtime_and_has_no_machine_local_path` | Passed; repo-root resolution, bounded timeout, and no checked-in machine path |

Focused run: `uv run pytest tests/test_chatgpt_review_loop.py -q` → 19 passed. Ruff passed after formatting. Runtime state is below `.agentic-workspace/local/`, which is already covered by `.gitignore` and was confirmed with `git check-ignore`.

Live PR #2292 has now supplied five SHA-bound blocked reviews. Therefore:

- review latency for head `67c3cce4`: 5 minutes 23 seconds from handoff to review;
- review latency for head `c0da5601`: 27 minutes 39 seconds from handoff to review;
- review latency for head `8570580e`: 25 minutes 52 seconds from handoff to review;
- review latency for head `31f69244`: 17 minutes 3 seconds from handoff to review;
- successful live controller-triggered exact-session resumptions: 1;
- successful fully unattended review-to-corrective-head cycles: 0;
- successful live manual exact-session recoveries: 1;
- automatic watcher detections: 3; two additional reviews required a foreground watcher restart;
- manual interventions in live trials: hook-trust activation, Windows wrapper diagnosis/fix, hook-trust flag placement diagnosis/fix, Windows executable-resolution diagnosis/fix, UTF-8 decoding diagnosis/fix, three watcher restarts, and one explicit recovery resume;
- stale/duplicate prevention: deterministic fixtures passed;
- missed or false blockers: 0 observed across the two live reviews.

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
