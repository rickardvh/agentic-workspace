# Compact Intent Contract

## Goal

- Define one compact machine-readable intent contract for active work so requested outcome, hard constraints, proof expectations, and escalation boundaries survive across sessions without broad rereading.
- Reuse the existing execplan contract instead of adding a second planning schema.

## Non-Goals

- Add another required execplan section.
- Turn planning into a narrative handoff system or backlog database.
- Solve the full minimal-resumable-execution problem in this slice.

## Intent Continuity

- Larger intended outcome: make active planning state cheap enough to resume and hand off across agents, sessions, and subscriptions without reconstructing the human's intent from prose and chat residue.
- This slice completes the larger intended outcome: no
- Continuation surface: `ROADMAP.md`

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `ROADMAP.md`
- Activation trigger: the compact intent contract lands and ordinary repo work still needs a smaller resumable execution slice to avoid broad rereads.

## Delegated Judgment

- Requested outcome: expose a compact active intent contract derived from the existing execplan/TODO planning contract, align the planning docs around it, and dogfood it in this repo.
- Hard constraints: keep the contract small; derive it from existing fields instead of inventing a second plan schema; keep package source, payload, and root install aligned; validate with package-local tests first.
- Agent may decide locally: the exact summary shape, the narrowest existing sections to project from, the minimal doc updates needed to keep the contract trustworthy, and the smallest dogfood path that proves the new contract reduces rereading.
- Escalate when: the slice would require a new mandatory plan section, broad TODO schema growth, or a generic task-history system instead of a compact active-work contract.

## Active Milestone

- ID: compact-intent-contract
- Status: completed
- Scope: add one compact machine-readable active intent-contract projection to planning summary, document the contract, and prove it against this repo's live active planning state.
- Ready: ready
- Blocked: none
- optional_deps: GitHub issue `#33`

## Immediate Next Action

- None. Slice completed; promote the minimal resumable execution-contract follow-through.

## Blockers

- None.

## Touched Paths

- `packages/planning/src/repo_planning_bootstrap/installer.py`
- `packages/planning/src/repo_planning_bootstrap/cli.py`
- `packages/planning/tests/test_installer.py`
- `packages/planning/README.md`
- `packages/planning/bootstrap/docs/`
- root planning docs and root installed planning payload after refresh

## Invariants

- The contract must be recoverable from existing planning fields.
- One bounded active task should be resumable from the compact contract plus narrow refs.
- The new surface should reduce rereading, not add another required planning dashboard.

## Contract Decisions To Freeze

- The first compact intent contract should be a projection of existing plan fields, not a new authoring burden.
- The canonical machine-readable home should be an existing planning query surface, not a new top-level command unless the existing surface proves insufficient.

## Open Questions To Close

- Which existing planning fields are the minimum required compact intent bundle for safe restart?
- Should the compact intent contract live only in planning summary, or should the root workspace layer mirror it once the planning-side contract proves useful?

## Validation Commands

- `cd packages/planning && uv run pytest tests/test_installer.py`
- `cd packages/planning && uv run ruff check .`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- Planning exposes one machine-readable compact intent contract for the current active work.
- The contract preserves requested outcome, hard constraints, local latitude, proof expectations, escalation boundaries, and minimal refs without requiring a new execplan section.
- Docs and tests align to the same compact contract.
- The new surface is dogfooded against this repo's live active planning state.

## Execution Summary

- Outcome delivered: `agentic-planning-bootstrap summary --format json` now exposes `active_contract` as a compact machine-readable projection of the current active execplan contract, carrying requested outcome, hard constraints, local latitude, escalation boundary, touched scope, proof expectations, and minimal refs without adding a new required plan section.
- Validation confirmed: `cd packages/planning && uv run pytest tests/test_installer.py -q`; `cd packages/planning && uv run ruff check .`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`; `uv run agentic-planning-bootstrap summary --format json`; `uv run python scripts/check/check_planning_surfaces.py`.
- Follow-on routed to: `ROADMAP.md` candidate `Minimal resumable execution contract`.
- Resume from: promote the resumable-execution slice if ordinary work still needs current next action, proof, and escalation state in one smaller active contract.

## Drift Log

- 2026-04-14: Promoted from GitHub issue `#33` after the startup-entrypoint tranche closed and the next clearest continuity gap was preserving active intent in a smaller machine-readable contract.
- 2026-04-14: Completed by projecting the existing execplan contract into `planning_summary` as `active_contract`, adding the canonical intent-contract doc, refreshing the root planning install, and dogfooding the result against this repo's live active execplan.
