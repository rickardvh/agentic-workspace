# Installed-Surface Ambiguity Cleanup

## Goal

- Clear the remaining package-context ambiguity in the installed memory surfaces so memory doctor no longer flags the repo's package-context notes as overlapping or overly procedural.

## Non-Goals

- Reopen the memory package architecture.
- Add another planning or review layer for memory hygiene.
- Eliminate safe nested-repo cache warnings that are not ambiguity bugs.

## Active Milestone

- Status: completed
- Scope: make the package-context notes more distinct, extract any repeated inspection choreography into a checked-in skill, and validate the result with the existing memory doctor and freshness lanes.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None. Milestone completed and archived after the installed package-context ambiguity class disappeared from memory doctor and the remaining output narrowed back to safe nested-repo and optional-append warnings only.

## Blockers

- None.

## Touched Paths

- `.agentic-workspace/memory/repo/`
- `packages/memory/`
- `TODO.md`
- `ROADMAP.md`
- `.agentic-workspace/planning/execplans/`

## Invariants

- Durable package-context notes should carry facts and boundaries, not choreography.
- Repeatable package-context inspection should live in a skill or runbook, not in a domain note.
- Memory freshness and doctor should stay the canonical validation lanes for this cleanup.

## Validation Commands

- `cd packages/memory && uv run pytest tests/test_installer.py`
- `uv run agentic-planning-bootstrap upgrade --target .`
- `uv run agentic-memory-bootstrap upgrade --target .`
- `uv run python scripts/check/check_memory_freshness.py`
- `uv run agentic-memory-bootstrap doctor --target .`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- The remaining manual-review ambiguity on `.agentic-workspace/memory/repo/domains/memory-package-context.md` is cleared or reduced to non-ambiguity advisory output.
- Package-context inspection has a checked-in skill so repeated choreography is no longer implied by the durable note.
- Planning and memory surface checks remain clean after the cleanup.

## Drift Log

- 2026-04-08: Promoted after the roadmap was otherwise drained and memory doctor still reported the same package-context overlap/procedure ambiguity class during a normal maintenance pass.
- 2026-04-08: Completed after adding the package-context inspection skill, tightening the installed package-context notes, and hardening the memory doctor heuristics so package-context companions and metadata sections no longer trigger false-positive ambiguity warnings.
