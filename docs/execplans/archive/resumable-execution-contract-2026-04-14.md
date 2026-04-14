# Resumable Execution Contract

## Goal

- Define one smaller machine-readable active execution contract so a new or weaker agent can resume from the current next action, current scope, proof expectations, and escalation boundary without rereading the full execplan.
- Build it directly on top of the new compact intent contract instead of inventing another workflow layer.

## Non-Goals

- Replace the execplan itself.
- Add mandatory new authoring sections to every plan.
- Solve ordinary-work cross-agent handoff in full generality in this slice.

## Intent Continuity

- Larger intended outcome: make active work resumable from the smallest useful checked-in contract so restart and cross-agent continuation stay cheap.
- This slice completes the larger intended outcome: no
- Continuation surface: `ROADMAP.md`

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `ROADMAP.md`
- Activation trigger: the resumable execution contract lands and ordinary work still needs a separate cross-agent handoff or proof-selection layer to keep restart and supervision cost low.

## Delegated Judgment

- Requested outcome: project the current active execplan into one compact resumable execution contract, align the planning docs, and dogfood it against this repo's live active work.
- Hard constraints: keep the contract derived from existing fields; keep it smaller than the full execplan; preserve explicit proof and escalation boundaries; validate package source, payload, and root install together.
- Agent may decide locally: the exact resumable-contract shape, which current-state fields are essential, and the smallest doc/test updates that keep restart behavior explicit without broadening the planning schema.
- Escalate when: the slice would require new mandatory plan sections, broad TODO schema expansion, or a heavy handoff system rather than one compact resumable execution object.

## Active Milestone

- ID: resumable-execution-contract
- Status: completed
- Scope: add one machine-readable resumable execution contract to planning summary, align the planning docs, and prove it against this repo's live active work.
- Ready: ready
- Blocked: none
- optional_deps: GitHub issue `#34`

## Immediate Next Action

- None. Slice completed; promote proof-selection or ordinary-work handoff follow-through next.

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

- The resumable contract must stay smaller than the active execplan.
- Current next action, proof, and escalation boundary must be recoverable without broad narrative rereads.
- The slice must leave active planning authoring cheaper, not heavier.

## Contract Decisions To Freeze

- The resumable execution contract should layer on top of `active_contract`, not duplicate or replace it.
- The first resumable object should answer restart and continuation questions for one active slice before trying to become a generic handoff artifact.

## Open Questions To Close

- Which additional current-state fields are the minimum required for a safe restart beyond the active intent contract?
- How should the resumable contract distinguish current-state recovery from broader ordinary-work cross-agent handoff?

## Validation Commands

- `cd packages/planning && uv run pytest tests/test_installer.py`
- `cd packages/planning && uv run ruff check .`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- Planning exposes one compact resumable execution contract for the current active slice.
- The contract preserves current next action, current scope, proof expectations, escalation boundary, and minimal refs in one smaller object.
- Docs and tests align to the same resumable contract.
- The contract is dogfooded against this repo's active work before archive.

## Execution Summary

- Outcome delivered: `agentic-planning-bootstrap summary --format json` now exposes `resumable_contract` as a smaller current-state restart contract layered on top of `active_contract`, carrying current next action, current milestone scope, completion criteria, proof expectations, escalation boundary, blockers, and minimal refs in one machine-readable object.
- Validation confirmed: `cd packages/planning && uv run pytest tests/test_installer.py -q`; `cd packages/planning && uv run ruff check .`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-planning-bootstrap summary --format json`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run python scripts/check/check_source_payload_operational_install.py`.
- Follow-on routed to: `ROADMAP.md` candidates `Nearly automatic proof selection` and `Cross-agent handoff as an ordinary-work mode`.
- Resume from: promote the next continuity slice if ordinary work still needs narrower proof selection or a first-class ordinary-work handoff contract.

## Drift Log

- 2026-04-14: Promoted from GitHub issue `#34` after the compact active intent contract landed as the prerequisite continuity slice.
- 2026-04-14: Completed by projecting the current active execplan into `planning_summary` as `resumable_contract`, adding the canonical resumable-execution doc, refreshing the root planning install, and dogfooding the result against this repo's live active execplan.
