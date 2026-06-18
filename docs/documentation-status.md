# Documentation Status

This page is a compact role and freshness index. It is not the package
overview, module map, or backlog. For shipped behavior, start with
[docs/index.md](index.md) and the `docs/package/` hierarchy.

Last reviewed: 2026-06-18.
Refresh route: update this page only when a public doc changes role, becomes a
current capability owner, or is freshly reviewed for currentness.

| Doc set | Role | Currentness | Owner note |
| --- | --- | --- | --- |
| [`README.md`](../README.md) | public entrypoint | current | stable install and positioning start point |
| [`docs/index.md`](index.md) | documentation owner map | current | canonical navigation for repeated concepts |
| [`docs/package/`](package/) | shipped package docs | current | root CLI, module selection, installed surfaces, knowledge routing, proof, and contracts |
| [`docs/maturity-model.md`](maturity-model.md) | maturity signal | current | support/adoption expectations, not a product map |
| [`docs/maintainer/`](maintainer/) | source-checkout maintainer workflow | current | validation, dogfooding, release, and test strategy |
| [`docs/reference/`](reference/) | generated contract reference | generated/current | regenerate from source schemata; do not hand-edit |
| [`docs/reviews/`](reviews/) | dated evidence | historical/current as dated | audit evidence, not first-contact product docs |
| `.agentic-workspace/planning/*/archive`, `.agentic-workspace/planning/closeout-evidence`, `.agentic-workspace/planning/reviews` | checked-in planning evidence | historical/current as dated | sampled 2026-06-18; retained because files carry dated review/proof or closeout context rather than live placeholders |

Status buckets:

- `current`: reviewed against the current package shape.
- `generated/current`: current when regenerated from the source contract.
- `historical/current as dated`: useful evidence whose date and purpose limit
  its authority.

Deletion rule: remove or compress stale status prose instead of expanding this
page. If a doc set needs detailed ownership, put that detail in its canonical
owner.
