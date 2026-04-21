# Planning Skill-Catalog Integrity Hardening

## Goal

- Align the human-facing planning skill catalogue with the real bundled skill registry and make README-to-registry drift fail in tests.

## Non-Goals

- Do not redesign the broader skill arsenal in this slice.
- Do not move repo-owned skills to a new home yet.
- Do not add new bundled skills only to satisfy documentation shape.

## Active Milestone

- ID: planning-skill-catalog-integrity-hardening
- Status: completed
- Scope: remove nonexistent bundled skills from the planning skill catalogue, clarify the catalogue around the actual bundled set, and add regression coverage that keeps the README aligned with `REGISTRY.json`.
- Ready: ready
- Blocked: none

## Immediate Next Action

- Archive this execplan and leave the remaining skill-system boundary cleanup candidate queued for a separate bounded slice.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `.agentic-workspace/planning/execplans/planning-skill-catalog-integrity-hardening-2026-04-09.md`
- `packages/planning/skills/README.md`
- `.agentic-workspace/planning/skills/README.md`
- `packages/planning/tests/test_skills_catalog.py`

## Invariants

- Human-facing skill docs must not overclaim bundled skills that do not exist.
- `REGISTRY.json` remains the machine-readable source of truth for bundled planning skills.
- Source, payload, and root install copies must stay aligned before the repo relies on the updated contract.

## Validation Commands

- `cd packages/planning && uv run pytest tests/test_skills_catalog.py tests/test_installer.py`
- `make maintainer-surfaces`
- `uv run agentic-planning-bootstrap upgrade --target .`

## Completion Criteria

- The planning skills catalogue lists only real bundled skills.
- Tests fail if the README skill list drifts from the bundled registry ids.
- The root installed planning skills catalogue reflects the corrected bundled set.

## Drift Log

- 2026-04-09: Promoted from the skill-system review after the planning skill catalogue was found to overclaim nonexistent bundled lifecycle skills.
- 2026-04-09: Completed by aligning the planning skill catalogue with the bundled registry and adding a direct README-to-registry assertion in the planning skill catalog tests.
