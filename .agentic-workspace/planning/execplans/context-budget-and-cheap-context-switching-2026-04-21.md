# Context Budget And Cheap Context Switching

## Goal

- Promote the next roadmap lane by making live working context smaller, interruptions cheaper, and later reload safer without turning the repo into a second chat log.

## Non-Goals

- Reopening the startup/discovery compression tranche that just completed.
- Expanding planning surfaces into a broad new archive or note system before one bounded context-budget slice proves its value.
- Flattening planning, memory, and workspace responsibilities while reducing context-switch cost.

## Intent Continuity

- Larger intended outcome: Keep the live working set minimal, make context shifts cheaper and safer, and preserve only the residue needed for later reload, review, proof, or continuation.
- This slice completes the larger intended outcome: no
- Continuation surface: `.agentic-workspace/planning/execplans/context-budget-and-cheap-context-switching-2026-04-21.md`
- Parent lane: `context-budget-and-cheap-context-switching`

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `.agentic-workspace/planning/execplans/context-budget-and-cheap-context-switching-2026-04-21.md`
- Activation trigger: complete the first bounded context-budget tranche and reassess the next cheapest pressure point inside the same lane.

## Iterative Follow-Through

- What this slice enabled: the next lane is now active with one bounded first slice instead of a diffuse context-management theme.
- Intentionally deferred: later archive-shape work, wider execplan/queryability work, and delegated-run review surfaces until the first context-budget contract is frozen.
- Discovered implications: the inactive roadmap queue should now begin with `bounded-delegation-and-run-review` once this lane is active.
- Proof achieved now: promotion state will be visible through `agentic-workspace summary --format json` once planning surfaces validate cleanly.
- Validation still needed: run the planning-surface checker and confirm summary reflects this lane as the only active item with the reduced roadmap queue.
- Next likely slice: define the minimum distinction between live working set, recoverable-later context, and required externalized residue, then attach tiny resumability notes and explicit context-shift triggers.

## Delegated Judgment

- Requested outcome: promote the context-budget lane and start it with one bounded implementation-oriented slice.
- Hard constraints: keep the lane bounded to context-budget, interruption, reload, and residue cost; do not reopen startup/front-door compression as the default answer to these issues.
- Agent may decide locally: exact tranche title, first-slice wording, and the smallest credible sequence across the issue cluster.
- Escalate when: the lane would widen into a generic planning rewrite, the first slice cannot be bounded without live issue re-triage, or the work would blur planning, memory, and workspace ownership.

## Active Milestone

- ID: context-budget-and-cheap-context-switching-2026-04-21
- Status: in-progress
- Scope: activate the lane and define the first bounded tranche around live working-set minimization, resumability residue, and explicit context-shift triggers.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Define the first implementation tranche explicitly around `#246`, `#247`, `#248`, and `#249`: freeze the live-working-set vs recoverable-later distinction, required externalized residue, tiny resumability notes, and context-shift triggers before broader archive or query-surface changes.

## Blockers

- None.

## Touched Paths

- `.agentic-workspace/planning/state.toml`
- `.agentic-workspace/planning/execplans/context-budget-and-cheap-context-switching-2026-04-21.md`

## Invariants

- Active lane state must remain recoverable from `todo.active_items` plus one execplan.
- Candidate lanes should leave the inactive roadmap queue once promoted.
- Context-budget work must preserve explicit ownership boundaries between planning, memory, and workspace surfaces.

## Contract Decisions To Freeze

- The first slice for this lane is the context-budget boundary problem, not a generic planning cleanup sweep.
- Live working-set minimization should distinguish active mental load from recoverable-later context and from residue that must be externalized before a shift.
- Resumability should become explicit enough to reduce rereads and interruption loss without turning every slice into archival bureaucracy.

## Open Questions To Close

- What information belongs in the live working set versus recoverable-later context versus mandatory externalized residue?
- What is the smallest resumability-note shape that lowers reload cost without becoming another broad planning artifact?
- Which task boundaries should trigger unloading one working bundle and reloading another?

## Validation Commands

- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-workspace summary --format json`

## Required Tools

- `uv`
- `agentic-workspace`

## Completion Criteria

- `todo.active_items` points at this execplan as the active lane.
- The inactive roadmap queue no longer contains `context-budget-and-cheap-context-switching`.
- The remaining inactive queue begins with `bounded-delegation-and-run-review`.
- Summary/report surfaces show one active planning thread and the updated roadmap ordering.

## Proof Report

- Validation proof (logs, command output, or screenshots): pending
- Proof achieved now: pending
- Evidence for "Proof achieved" state: pending

## Intent Satisfaction

- Original intent: Promote the next lane.
- Was original intent fully satisfied?: pending
- Evidence of intent satisfaction: pending
- Unsolved intent passed to: none

## Closure Check

- Slice status: in-progress
- Larger-intent status: open
- Closure decision: keep-open
- Why this decision is honest: promotion starts the lane but does not satisfy the broader context-budget outcome.
- Evidence carried forward: this execplan and the active queue entry
- Reopen trigger: none

## Execution Summary

- Outcome delivered: active planning lane promotion for context-budget and cheap context switching.
- Validation confirmed: pending
- Follow-on routed to: none yet
- Knowledge promoted (Memory/Docs/Config): none
- Resume from: define and execute the first bounded context-budget tranche

## Drift Log

- 2026-04-21: Promoted the `context-budget-and-cheap-context-switching` roadmap lane into active planning after the product-compression tranche completed.
