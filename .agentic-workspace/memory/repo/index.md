# Memory Index

## Purpose

- Memory is the compact anti-rediscovery layer for durable repository knowledge.
- Planning owns current work; skills and operations own procedures; canonical docs own broad explanation.
- Route from the manifest and load only matching notes. Do not bulk-load this tree.

## Routes

- `src/agentic_workspace/**`, `generated/**`, or generators: `domains/example-runtime-boundary.md`
- `packages/memory/**`: `domains/memory-package-context.md`
- `packages/planning/**` or `.agentic-workspace/planning/**`: `domains/planning-package-context.md`
- installed ownership or package/root boundary changes: `decisions/installed-system-consolidation-2026-04-05.md`
- startup, Planning routing, or recurring active-plan friction: `mistakes/recurring-failures.md`

## Budget

- Load this index plus at most two matched notes in ordinary work.
- Direct tasks with no manifest match receive no additional Memory note.
- A `stale_when` match makes the note review evidence, not current authority.

## Verify

- `.agentic-workspace/memory/repo/manifest.toml`
- `uv run python scripts/check/check_memory_freshness.py --strict`

## Load when

- Selecting durable repository context for a task or changed path.

## Review when

- The manifest, retained note set, or routing budget changes.

## Failure signals

- An unregistered note influences an AW decision.
- A procedure or active issue state is added as durable Memory.
- More than two notes are loaded without a concrete route reason.

## Last confirmed

2026-08-11 during issues #2304-#2306 context curation.
