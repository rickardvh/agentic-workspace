# Lazy Discovery Measurements

## Purpose

This page defines the cheap measurement framework for lazy discovery.

Use it when a compact contract change claims to reduce reading or token cost and needs proof stronger than "the schema looks cleaner."

## Rule

Measure the preferred compact/query-first route for one workflow question against the broader plausible fallback route.

Prefer cheap reproducible proxies over invented exactness.

## Current Framework

Use:

```bash
uv run python scripts/check/measure_lazy_discovery.py --target .
```

The current framework measures:

- artifacts loaded before the first safe action
- file reads avoided when a compact route replaces a prose-first path
- UTF-8 bytes returned
- character count returned
- a simple token proxy: `ceil(character_count / 4)`

It compares:

- the preferred compact command or selector for a question
- the broader fallback route a contributor would otherwise use

Fallback routes may be:

- a broader machine-readable surface
- a file bundle when the real fallback path is prose-first or file-first rather than query-first

Current covered questions:

- startup and routing contract lookup
- active planning inspection and restart handoff
- proof-lane selection
- ownership lookup
- setup and jumpstart inspection

## Interpretation Rule

- Prefer cases where the compact route replaces multiple file reads or a broad dump with one bounded answer.
- Count query-first wins in artifact and file-read reduction first; byte and token proxies are secondary confirmation.
- Keep correction pressure, curation mistakes, and restart quality as qualitative notes in the audit artifact unless a cheap structured proxy becomes trustworthy later.

## Boundaries

- This is a retrieval-size proxy, not exact model token accounting.
- It is intentionally small and static; it is not a benchmark runner or telemetry lane.
- Do not turn this into runtime telemetry or generic analytics.

## Relationship To Other Docs

- Use [`.agentic-workspace/docs/compact-contract-profile.md`](.agentic-workspace/docs/compact-contract-profile.md) for the selector and compact-answer contract itself.
- Use [`.agentic-workspace/docs/reporting-contract.md`](.agentic-workspace/docs/reporting-contract.md) and [`docs/default-path-contract.md`](docs/default-path-contract.md) when choosing the preferred compact route for a workflow question.
- Use [`.agentic-workspace/memory/repo/runbooks/dogfooding-feedback-routing.md`](.agentic-workspace/memory/repo/runbooks/dogfooding-feedback-routing.md) when you want to classify internal friction, repeated surface pull, or outsider-legibility concerns during ordinary work.
- Use [`.agentic-workspace/memory/repo/runbooks/dogfooding-usage-ledger.md`](.agentic-workspace/memory/repo/runbooks/dogfooding-usage-ledger.md) when you want to record whether the measured route was actually chosen during ordinary work.
- Use `.agentic-workspace/planning/reviews/README.md` ordinary-use-pull mode when the ledger shows repeated low-pull patterns and you need to decide whether to merge, demote, or retire a surface.
- Use [`docs/design-principles.md`](docs/design-principles.md) for the "proof should beat preference" rule that motivates this measurement.
