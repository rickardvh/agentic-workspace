# Documentation Status

This page classifies documentation roles. It is **not** a freshness authority for rapidly changing commands, module metadata, installed footprints, or runtime contracts.

For current product meaning, start with [the documentation index](index.md). For exact machine contract facts, use the source contract/runtime output or a generated reference that identifies that authority.

Manual role review: 2026-08-20.

A manual review date means only that the role classification below was inspected on that date. It does not prove that every fact inside the document still matches the current release or contract revision.

| Doc set | Role | Trust/currentness rule |
| --- | --- | --- |
| [`README.md`](../README.md) | public entrypoint | stable product/adoption summary; should avoid exhaustive contract facts |
| [`docs/index.md`](index.md) | documentation owner map | canonical navigation and abstraction ladder |
| [`docs/package/`](package/) | conceptual package documentation plus some transitional design material | use conceptual owners for meaning; treat issue-linked/test-inventory pages as maintainer/design evidence until moved, merged, or deleted |
| [`docs/architecture.md`](architecture.md) | conceptual architecture | kernel/module/repo/adapter ownership model |
| [`docs/extension-boundary.md`](extension-boundary.md) | current extensibility/support-boundary explanation | distinguishes core extensibility direction from support-bearing public compatibility |
| [`docs/maturity-model.md`](maturity-model.md) | maturity terminology | must agree with public package metadata or explicitly explain any capability-vs-distribution distinction |
| [`docs/maintainer/`](maintainer/) | source-checkout maintainer workflow | repo-specific validation, dogfooding, generation, release, and maintenance procedure |
| [`docs/reference/`](reference/) | generated contract reference | trustworthy only for the source/contract revision from which it was generated; schema-shape pages are not automatically current-value catalogues |
| [`docs/reviews/`](reviews/) | dated evidence | historical evidence; date and purpose limit authority |
| `.agentic-workspace/planning/` reviews/archive/closeout evidence | Planning evidence/state | current only according to its owning Planning lifecycle; historical records are not public product doctrine |

## Currentness rules

Use these buckets instead of a blanket `current` label:

- **conceptual/current** — stable meaning reviewed against the current product model; exact changing values are linked rather than copied.
- **generated/source-bound** — derived from a named source contract or schema and current only for that source revision/digest.
- **runtime-current** — returned from the configured admitted runtime for the target repository.
- **historical/as-dated** — useful evidence whose date and purpose bound its authority.
- **transitional** — retained temporarily while a newer owner is being established; must not compete as equal current authority.

## Drift policy

Do not make this page "fresh" by changing only the date.

When a document claims exact rapidly changing facts, prefer one of:

1. derive the fact from machine-readable authority;
2. link to a generated/source-bound reference;
3. link to a runtime query;
4. add a mechanical parity/drift check;
5. remove the duplicated exact claim from conceptual prose.

If none of those is justified, the page should state that its content is explanatory rather than exact current contract authority.

The documentation cleanup should reduce this status surface over time rather than expanding it into another inventory.