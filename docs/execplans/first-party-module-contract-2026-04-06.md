# First-Party Module Contract

## Goal

- Formalize the shared internal contract that planning and memory already use as first-party modules so the workspace layer can orchestrate them through explicit metadata and adapter rules instead of module-specific branching.

## Non-Goals

- Design the third-party extension boundary yet.
- Build a full registry or capability model in one pass.
- Reopen stable package contract boundaries that just froze unless the new contract work proves a real conflict.

## Active Milestone

- Status: in-progress
- Scope: audit the current workspace orchestration path, name the shared first-party module contract it already assumes, and tighten root-module boundaries where that contract is currently implicit or duplicated.
- Ready: ready
- Blocked: none
- optional_deps: none

Keep one active milestone by default.

## Immediate Next Action

- Audit the current workspace module descriptors, result adapters, and lifecycle dispatch path to list the metadata and behaviors that already act like an internal first-party module contract.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/execplans/
- src/
- packages/

Keep this as a scope guard, not a broad file inventory.

## Invariants

- The workspace layer must stay a thin orchestrator, not a second owner of planning or memory semantics.
- First-party module metadata should be explicit before any registry or plugin design builds on it.
- Planning and memory must remain selectively adoptable and independently meaningful.
- Shared orchestration contracts should reduce bespoke branching rather than hide it under new abstraction names.
- Validation should prove boundary clarity and reporting consistency, not just type-shape cleanup.

Keep invariants contract-shaped and brief.

## Validation Commands

- uv run pytest tests/test_workspace_cli.py
- cd packages/planning && uv run pytest
- cd packages/memory && uv run pytest
- uv run python scripts/check/check_planning_surfaces.py

## Completion Criteria

- The workspace layer has an explicit description of the shared first-party module contract it expects from planning and memory.
- Module metadata, lifecycle hooks, and report adaptation no longer depend on undocumented package-specific assumptions.
- Root orchestration code gets simpler or more uniform rather than more magical.
- The resulting contract is narrow enough to support later registry work without prematurely acting like a public plugin API.

## Drift Log

- 2026-04-06: Promoted after stable contract freeze landed cleanly enough that the next orchestration risk is no longer package-surface ambiguity but implicit module-contract knowledge living in the workspace layer.