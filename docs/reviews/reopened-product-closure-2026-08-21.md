# Reopened product-closure review

Date: 2026-08-21

Issues reviewed: #2606, #2607, #2613, and #2623.

## Decision

The reopened gaps are resolved as one subtractive composition change. Independent modules may publish optional, typed, revisioned facts, but those facts enter the existing instruction IR and operating decision. Scoped Markdown is the ordinary repository-authored instruction surface; workflow obligations remain only as a specialized compatibility surface for stage-bound lifecycle behavior.

This change adds no fact store, module-defined instruction operator, second decision compiler, or new authority owner. Command strings remain descriptive metadata and never become obligation identity.

## Acceptance mapping

| Concern | Evidence | Result |
| --- | --- | --- |
| Stable source-owned module facts (#2606, #2607) | `src/agentic_workspace/module_contract.py`, `src/agentic_workspace/contracts/schemas/module_capability.schema.json`, `tests/test_module_contract.py` | Facts have a stable id, declared type and type-checked value, module-owner identity, revision, and currentness. Facts are optional, ids fail closed on collision, and operation results may refresh only facts declared by the module contract. |
| Existing decision composition (#2606, #2623) | `src/agentic_workspace/instruction_clause_ir.py`, `src/agentic_workspace/operating_decision.py`, `tests/test_module_extension_scenario_matrix.py` | Current facts enter the existing instruction IR as source facts. Repository-owned clauses may reference them; stale, removed, and irrelevant facts contribute no active instruction. No module can define a new instruction clause or decision operator. |
| Out-of-tree extension proof (#2607) | `tests/fixtures/external_signals_module/src/external_signals/__init__.py`, `tests/test_module_contract.py`, `tools/model-cli-harness/external-agent-evaluation/module-extension-scenario-measurements.json` | The independent fixture publishes and refreshes a typed fact through the public contract while staying within the existing capability and completion-cost budgets. |
| Ordinary repository instruction authoring (#2613) | `.agentic-workspace/instructions/workspace-operating.md`, `.agentic-workspace/config.toml`, `src/agentic_workspace/contracts/workflow_definition_format.json`, workspace-default contract and schema tests | Generic startup and boundary guidance moved to scoped Markdown. Contract, schema, defaults, config, inventory, and generated references identify scoped Markdown as ordinary and workflow obligations as specialized compatibility only. |
| Specialized lifecycle compatibility (#2613, #2623) | `.agentic-workspace/config.toml`, `tests/test_workspace_defaults_cli.py` | The remaining obligations are stage-bound adapter refresh, post-proof commit, dogfooding closeout, and external-system intent refresh. Their ids remain stable metadata; embedded command strings do not define identity or widen authority. |

## Integrated subtraction check

- Reused the existing module contribution packet, instruction IR, operating-decision compiler, and module operation result path.
- Removed two generic workflow obligations instead of translating them into another obligation registry.
- Kept module facts optional so first-party modules without facts preserve their existing normalized contract.
- Kept fact applicability repository-owned and revision-aware; modules provide source data, not execution or claim authority.
- Kept the existing specialized obligation consumer only for lifecycle behavior that survives a stage transition.

## Dogfooding and operating-cost assessment

- `workflow_cost_found`: generic repository guidance previously required authors to choose between scoped Markdown and a stage-shaped obligation record.
- `architecture_cost_found`: module-owned observations had no typed route into the existing instruction decision, encouraging ad hoc projection or a parallel store.
- `needless_complexity_found`: two generic obligations and the public presentation of obligations as a primary component family were removed or demoted.
- `correct_by_design_assessment`: ordinary guidance now has one authoring surface; modules use one optional fact field and the existing operation result for refresh.
- `surfaces_added`: one optional module-contract field and one repo-scoped Markdown file; no command, store, operator, or workflow phase.
- `surfaces_removed_merged_or_demoted`: two generic obligations were removed and the remaining obligation family became specialized compatibility-only.
- `artifact_footprint_changed`: contract/schema/generated references and this closure review changed; Planning and Memory ownership did not.
- `shipped_default_footprint_changed`: unchanged for modules that omit facts; ordinary host guidance is smaller and more direct.
- `signals_consumed`: the reopened issue comments requiring typed fact lifecycle, out-of-tree proof, ordinary scoped Markdown, and integrated subtraction review.
- `signals_still_accumulating`: reconciliation reports unrelated historical execplans and one stale active projection; those existing Planning owners are outside this four-issue change.
- `durable_residue_consumed_or_routed`: stable rules live in the module contract, schemas, scoped guidance, docs, checks, and tests; no Memory promotion is needed.
- `human_steering_avoided_next_time`: defaults and generated references now prevent presenting workflow obligations as the ordinary authoring route.
- `validation_role`: focused tests, full workspace CLI tests, typechecking, schema checks, and generated-adapter conformance confirmed the constructed path.
- `follow_up_routed`: unrelated Planning cleanup remains visible through `agentic-workspace reconcile`; no new issue is required for this slice.
- `net_cost_direction`: lower.

Durable-residue result: validation passed; all four issue outcomes are implemented; intent is satisfied subject to review and merge; operating cost is reduced; durable residue is routed to docs, contracts, checks, and tests; post-promotion shape is `shrink`.

## Anti-overfitting and affordance review

- `user_agent_value`: repository authors have one obvious ordinary guidance surface, and module authors can contribute fresh typed observations without inventing an integration path.
- `surface_pressure`: the optional fact field replaces missing ad hoc composition while two generic obligation records and primary-family posture are removed.
- `portability_boundary`: fact identity, type, source revision, and currentness are generic; no repository vocabulary, executable, provider, or agent runtime is package policy.
- `human_intent_preserved`: applicability and effects stay in repo-owned scoped instructions and the existing authority-bearing instruction IR.
- `primary_next_action`: author ordinary guidance in `.agentic-workspace/instructions/*.md`; use an obligation only for a concrete stage-bound lifecycle consumer.
- `irrelevant_actions_demoted`: generic obligation promotion is removed from defaults and public contract wording; stale and irrelevant module facts do not produce active effects.
- `resolved_invocation`: generated references and checks use the repository's configured commands; public docs remain invocation-neutral.
- `weak_agent_path`: defaults and generated references name the ordinary surface directly.
- `strong_agent_escape_hatch`: experts can inspect the module contract, fact provenance, instruction projection, and compatibility obligation report.
- `context_burden_change`: lower; facts are relevance-filtered and optional, while ordinary guidance no longer competes with a second authoring model.
- `validation_role`: validation confirms the declared route and fails closed on owner, identity, type, currentness, or collision errors.

## Residue

No unresolved product gap remains within these four reopened issues. Future fact types or lifecycle consumers require concrete source-owner semantics and must compose through the same existing decision boundary rather than creating a parallel store or operator system. The dogfooding review found no session-specific improvement signal that belongs in Memory; unrelated stale Planning artifacts remain with their existing owner and were not activated or modified.
