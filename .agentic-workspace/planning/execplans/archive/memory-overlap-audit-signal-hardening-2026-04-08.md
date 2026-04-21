# Memory Overlap-Audit Signal Hardening

## Goal

- Reduce repeated low-signal overlap warnings around the installed-system decision family and adjacent package-context notes so memory doctor output remains trustworthy during normal maintenance.

## Non-Goals

- Perform broad memory-note consolidation across the repo.
- Redesign the entire memory doctor or freshness systems.
- Suppress genuine multi-home drift warnings for unrelated note families.

## Active Milestone

- Status: completed
- Scope: inspected the current overlap-warning cluster, tightened the overlap heuristic and current-note handoff handling for this class of adjacent durable notes, and proved the repeated low-signal warnings were reduced without hiding the remaining package-context overlap problem.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None. Archived after the overlap-audit warning cluster was reduced and the focused validation lane passed.

## Blockers

- None.

## Touched Paths

- `packages/memory/src/`
- `packages/memory/tests/`
- `.agentic-workspace/memory/repo/`
- `docs/`

## Invariants

- The overlap audit must still surface genuinely ambiguous multi-home durable notes.
- The fix should prefer structural evidence over brittle keyword suppression.
- Current-note authority and freshness checks must stay intact.

## Validation Commands

- `uv run agentic-memory-bootstrap doctor --target .`
- `uv run python scripts/check/check_memory_freshness.py`
- `cd packages/memory && uv run pytest`

## Completion Criteria

- The repeated low-signal installed-system overlap cluster is reduced or reclassified to match the real maintenance risk.
- A focused regression test covers the chosen heuristic or note-family rule.
- Memory doctor and freshness outputs remain coherent for the current repo after the change.

## Drift Log

- 2026-04-08: Promoted from `ROADMAP.md` after another normal maintenance cycle confirmed the overlap audit remained the dominant unresolved workflow signal.
- 2026-04-08: Tightened the decision-family overlap audit to require topical alignment in titles, taught current-note overlap pressure to respect explicit durable-handoff wording, and reduced the live doctor output to one remaining package-context overlap warning.
