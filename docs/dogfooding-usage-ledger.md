# Dogfooding Usage Ledger

## Purpose

This ledger records how the product is used in ordinary repo work without shipping telemetry.

Use it to capture:

- which surfaces were used
- which surfaces were skipped
- why a feature was chosen or avoided
- whether the choice felt obvious, forced, confusing, or unnecessary

This is a local evaluation aid, not a product analytics system.

## Scope

Track only repo-local dogfooding and maintenance work.

Do not try to measure every interaction.
Do not collect personal data.
Do not record anything that would be better expressed as an execplan, roadmap item, or review finding.

## Entry Shape

Record one entry per meaningful task or decision point.

Each entry should include:

- Date:
- Task class:
- Goal:
- Surfaces used:
- Surfaces skipped:
- Selection reason:
- Skip reason:
- Friction:
- Cost note:
- Follow-up:

## Ledger Template

```md
## <date> - <task class>

- Goal:
- Surfaces used:
- Surfaces skipped:
- Selection reason:
- Skip reason:
- Friction:
- Cost note:
- Follow-up:
```

## Review Workflow

Use the ledger in three steps:

1. Record usage during the task, not only afterward.
2. Review the recent entries for repeated skipped surfaces, repeated confusion, or repeated fallback paths.
3. Route repeated signals into `ROADMAP.md`, `TODO.md`, a review artifact, or canonical docs.

## Relationship To Existing Measurement Lane

Use `docs/lazy-discovery-measurements.md` for retrieval-cost measurement.

Use this ledger for ordinary-use pull and feature-choice reasons.

Together they answer different questions:

- lazy-discovery measurements: how cheap a route is to read or load
- usage ledger: whether the route is actually chosen in daily work and why

## Review Questions

When reviewing the ledger, ask:

- Which surfaces are consistently used first?
- Which surfaces are consistently skipped?
- Which features require explanation before use?
- Which choices appear to depend on insider knowledge?
- Which skipped surfaces should be merged, demoted, or better surfaced?

## Closure Rule

If a repeated pattern becomes durable product guidance, promote it into canonical docs or planning.

If it only matters for one repo, keep it as a local dogfooding note and route the resulting friction through the checked-in feedback loop.
