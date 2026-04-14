# Workspace Reporting Contract

This page defines the compact shared schema used by `agentic-workspace report --format json`.

Use it when you want one derived inspection surface for combined workspace state instead of reading raw module files first.

## Purpose

- Keep workspace reporting compact, machine-readable, and comparable.
- Derive workspace and module summaries from canonical module-owned surfaces.
- Expose next-action guidance without turning reporting into a new source-of-truth store.

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
- `registry`
- `config`
- `reports`

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
- what findings or warnings need attention?

## Guardrails

- Do not treat the report as a second state store.
- Do not require raw module files before the report when the report already answers the question.
- Keep findings, warnings, and next-action guidance separate.
- Keep module reports compact and derived.
