# Workspace Reporting Contract

This page defines the compact shared schema used by `agentic-workspace report --format json`.

Use it when you want one derived inspection surface for combined workspace state instead of reading raw module files first.

## Purpose

- Keep workspace reporting compact, machine-readable, and comparable.
- Derive workspace and module summaries from canonical module-owned surfaces.
- Expose next-action guidance without turning reporting into a new source-of-truth store.
- Prefer one bounded question at a time when the report can answer it cheaply.
- Surface jumpstart discovery before any seed writes happen.

## Shared Schema

The report command emits a `schema` object with:

- `schema_version`
- `canonical_doc`
- `command`
- `shared_fields`
- `report_principles`

The surrounding report payload keeps these fields separate:

- `kind`
- `command`
- `target`
- `selected_modules`
- `installed_modules`
- `health`
- `findings`
- `next_action`
- `discovery`
- `registry`
- `config`
- `reports`

## Discovery Shape

The `discovery` object is the pre-write, pre-seed jumpstart layer.

It groups candidate surfaces into three buckets:

- `memory_candidates`
- `planning_candidates`
- `ambiguous`

Each candidate item carries:

- `surface`
- `reason`
- `confidence`
- `refs`

## Usage

Prefer:

```bash
agentic-workspace report --target ./repo --format json
```

Use the machine-readable report first when the question is:

- what modules are installed?
- what is the combined workspace health?
- what mixed-agent posture is in effect?
- what should happen next?
- what existing repo surfaces look like durable Memory or Planning seed candidates?
- what findings or warnings need attention?

## Guardrails

- Do not treat the report as a second state store.
- Do not require raw module files before the report when the report already answers the question.
- Keep findings, warnings, and next-action guidance separate.
- Keep module reports compact and derived.
- Keep concern-shaped subobjects narrow enough that one question does not force unrelated contract domains to load.
- Keep discovery read-only until a jumpstart promotion explicitly decides to seed.

## Relationship To Lazy Discovery

Use [`docs/compact-contract-profile.md`](docs/compact-contract-profile.md) for the selector-shaped answer envelope that should sit underneath the report surface when one answer is enough.

Use [`docs/lazy-discovery-measurements.md`](docs/lazy-discovery-measurements.md) when you want to check whether a narrow query is actually cheaper than a broad dump.

Use `agentic-workspace jumpstart --target ./repo --format json` when the report has already identified a bounded follow-through path and you want the public jumpstart surface rather than the broader combined report.
