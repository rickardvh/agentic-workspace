# Memory Contract Framing

## Goal

- Clarify `memory/mistakes/recurring-failures.md` as anti-trap and anti-rediscovery memory rather than bug tracking, and tighten the high-level memory-package framing so skimming readers are pushed toward one-home ownership and subordination to planning earlier.

## Non-Goals

- Redesign the memory taxonomy or routing system.
- Reopen the weak-authority current-note contract that already landed.
- Build new automation around memory capture or issue sync.

## Active Milestone

- Status: completed
- Scope: update the recurring-failures contract, top-level memory framing, and shipped memory workflow/docs so the package is harder to overread as a generic bug tracker or broad fallback knowledge store.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None. Milestone completed and archived after the recurring-failures contract pass, high-level framing updates, and focused memory validation lane all passed.

## Blockers

- None.

## Touched Paths

- `packages/memory/`
- `memory/`
- `.agentic-workspace/memory/`
- `docs/`

## Invariants

- Memory must remain selectively adoptable without planning installed.
- Recurring-failures must stay distinct from tests, issue tracking, and active planning.
- High-level framing should bias toward expensive-to-rediscover knowledge and one primary home per fact.

## Validation Commands

- `cd packages/memory && uv run pytest`
- `uv run python scripts/check/check_memory_freshness.py`

## Completion Criteria

- The recurring-failures surface is clearly framed as anti-trap memory rather than bug tracking.
- High-level memory docs and workflow wording bias earlier toward anti-rediscovery value, one-home ownership, and planning subordination.
- The shipped memory package surfaces stay internally consistent after the docs pass.

## Drift Log

- 2026-04-08: Promoted from live GitHub issue intake after issue `#5` proved compound and issues `#3` and `#4` stayed open as duplicate recurring-failures signals.
- 2026-04-08: Completed after updating recurring-failures, memory index/workflow framing, shipped package README surfaces, and focused installer assertions.
