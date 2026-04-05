# Cross-Module Collaboration Contract

## Goal

- Make concurrent git collaboration safer by documenting canonical-source precedence, branch-vs-trunk state boundaries, and selective write authority across Agentic Memory, Agentic Planning, and the thin workspace layer.

## Non-Goals

- Add new product-managed state or orchestration layers.
- Redesign memory or planning package internals.
- Introduce repo-specific collaboration rules that would not make sense in ordinary target repositories.

## Active Milestone

- Status: completed
- Scope: tightened the canonical integration and collaboration docs, chooser guidance, and maintainer playbook so contributors can tell which surfaces are authoritative to edit, which are generated, and how partial-adoption repos should behave.
- Ready: ready
- Blocked: none
- optional_deps: none

Keep one active milestone by default.

## Immediate Next Action

- Promote the installed-contract collaboration design checklist once the package-authoring guidance can be kept short and directly actionable.

Keep exactly one immediate action by default; avoid multi-step mini-plans here.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/
- README.md

Keep this as a scope guard, not a broad file inventory.

## Invariants

- Memory and planning must remain selectively adoptable.
- The workspace layer must stay thin and orchestration-only.
- Generated surfaces must point back to their canonical sources rather than becoming editable authorities.
- Collaboration rules should clarify boundaries rather than add another policy layer.

Keep invariants contract-shaped and brief.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py
- make maintainer-surfaces

## Completion Criteria

- Integration docs state canonical-source precedence and branch-vs-trunk boundaries explicitly.
- Maintainer docs explain which surfaces are safe to edit directly versus rerendered or package-managed.
- Partial-adoption guidance shows how write authority changes when a repo installs memory only, planning only, or both.

## Drift Log

- 2026-04-06: Activated the cross-module collaboration contract tranche after completing planning and memory collaboration-safety hardening.
- 2026-04-06: Completed the tranche after tightening the integration contract, collaboration-safety rules, chooser guidance, and maintainer routing docs.