# Planning Hierarchy Routing Tranche

## Goal

- Align `agentic-planning-bootstrap summary --format json` and `agentic-planning-bootstrap report --format json` with the simplified planning hierarchy, and tighten the owned routing rules between `ROADMAP.md`, `TODO.md`, execplans, and reviews.

## Non-Goals

- Redesign `ROADMAP.md`, `TODO.md`, execplans, or reviews into a new planning system.
- Add a second canonical planning record beside `planning_record`.
- Add a project-management backlog, queue database, or new planning module.

## Intent Continuity

- Larger intended outcome: make `ROADMAP.md`, `TODO.md`, execplans, reviews, and machine-readable planning state agree on the simplified hierarchy and routing rules.
- This slice completes the larger intended outcome: yes
- Continuation surface: none
- Parent lane: planning-hierarchy-routing-queue

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: planning now exposes the hierarchy view directly and defines a quieter routing boundary for active, near-term, deferred, and review-shaped work.
- Intentionally deferred: standing-intent durability, optimization-bias/setup-findings follow-through, and memory habitual-pull work that depend on the new hierarchy staying stable first.
- Discovered implications: `TODO.md` needs a compact near-term queue projection when active work should hand off into the next same-thread chunk without widening the current execplan.
- Proof achieved now: summary/report output, canonical docs, and this repo's live plan now agree on active chunk, parent lane, near-term queue, continuation owner, and proof state.
- Validation still needed: none beyond normal future dogfooding on later planning tranches.
- Next likely slice: promote the standing-intent durability lane from `ROADMAP.md`.

## Delegated Judgment

- Requested outcome: finish the planning hierarchy lane by making compact hierarchy state, TODO near-term queue rules, and surface routing agree in one shipped contract.
- Hard constraints: keep `planning_record` canonical; derive new hierarchy state from existing planning surfaces; keep `TODO.md` activation-focused rather than backlog-shaped; avoid new planning artifacts or tracker abstractions.
- Agent may decide locally: the exact projection name, whether one small routing doc is enough, which docs need the strongest ownership language, and the narrowest validation that proves source/payload/root alignment.
- Escalate when: the best remaining change would require a new queue file, heavy review automation, or broad redesign of candidate lanes, standing intent, or memory boundaries.

## Active Milestone

- ID: planning-hierarchy-routing-tranche
- Status: completed
- Scope: complete the hierarchy lane by landing the derived hierarchy view plus the routing and TODO-boundary contract it needs.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed tranche, close the planning-hierarchy issues it satisfied, and advance the roadmap to the standing-intent lane.

## Blockers

- None.

## Touched Paths

- TODO.md
- .agentic-workspace/planning/execplans/planning-hierarchy-routing-tranche-2026-04-17.md
- packages/planning/src/repo_planning_bootstrap/installer.py
- packages/planning/src/repo_planning_bootstrap/cli.py
- packages/planning/bootstrap/docs/planning-routing-contract.md
- packages/planning/bootstrap/.agentic-workspace/planning/execplans/README.md
- packages/planning/bootstrap/.agentic-workspace/planning/execplans/TEMPLATE.md
- packages/planning/bootstrap/.agentic-workspace/planning/upstream-task-intake.md
- packages/planning/bootstrap/.agentic-workspace/docs/candidate-lanes-contract.md
- packages/planning/README.md
- packages/planning/tests/test_installer.py

## Invariants

- `planning_record` remains the canonical compact active planning state.
- The new hierarchy view must reduce rereading and not become a second planner state store.
- The hierarchy stays explicit across direction (`ROADMAP.md`), activation (`TODO.md`), execution (`.agentic-workspace/planning/execplans/`), and bounded review (`.agentic-workspace/planning/reviews/`).

## Contract Decisions To Freeze

- The hierarchy view should be a projection over existing planning state, not a new owned artifact.
- `TODO.md` may hold one active chunk plus the smallest near-term same-thread queue, but it must not become backlog storage.
- Discovered-work routing should be expressed through one owned contract rather than scattered prose.

## Open Questions To Close

- None.

## Validation Commands

- uv run pytest packages/planning/tests/test_installer.py -q
- uv run python scripts/check/check_planning_surfaces.py
- uv run python scripts/check/check_source_payload_operational_install.py
- uv run agentic-planning-bootstrap summary --format json
- uv run agentic-planning-bootstrap report --format json
- uv run agentic-planning-bootstrap upgrade --target .
- uv run agentic-memory-bootstrap upgrade --target .

## Required Tools

- uv

## Completion Criteria

- Planning summary exposes one compact hierarchy projection derived from active planning state when available.
- Planning report surfaces the same hierarchy and near-term queue view cheaply enough for normal restart/use.
- Canonical planning docs define one routing contract between roadmap, TODO, execplans, and reviews without reopening backlog-like queue shapes.
- This repo's live plan and queue dogfood the hierarchy/routing contract without drift warnings.

## Execution Summary

- Outcome delivered: added `hierarchy_contract` to planning summary/reporting, exposed near-term TODO queue state, and defined one canonical planning-routing contract across roadmap, TODO, execplans, and reviews.
- Validation confirmed: `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run python scripts/check/check_source_payload_operational_install.py`; `uv run agentic-planning-bootstrap summary --format json`; `uv run agentic-planning-bootstrap report --format json`; final root refresh via both package upgrade commands.
- Follow-on routed to: `ROADMAP.md` next lane `standing-intent-durability`
- Resume from: no further action in this tranche; promote the standing-intent lane when the next bounded slice is ready.

## Drift Log

- 2026-04-17: Promoted the top-priority planning hierarchy lane.
- 2026-04-17: Expanded the tranche from summary/report alignment into full hierarchy/routing closure so the checked-in plan matches the actual shipped work.
