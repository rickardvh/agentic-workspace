# Lazy Discovery Measurements

## Purpose

This page defines the first cheap measurement framework for lazy discovery.

Use it when a compact contract change claims to reduce reading or token cost and needs proof stronger than “the schema looks cleaner.”

## Rule

Measure one-answer retrieval against the corresponding full-surface dump.

Prefer cheap reproducible proxies over invented exactness.

## First Framework

Use:

```bash
uv run python scripts/check/measure_lazy_discovery.py --target .
```

The first framework measures:

- UTF-8 bytes returned
- character count returned
- a simple token proxy: `ceil(character_count / 4)`

It compares:

- the full machine-readable surface for a question
- the selector-shaped narrow answer for the same question

Current covered questions:

- choosing the validation lane
- reading the current proof state
- resolving the owner of active execution state

## Boundaries

- This is a retrieval-size proxy, not exact model token accounting.
- The first pass is intentionally small and static.
- Do not turn this into runtime telemetry or generic analytics.

## Relationship To Other Docs

- Use [`docs/compact-contract-profile.md`](docs/compact-contract-profile.md) for the selector and compact-answer contract itself.
- Use [`docs/design-principles.md`](docs/design-principles.md) for the “proof should beat preference” rule that motivates this measurement.
