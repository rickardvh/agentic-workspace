# Execution Scaling Contract

## Goal

- Make the simple-task path explicit in the planning contract so agents can execute small, local work directly while promoting into execplans only when complexity, ambiguity, retry cost, or handoff risk justifies the extra structure.

## Non-Goals

- Force every task through planning surfaces.
- Remove execplans for work that genuinely needs bounded execution structure.
- Add a new top-level planner, classifier, or orchestration layer.

## Active Milestone

- Status: in-progress
- Scope: turn recent maintainer feedback into a bounded execution-scaling tranche covering the direct-execution fast path, operational promotion triggers, minimal residue rules, and validation guidance for the right failure cases.
- Ready: ready
- Blocked: none
- optional_deps: none

Keep one active milestone by default.

## Immediate Next Action

- Re-run the planning checks and decide whether the tranche is complete enough to archive or still needs a final residue-focused pass.

Keep exactly one immediate action by default; avoid multi-step mini-plans here.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- AGENTS.md
- docs/
- packages/planning/
- scripts/check/

Keep this as a scope guard, not a broad file inventory.

## Invariants

- Planning must remain a promotion mechanism for structure, not a startup ritual.
- Simple work should stay simple when direct execution can complete it safely in one coherent pass.
- Direct execution still needs minimal checked-in residue when task state or durable knowledge changes.
- Memory and planning must remain selectively adoptable.

Keep invariants contract-shaped and brief.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py
- make maintainer-surfaces
- cd packages/planning && uv run pytest

## Completion Criteria

- The planning contract states direct execution as an explicit success mode for small, local, well-bounded work.
- Promotion triggers are operational and concrete instead of vague or purely abstract.
- Direct execution has a minimal residue contract that avoids both chat-only follow-up and unnecessary planning residue.
- Validation guidance reflects interrupted work, resumed work, handoff, partial failure recovery, stale residue avoidance, and concurrent branch work rather than only one-shot greenfield tasks.

## Drift Log

- 2026-04-06: Promoted from maintainer feedback after a small-project experiment showed the fast path can succeed without planning, but the transition into planning still needs a clearer checked-in contract.
- 2026-04-06: Tightened the contract in planning docs, shipped bootstrap payloads, and manifest-backed maintainer guidance so direct execution and promotion triggers are stated in the same operational language across installed and self-hosted surfaces.
- 2026-04-06: Expanded the checker's promotion signals to cover resume, handoff, recovery, retry, and concurrent-branch language so the direct-task fast path fails closed when restart cost is no longer trivial.