# Payload Drift Detection and Local-only Adoption

## Goal

- Restore high trust in payload integrity through early drift detection.
- Enable "guest mode" usage of Agentic Workspace in unowned repositories through `--local-only` installation.

## Non-Goals

- Redesigning the entire packaging model.
- Broadly rewriting installer internals for both packages in one pass (beyond what's needed for drift/local-only).

## Intent Continuity

- Larger intended outcome: Formalizing Agentic Workspace Memory and Hygiene
- This slice completes the larger intended outcome: yes
- Continuation surface: none
- Parent lane: payload-drift-and-installer-knowledge, local-only-adoption-and-external-agent-ergonomics

## Delegated Judgment
- Requested outcome: Restore trust in payload integrity and enable local-only adoption without breaking existing install or upgrade workflows.
- Hard constraints: Preserve monorepo mirroring invariants and avoid broad installer rewrites beyond what this slice needs.
- Agent may decide locally: The exact drift-report wording and the narrowest implementation approach that proves drift and local-only behavior.
- Escalate when: Payload-root resolution or installer flow changes would require a breaking contract change.

## Execution Summary
- Outcome delivered: enabled explicit local-only install support through `agentic-workspace install --local-only`, wrote the workspace into `.gemini/agentic-workspace/`, and updated the surrounding docs and tests so the guest-mode path is explicit rather than inferred.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q`; `uv run python scripts/check/check_planning_surfaces.py`.
- Follow-on routed to: none.
- Resume from: none.

## Required Continuation
- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: Drift detection now fails fast on payload mismatch, so local-only work can build on a stable trust signal.
- Intentionally deferred: none for this lane.
- Discovered implications: Local-only adoption is now a first-class install path rather than a hidden inference path.
- Proof achieved now: Lane 1 and Lane 2 are implemented and checked by the planning/report surfaces.
- Validation still needed: none for this execplan slice.
- Next likely slice: none.

## Active Milestone

- Status: completed
- Scope: Lane 2 (Local-only Adoption)
- Ready: no
- Blocked: no
- optional_deps: none

## Immediate Next Action

- No further action required for this execplan slice.

## Blockers

- None.

## Touched Paths

- packages/planning/src/repo_planning_bootstrap/installer.py
- packages/memory/src/repo_memory_bootstrap/installer.py
- src/agentic_workspace/cli.py
- docs/installer-behavior.md

## Invariants

- `agentic-workspace report` must be the primary surface for discovering drift.
- Local-only mode must never write to tracked repository files (except .gitignore).

## Validation Commands

- `agentic-workspace report`
- `agentic-workspace install --local-only`
- `uv run pytest packages/planning/tests`
- `uv run pytest packages/memory/tests`

## Completion Criteria

- [x] `agentic-workspace report` surfaces drift when a mirror file is missing or differs from root.
- [x] `agentic-workspace install --local-only` creates a functional installation in `.gemini/agentic-workspace/`.
- [x] `docs/installer-behavior.md` accurately describes payload resolution for both packages.
- [x] All tests pass.

## Drift Log

- 2026-04-19: Initial plan created for Lane 1 and 2.
