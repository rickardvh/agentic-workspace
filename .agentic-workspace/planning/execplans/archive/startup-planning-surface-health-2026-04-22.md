# Startup Planning-Surface Health

Compact inactive-plan residue generated at archive time.
Use git history for superseded active-step detail; keep only the closure, continuation, proof, and cheap-resume residue here.

## Origin

- Archived from: .agentic-workspace/planning/execplans/startup-planning-surface-health-2026-04-22.md

## Intent Continuity

- Larger Intended Outcome: make planning and Memory cooperate tightly at the workflow level so work pulls relevant durable understanding before execution and preserves later-useful residue after finishing, while keeping both modules independently usable.
- This Slice Completes The Larger Intended Outcome: no
- Continuation Surface: .agentic-workspace/planning/state.toml
- Parent Lane: `planning-memory-operating-loop`

## Required Continuation

- Required Follow-On For The Larger Intended Outcome: yes
- Owner Surface: .agentic-workspace/planning/state.toml
- Activation Trigger: activate the memory-recurring-friction-improvement-pressure lane only if recurring-friction evidence from `#263` still needs additional durable accumulation or stronger validation/reporting after the planning-owned startup/resume gap is closed.

## Delegated Judgment

- Requested Outcome: expose a compact planning-surface health signal early enough that startup and resume do not have to rediscover drift through exploratory reading
- Hard Constraints: reuse the existing warning path, stay compact and actionable, and keep planning independent from Memory
- Agent May Decide Locally: the exact health field names, whether the human summary output mirrors the JSON shape directly, and the smallest proof that startup/resume now sees the signal
- Escalate When: the change would require a second checker, a broader summary/report redesign, or any dependency on Memory being installed

## Intent Interpretation

- Literal Request: continue and finish the active lane, and commit after each slice
- Inferred Intended Outcome: close the remaining planning-owned lane work through bounded slices and leave only genuinely separate follow-on behind
- Chosen Concrete What: add a compact planning-surface health view to the startup summary and CLI output so resume/startup sees clean/not-clean state, mismatches, and the shortest next fix
- Interpretation Distance: low
- Review Guidance: reject the slice if it adds a second checker, broad telemetry, or any Memory dependency instead of reusing the existing planning warning path.

## Execution Bounds

- Allowed Paths: `.agentic-workspace/planning/`, `packages/planning/`, `tests/`
- Max Changed Files: 12
- Required Validation Commands: `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace summary --format json`
- Ask-Before-Refactor Threshold: stop before broad summary/report redesign or any new planning validation subsystem
- Stop Before Touching: memory package code, recurring-friction accumulation workflows, or unrelated roadmap/doctor/report architecture

## Stop Conditions

- Stop When: the startup signal cannot be expressed as a thin view over existing planning warnings
- Escalate When Boundary Reached: the slice would require a second checker, a new persistence layer, or broad report redesign
- Escalate On Scope Drift: more than the summary/CLI/docs/tests path is needed to show the startup health signal
- Escalate On Proof Failure: the signal cannot stay compact and actionable enough for interrupted-work recovery

## Context Budget

- Live Working Set: issue `#262`, the current summary startup path, existing warning list, and the shortest remediation mapping already available in the planning package
- Recoverable Later: broader lane rationale from `#264`, the completed pre-work and post-work handshake slices, and the memory-owned recurring-friction follow-on from `#263`
- Externalize Before Shift: the exact startup health shape, the shortest next-action rule, and the rule that this remains a thin planning-owned view over existing warnings
- Tiny Resumability Note: keep the startup signal to clean/not-clean status, compact mismatch rows, and the shortest corrective action
- Context-Shift Triggers: shift once the startup host surface is chosen or if the work starts demanding broader report architecture changes

## Execution Run

- Run Status: completed
- Executor: Codex
- Handoff Source: active execplan plus checked-in planning summary
- What Happened: added a compact `planning_surface_health` projection to the planning summary schema and human summary CLI so startup/resume can see clean/not-clean state, warning paths, and the shortest suggested corrective action without rerunning a separate checker.
- Scope Touched: `.agentic-workspace/planning/state.toml`, `.agentic-workspace/planning/execplans/`, `packages/planning/src/repo_planning_bootstrap/{installer,cli}.py`, and `packages/planning/tests/test_installer.py`.
- Validations Run: `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace summary --format json`
- Result For Continuation: the remaining follow-on is no longer a planning-owned startup/resume gap; it is the memory-owned recurring-friction evidence lane from `#263`.
- Next Step: archive this slice, close `#262`, close the completed handshake parent `#264`, and split the remaining memory-owned follow-on into its own candidate lane.

## Finished-Run Review

- Review Status: completed
- Scope Respected: yes
- Proof Status: satisfied
- Intent Served: yes
- Misinterpretation Risk: low
- Follow-On Decision: archive this slice and retire the mixed planning-memory lane in favor of a separate memory-only follow-on for `#263`

## Proof Report

- Validation proof: `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace summary --format json`
- Proof achieved now: startup and resume now expose a compact planning-surface health view with clean/not-clean state, warning paths, and the shortest next corrective action through the existing summary path.
- Evidence for "proof achieved" state: installer tests passed with the new summary schema and human-output assertions, checker tests stayed green, the repo planning checker reported no drift warnings, and the live summary now exposes a `planning_surface_health` block with `status`, `warning_count`, `recommended_next_action`, and compact warning rows.

## Intent Satisfaction

- Original intent: continue and finish the active lane, and commit after each completed slice
- Was original intent fully satisfied?: no
- Evidence of intent satisfaction: the remaining planning-owned startup/resume gap is closed, but the broader product direction still has a separate memory-owned recurring-friction follow-on that should not be forced to remain inside a mixed planning lane.
- Unsolved intent passed to: `.agentic-workspace/planning/state.toml`

## Closure Check

- Slice status: bounded slice complete
- Larger-intent status: open
- Closure decision: archive-but-keep-lane-open
- Why this decision is honest: the planning-owned lane work is complete, but the repo still has a separate memory-owned follow-on around recurring-friction evidence that should stay visible in checked-in planning state instead of being silently dropped.
- Evidence carried forward: startup/resume health now lives in the planning summary path, the handshake parent can close, and the remaining open issue is `#263` under a separate memory-owned candidate lane.
- Reopen trigger: reopen only if startup/resume stops surfacing compact planning-surface health early enough or if new planning-owned drift gaps appear beyond the existing warning path.

## Execution Summary

- Outcome delivered: shipped a compact `planning_surface_health` startup/resume view through `agentic-workspace summary --format json` and the human summary CLI so resumed work can see clean/not-clean state, warning paths, and the shortest corrective action immediately.
- Validation confirmed: `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace summary --format json`
- Follow-on routed to: .agentic-workspace/planning/state.toml, where the mixed planning-memory lane has retired and the remaining memory-owned recurring-friction work from `#263` stands alone under memory-recurring-friction-improvement-pressure.
- Post-work posterity capture: preserve the rule that startup/resume health should remain a thin planning-owned projection over existing warnings, not a second checker or a Memory dependency.
- Knowledge promoted (memory/docs/config): promoted the startup-resume health shape into the planning summary and CLI contract; no Memory-owned implementation change was required.
- Resume from: .agentic-workspace/planning/state.toml, where memory-recurring-friction-improvement-pressure is the only remaining follow-on from this broader direction.
