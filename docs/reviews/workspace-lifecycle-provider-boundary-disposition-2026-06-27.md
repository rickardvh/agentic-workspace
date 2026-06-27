# Workspace Lifecycle and Provider Runtime Boundary Disposition

Date: 2026-06-27

Issues: #1656, #1649

## Purpose

This review closes the #1656 workspace lifecycle/provider slice with symbol-by-symbol dispositions for the four scoped runtime boundaries. It treats lifecycle mutation, Planning reconciliation, and provider refresh as different risks, rather than one generic adapter group.

Source command:

```powershell
uv run python scripts/check/check_generated_command_packages.py --python-completion-blockers --format json
```

Current checker baseline for this slice:

- 75 accepted runtime symbols.
- 19 workspace package runtime boundaries.
- The scoped provider symbol remains classified as `provider-integration`.
- The scoped lifecycle and reconcile symbols remain accepted hand-owned runtime boundaries; this PR changes semantic ownership for reconcile without claiming full generated minimization.

## Disposition Table

| Symbol | Current risk | Disposition | Semantic owner after this PR | CG/control shape needed before more migration | Proof/update |
| --- | --- | --- | --- | --- | --- |
| `_run_init_lifecycle_adapter` | lifecycle mutation orchestration | Retain as AW-owned runtime adapter. It already projects `lifecycle_plan`, but target/config/module selection and init/adopt/write policy are still coupled to managed-surface safety. | AW lifecycle runtime in `workspace_runtime_primitives.py` / `workspace_runtime_core.py`. | `transaction.envelope` with explicit plan/apply object, dry-run equivalence proof, managed-surface safety hooks, conflict policy hooks, and provenance hooks. | Keep conformance lifecycle dry-run cases plus generated package checks. |
| `_run_lifecycle_mutation_adapter` | lifecycle mutation orchestration | Retain as AW-owned runtime adapter. The repair path and lifecycle command application still decide what mutation is allowed. | AW lifecycle runtime in `workspace_runtime_primitives.py` / `workspace_runtime_core.py`. | Same `transaction.envelope`; no generic move until safe dry-run/apply/provenance semantics are contract-backed. | Keep lifecycle destructive-refusal and dry-run conformance plus workspace tests. |
| `_run_reconcile_report_adapter` | Planning reconciliation payload plus root CLI routing | Moved the implementation to `workspace_runtime_planning.py`; `workspace_runtime_core.py` now forwards lazily and `workspace_runtime_primitives.py` re-exports for generated/private compatibility. | Planning runtime owner owns reconciliation payload loading, safe-prune semantics, and text rendering handoff; workspace generated bindings still import the compatibility symbol until a Planning facade is introduced. | Generic report routing can move later after section/view routing is contract-backed. Planning reconciliation semantics stay Planning-owned. | Added owner-routing regression and retained reconcile JSON/safe-prune tests. |
| `_run_external_intent_refresh_github_adapter` | provider integration | Retain as provider-owned runtime adapter. Repo resolution, `gh` invocation, issue filtering, evidence normalization/write semantics, and failure trust remain host-owned. | AW provider integration runtime in `workspace_runtime_primitives.py` / `workspace_runtime_core.py`. | Host-neutral `provider.envelope` with provider fixtures, uninterpreted raw-response capture, host-owned evidence schema, and failure-trust hooks. | Keep external-intent refresh tests and runtime-symbol working-set classification. |

## Implementation Decision

The only safe code movement in this slice is the reconcile owner split. The existing `planning.reconcile.load` primitive proves the reconciliation payload is Planning-owned, and the root `reconcile` command already exposes provider-agnostic Planning state. Moving the adapter implementation to `workspace_runtime_planning.py` names that ownership without hiding safe-prune policy in generic code.

The lifecycle adapters are deliberately not moved behind a generic transaction primitive in this PR. A transaction primitive without explicit dry-run equivalence, plan/apply object shape, and provenance hooks would make mutation policy harder to review.

The GitHub external-intent refresh adapter is not a lifecycle adapter. It remains a provider integration boundary until command-generation or shared runtime support has a host-neutral provider fixture and envelope.

## Residual Follow-Up

- Add a host-neutral `transaction.envelope` candidate in command-generation before attempting lifecycle mutation migration.
- Add a host-neutral `provider.envelope` fixture before attempting provider refresh migration.
- Consider a generated Planning runtime facade for root `reconcile` after generated bindings can name Planning owner modules directly without losing compatibility.

## Proof

Required checks for this artifact:

```powershell
uv run pytest tests/test_workspace_cli.py::test_reconcile_report_adapter_routes_through_planning_owner tests/test_workspace_summary_cli.py::test_workspace_reconcile_json_exposes_provider_agnostic_planning_state tests/test_workspace_summary_cli.py::test_workspace_reconcile_apply_safe_prune_removes_exact_closed_items -q
uv run python scripts/check/check_generated_command_packages.py --python-completion-blockers --format json
uv run python scripts/check/check_contract_tooling_surfaces.py --quiet-success
```
