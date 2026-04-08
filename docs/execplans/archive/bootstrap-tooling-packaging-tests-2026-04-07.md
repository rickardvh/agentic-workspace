# Execplan: Bootstrap-Tooling Packaging Tests

## Goal

Add artifact-level packaging tests for all three shipped packages (`agentic-workspace`, `agentic-planning-bootstrap`, `agentic-memory-bootstrap`) so that builds pass local source tests only when the actual wheel and sdist artifacts contain required payload files, bundled skills, and helper scripts.

## Non-Goals

- Do not refactor packaging metadata or build configuration in this pass.
- Do not add new payload files or restructure existing ones.
- Do not change the installer or bootstrap logic itself.

## Active Milestone

- Status: completed
- Ready: ready
- Blocked: none

## Immediate Next Action

Archived after the packaging tests were tightened and validated.

## Touched Paths

- `tests/test_workspace_packaging.py`
- `packages/planning/tests/test_packaging.py`
- `packages/memory/tests/test_packaging.py`
- `scripts/check/check_packaging_artifacts.py` (helper, optional)

## Validation Commands

- `uv run pytest tests/test_workspace_packaging.py`
- `uv run pytest packages/planning/tests/test_packaging.py`
- `uv run pytest packages/memory/tests/test_packaging.py`

## Completion Criteria

- [x] Root workspace package test asserts wheel/sdist contain `.agentic-workspace/WORKFLOW.md` and `.agentic-workspace/OWNERSHIP.toml`
- [x] Planning package test asserts wheel/sdist contain required payload files and generated routing docs
- [x] Memory package test asserts wheel/sdist contain required payload files and skills
- [x] All three tests pass in the CI lane and locally with `make check-all`
- [x] Packages produce identical file inventories across clean source builds and artifact installs

## Invariants

- Packaging tests must run without requiring external package installations (build artifacts locally).
- Tests should fail loudly if required payload files are missing from any artifact.

## Drift Log

- 2026-04-07: Promoted from `docs/reviews/bootstrap-tooling-followup-requirements-2026-04-07.md` as high-priority friction-confirmed finding.
- 2026-04-08: Archived after the root, planning, and memory packaging tests were validated.
