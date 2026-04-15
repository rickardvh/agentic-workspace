# Compact Operating Map

## Goal

- Close GitHub issue `#84` by adding one compact operating map that tells agents which contract surface to ask first without recreating a broad handbook.

## Non-Goals

- Do not add another long-form concept document.
- Do not restate the full semantics of existing contracts.
- Do not widen this slice into the maintenance-rule or measurement follow-ons from `#88` and `#87`.

## Intent Continuity

- Larger intended outcome: close the remaining GitHub planning-refinement queue and empty the roadmap while keeping concept overhead lower than the operating savings.
- This slice completes the larger intended outcome: no
- Continuation surface: ROADMAP.md

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: ROADMAP.md
- Activation trigger: when the compact operating map lands and the maintenance-rule tranche for `#88` is ready to apply immediately

## Delegated Judgment

- Requested outcome: ship one compact operating map that groups the current contract surfaces into a few practical buckets, answers what to ask first, and points back to the existing report/summary/selector surfaces instead of duplicating them.
- Hard constraints: keep the map smaller than the broader default-path contract, avoid inventing new operational concepts, and make the routing query-first rather than prose-first.
- Agent may decide locally: the exact bucket names, the best compact home for the map, which adjacent docs need a short supporting update, and which dogfood questions best prove the map works.
- Escalate when: the smallest safe implementation would require a broader redesign of lifecycle docs, a new command/schema, or a concept-heavy map that belongs in a larger product rethink.

## Active Milestone

- Status: completed
- Scope: added the compact operating map, aligned the supporting route docs, and dogfooded the map against real startup and planning-inspection questions.
- Ready: complete
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Promote the maintenance-rule tranche from `ROADMAP.md`.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/which-package.md
- docs/default-path-contract.md
- README.md

## Invariants

- The map stays smaller and cheaper than the broader default-path contract.
- The map points to report, summary, and selector surfaces instead of restating their semantics.
- The map answers "what should I ask first?" for ordinary work without becoming a second handbook.

## Contract Decisions To Freeze

- The compact operating map belongs in an existing front-door docs surface rather than a new top-level concept file.
- Startup, active execution, proof/ownership, handoff/setup, and mixed-agent posture are enough buckets for the first slice.
- The map should route into existing query-first surfaces before richer docs.

## Open Questions To Close

- Does `docs/which-package.md` stay compact enough after adding the map, or should one bucket move back into `docs/default-path-contract.md`?
- Which two real questions best prove the map lowers startup and planning-inspection overhead?

## Validation Commands

- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-planning-bootstrap summary --format json`
- `uv run agentic-workspace report --target . --format json`

## Completion Criteria

- GitHub issue `#84` is closed.
- The repo has one compact operating map that points to the right first question/surface buckets.
- The map stays smaller than the broader default-path contract and does not duplicate existing contract semantics.
- One startup question and one active-planning question are answered by following the map without broad rereading.

## Execution Summary

- Outcome delivered: `docs/which-package.md` now carries one compact operating-map table that groups startup/lifecycle, active execution, combined workspace state, proof/ownership, handoff/setup, and mixed-agent posture into query-first buckets, while `docs/default-path-contract.md` stays the fuller route contract behind that smaller map.
- Validation confirmed: `uv run python scripts/check/check_planning_surfaces.py`, `uv run agentic-workspace config --target . --format json`, `uv run agentic-planning-bootstrap summary --format json`
- Follow-on routed to: ROADMAP.md
- Resume from: promote the maintenance rule for `#88`, then expand measurement for `#87` after that guardrail is in place

## Drift Log

- 2026-04-15: Promoted GitHub issue `#84` after the planning-state/reporting hierarchy landed so the operating map can compress a stable route instead of documenting a moving target.
- 2026-04-15: Closed `#84` after dogfooding the map against one startup question (`agentic-workspace config --target . --format json`) and one active-planning question (`agentic-planning-bootstrap summary --format json`) without broad rereading.
