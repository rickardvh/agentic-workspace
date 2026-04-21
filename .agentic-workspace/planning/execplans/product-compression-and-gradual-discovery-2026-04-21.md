# Product Compression And Gradual Discovery

## Goal

- Promote the next roadmap lane by making the visible product shape smaller and more progressively discoverable without losing real leverage.

## Non-Goals

- Reopening the ownership-boundary lane that just closed under `#231` and `#240`.
- Broad file relocation unrelated to startup/discovery/compression pressure.
- Inventing a new public extension or module system while reducing startup surface cost.

## Intent Continuity

- Larger intended outcome: Make the visible product shape smaller and more progressively discoverable while preserving real leverage.
- This slice completes the larger intended outcome: no
- Continuation surface: `.agentic-workspace/planning/execplans/product-compression-and-gradual-discovery-2026-04-21.md`
- Parent lane: `product-compression-and-gradual-discovery`

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `.agentic-workspace/planning/execplans/product-compression-and-gradual-discovery-2026-04-21.md`
- Activation trigger: complete the first bounded startup/discovery tranche and reassess the next compression slice from the same lane.

## Iterative Follow-Through

- What this slice enabled: the next roadmap lane is now active, bounded, and recoverable from repo-owned planning surfaces.
- Intentionally deferred: README tightening, doctrine compression, and broader query-surface cleanup until the startup/discovery contract is frozen.
- Discovered implications: the inactive roadmap queue should now begin with system-intent-and-planning-trust once this lane is active.
- Proof achieved now: promotion state will be visible through `agentic-workspace summary --format json` once planning surfaces validate cleanly.
- Validation still needed: run the planning-surface checker and confirm summary reflects one active item plus the reduced roadmap.
- Next likely slice: implement the minimum startup operating model from `#223` plus the gradual-discovery and capability-advertisement tranche from `#227` and `#228`.

## Delegated Judgment

- Requested outcome: Promote the next roadmap lane and start the product-compression-and-gradual-discovery thread cleanly.
- Hard constraints: keep the lane bounded to startup/discovery/compression pressure; do not reopen closed ownership cleanup unless new evidence demands it.
- Agent may decide locally: exact tranche title, bounded first-slice wording, and compact continuation framing.
- Escalate when: the lane boundary becomes ambiguous, the requested outcome would widen into a different lane, or the first slice cannot be bounded without live issue re-triage.

## Active Milestone

- ID: product-compression-and-gradual-discovery-2026-04-21
- Status: in-progress
- Scope: activate the lane and define the first bounded tranche around the tiny safe startup model and gradual discovery cues.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Define the first implementation tranche explicitly as `#223` + `#227` + `#228`: freeze the tiny safe startup model, boundary-triggered escalation cues, and compact top-level capability advertisement before README or doctrine compression.

## Blockers

- None.

## Touched Paths

- `.agentic-workspace/planning/state.toml`
- `.agentic-workspace/planning/execplans/product-compression-and-gradual-discovery-2026-04-21.md`
- `.agentic-workspace/planning/reviews/product-compression-context-cost-review-2026-04-21.md`

## Invariants

- Active lane state must remain recoverable from `todo.active_items` plus one execplan.
- Completed roadmap lanes should leave the inactive queue instead of lingering as stale candidates.
- Promotion should not silently widen the requested outcome beyond the product-compression/discovery lane.

## Contract Decisions To Freeze

- The first slice for this lane is the startup/discovery boundary problem, not a generic “make docs smaller” sweep.
- Gradual discovery should stay capability- and boundary-triggered rather than ontology-first.
- Root-visible product shape should shrink by better routing and quieter defaults before introducing new concepts.

## Open Questions To Close

- Which current startup surfaces are genuinely required for the tiny safe model versus legacy or secondary discovery aids?
- What escalation cues should make deeper concepts discoverable without forcing upfront ontology load?
- How should top-level module capability advertisement stay compact while still signaling when deeper concepts become relevant?
- Which README and doctrine content should be treated as follow-on compression targets only after the startup/discovery contract is frozen?

## Validation Commands

- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-workspace summary --format json`

## Required Tools

- `uv`
- `agentic-workspace`

## Completion Criteria

- `todo.active_items` points at this execplan as the active lane.
- The completed ownership-boundary lane is no longer present in the inactive roadmap queue.
- The remaining inactive queue begins with `system-intent-and-planning-trust`.
- Summary/report surfaces show one active planning thread and the updated roadmap ordering.

## Proof Report

- Validation proof (logs, command output, or screenshots): pending
- Proof achieved now: pending
- Evidence for "Proof achieved" state: pending

## Intent Satisfaction

- Original intent: Promote the next lane.
- Was original intent fully satisfied?: not yet
- Evidence of intent satisfaction: pending
- Unsolved intent passed to: none

## Execution Summary

- Outcome delivered: not completed yet
- Validation confirmed: pending
- Follow-on routed to: none yet
- Knowledge promoted (Memory/Docs/Config): none
- Resume from: define and execute the first bounded startup/discovery tranche

## Drift Log

- 2026-04-21: Promoted the `product-compression-and-gradual-discovery` roadmap lane into active planning after the ownership-boundary lane closed.
