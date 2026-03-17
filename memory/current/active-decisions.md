# Active Decisions

## Status

Active

## Scope

- Current high-impact technical or operational decisions for `agentic-memory`.

## Applies to

- `<KEY_SUBSYSTEMS>`
- `<KEY_REPO_DOCS>`
- `<RELEVANT_RUNTIME_OR_INTERFACE_PATHS>`

## Load when

- Choosing implementation strategy across major subsystems.
- Deciding which source of truth to trust during a refactor.

## Review when

- Architecture boundaries change.
- Public interfaces or core operating modes change.

## Failure signals

- Conflicting plans reference different sources of truth.
- A change proposal depends on an unconfirmed default or stale assumption.

## Rule or lesson

- Record only the active decisions that materially affect implementation choices.
- Move mature, long-lived rationale into `memory/decisions/` when it no longer belongs in a current-orientation note.
- Keep repo-local scope and guardrails in `AGENTS.md`; keep reusable operating rules in `memory/system/WORKFLOW.md`.

## How to recognise it

- You are making a trade-off that affects multiple subsystems.
- You need to know which current boundary or contract is intentional.

## Verify

- Check the active architecture docs, contracts, or decision records referenced in `## Applies to`.
- Confirm that older decisions have been moved out if they are no longer current.

## Verified against

- `AGENTS.md`
- `memory/system/WORKFLOW.md`
- `README.md`
- `src/repo_memory_bootstrap/installer.py`

## What to do

- Keep this file current and compact.
- Prefer one line per active decision unless more detail is required for safe implementation.

## Last confirmed

2026-03-17 during workflow split review
