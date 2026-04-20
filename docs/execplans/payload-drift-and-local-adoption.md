# Payload Drift Detection and Local-only Adoption

## Goal

- Restore high trust in payload integrity through early drift detection.
- Enable "guest mode" usage of Agentic Workspace in unowned repositories through `--local-only` installation.

## Non-Goals

- Redesigning the entire packaging model.
- Broadly rewriting installer internals for both packages in one pass (beyond what's needed for drift/local-only).

## Intent Continuity

- Larger intended outcome: Formalizing Agentic Workspace Memory and Hygiene
- This slice completes the larger intended outcome: no
- Continuation surface: docs/execplans/payload-drift-and-local-adoption.md
- Parent lane: payload-drift-and-installer-knowledge, local-only-adoption-and-external-agent-ergonomics

## Delegated Judgment
- Requested outcome: Restore trust in payload integrity and enable local-only adoption without breaking existing install or upgrade workflows.
- Hard constraints: Preserve monorepo mirroring invariants and avoid broad installer rewrites beyond what this slice needs.
- Agent may decide locally: The exact drift-report wording and the narrowest implementation approach that proves drift and local-only behavior.
- Escalate when: Payload-root resolution or installer flow changes would require a breaking contract change.

## Execution Summary
- **Lane 1 (Payload Drift Detection)**: COMPLETED.
  - Implemented `_detect_payload_drift` in both `planning` and `memory` installers.
  - Integrated drift detection into `agentic-workspace report` and `memory_report`.
  - Verified that missing, differing, or extra payload files are correctly reported.
  - Resolved false positives in tests and non-dev targets by passing `target_root`.
- **Lane 2 (Local-only Adoption)**: PLANNED.

## Required Continuation
- Required follow-on for the larger intended outcome: yes
- Owner surface: docs/execplans/payload-drift-and-local-adoption.md
- Activation trigger: Lane 2 (Local-only Adoption) is ready to start.

## Iterative Follow-Through

- What this slice enabled: Drift detection now fails fast on payload mismatch, so local-only work can build on a stable trust signal.
- Intentionally deferred: Guest-mode wiring and installer/docs cleanup for `--local-only`.
- Discovered implications: The remaining follow-on is a distinct adoption slice, not a refinement of the drift check.
- Proof achieved now: Lane 1 is implemented and checked by the planning/report surfaces.
- Validation still needed: drift detection verification and local-only install verification.
- Next likely slice: Lane 2, local-only adoption.

## Active Milestone

- Status: in-progress
- Scope: Lane 2 (Local-only Adoption)
- Ready: ready
- Blocked: no
- optional_deps: none

## Immediate Next Action

- Implement `--local-only` installer support and the matching CLI path for guest-mode adoption.

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

- [ ] `agentic-workspace report` surfaces drift when a mirror file is missing or differs from root.
- [ ] `agentic-workspace install --local-only` creates a functional installation in `.gemini/agentic-workspace/`.
- [ ] `docs/installer-behavior.md` accurately describes payload resolution for both packages.
- [ ] All tests pass.

## Drift Log

- 2026-04-19: Initial plan created for Lane 1 and 2.
