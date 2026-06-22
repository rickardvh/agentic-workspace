# Runtime Boundary Decomposition Audit

Date: 2026-06-20

Follow-up issue: [#1649](https://github.com/rickardvh/agentic-workspace/issues/1649)

## Purpose

This review records a first-pass audit of the accepted hand-owned runtime boundaries reported by the generated-command package checker. The goal is to separate truly package-specific semantic kernels from behavior that should eventually become JSON Schema, declarative package-owned policy, or generic command-generation control/dataflow operations.

The audit does not claim runtime minimization is complete. It is a migration planning artifact.

## Source

Command:

```powershell
uv run python scripts/check/check_generated_command_packages.py --python-completion-blockers --format json
```

Current inventory:

- 85 accepted runtime boundary entries.
- 73 unique source symbols.
- 0 generic deterministic runtime-debt symbols in the current checker report.
- 0 ordinary source-operation usages of command-generation transitional primitive IDs.

The 85 count is a boundary-entry count, not a file count or unique-symbol count.

## Classification Model

Each accepted boundary entry should be classified into one of these buckets:

- `schema-only`: behavior should be expressible as JSON Schema plus declared payload/policy inputs.
- `declarative-policy`: behavior should be package-owned policy, routing, lifecycle, safety, freshness, view, or transition data consumed by generic machinery.
- `generic-cg-control`: behavior should move toward generic command-generation pseudocode operations.
- `mixed-policy-plus-kernel`: behavior contains decomposable generic/policy scaffolding plus a package-owned semantic kernel.
- `irreducible-domain-kernel`: behavior should remain package-owned code for now.
- `provider-adapter`: behavior integrates with an external provider or subprocess boundary.

## First-Pass Counts

| Classification | Entry count | Unique symbols | Interpretation |
| --- | ---: | ---: | --- |
| `schema-only` | 2 | 1 | Should be expressible as JSON Schema plus declared payload/policy inputs. |
| `declarative-policy` | 20 | 18 | Likely better as policy/view/routing/transition data plus generic loaders/projectors. |
| `generic-cg-control` | 7 | 7 | Should move toward generic CG pseudocode operations. |
| `mixed-policy-plus-kernel` | 48 | 40 | Has decomposable generic/policy scaffolding plus a package-owned semantic kernel. |
| `irreducible-domain-kernel` | 7 | 6 | Should probably remain package-owned code for now. |
| `provider-adapter` | 1 | 1 | Provider integration boundary; not a CG generic semantics target yet. |

Initial conclusion: the reducible surface is much larger than the truly irreducible domain-kernel surface. Most entries should be decomposed before deciding they must remain hand-owned runtime code.

## Guardrails

- Do not move AW product semantics into command-generation source.
- Do not add arbitrary expression evaluation, embedded Python/JS, or unbounded loops to command generation.
- Keep generic CG operations schema-backed, implementation-independent, and pseudocode-like.
- Keep Memory, Planning, Verification, workspace startup/proof, and provider semantics package-owned unless they are expressed as package-owned declarative policy consumed by generic execution machinery.
- Do not claim runtime minimization merely by moving code-shaped logic into generated files.
- Do not count schema/policy migration as complete unless generated operations actually consume the new source of truth.

## Candidate Generic CG Operation Families

These operation families look useful without encoding AW-specific semantics in command-generation:

- `control.if` and `control.switch` over declared booleans/enums only.
- `collection.map`, `collection.filter`, `collection.group_by`, `collection.sort_by`, and `collection.dedupe` over declared object fields.
- `record.project`, `record.merge`, and `record.set_default`.
- `template.render` or `view.render` from named templates or view specs.
- `diagnostic.emit` and `result.classify` for structured status records.
- `filesystem.plan_changes` plus guarded `filesystem.apply_plan`.
- `state.transition` from package-owned transition tables.
- `command.delegate` for front-door/module delegation envelopes.

## First-Pass Symbol Table

| Classification | Current class | Symbol | Audit reason |
| --- | --- | --- | --- |
| declarative-policy | package-specific-judgment | `repo_memory_bootstrap.runtime_primitives._load_memory_bootstrap_doctor` | Doctor checks should be schema/policy records plus generic projection. |
| declarative-policy | package-specific-judgment | `repo_memory_bootstrap.runtime_primitives._load_memory_current` | Current-note view can be declarative view policy. |
| declarative-policy | package-specific-judgment | `repo_memory_bootstrap.runtime_primitives._load_memory_prompt` | Prompt rendering should be template/policy driven. |
| declarative-policy | package-specific-judgment | `repo_memory_bootstrap.runtime_primitives._load_memory_report` | Report assembly can be schema/view driven. |
| declarative-policy | package-specific-judgment | `repo_planning_bootstrap.installer.collect_status` | Status collection can be declared file/state projection. |
| declarative-policy | package-specific-judgment | `repo_planning_bootstrap.installer.doctor_bootstrap` | Doctor checks can be declared checks plus generic projection. |
| declarative-policy | package-specific-judgment | `repo_planning_bootstrap.installer.planning_report` | Report assembly can be schema/view driven. |
| declarative-policy | package-specific-judgment | `repo_planning_bootstrap.installer.planning_report_tiny` | Tiny report projection can be view policy. |
| declarative-policy | package-specific-judgment | `repo_planning_bootstrap.runtime_projection.load_planning_summary_operation` | Summary projection can be view policy. |
| declarative-policy | package-specific-judgment | `repo_planning_bootstrap.runtime_projection.render_planning_prompt_operation` | Prompt rendering should be template/policy driven. |
| declarative-policy | package-specific-judgment | `agentic_workspace.workspace_runtime_primitives._load_workspace_operation_config` | Config layering can be schema/policy driven with generic loading. |
| declarative-policy | package-specific-judgment | `agentic_workspace.workspace_runtime_primitives._load_workspace_operation_system_intent_config` | Source hints and required fields can be policy data. |
| declarative-policy | package-specific-judgment | `agentic_workspace.workspace_runtime_primitives._render_workspace_operation_prompt` | Template/render selection should be contract/policy driven. |
| declarative-policy | package-specific-judgment | `agentic_workspace.workspace_runtime_primitives._resolve_workspace_operation_selection` | Module/selection defaults can be declarative enum policy. |
| declarative-policy | live-workspace-inspection | `agentic_workspace.workspace_runtime_primitives._run_lifecycle_report_adapter` | Mostly status/readiness projection from declared module state. |
| declarative-policy | live-workspace-inspection | `agentic_workspace.workspace_runtime_primitives._run_modules_report_adapter` | Module inspection can become declared roots/signals plus generic projection. |
| declarative-policy | live-workspace-inspection | `agentic_workspace.workspace_runtime_primitives._run_report_combined_adapter` | Combined report assembly can be declarative section routing. |
| declarative-policy | package-specific-judgment | `agentic_workspace.workspace_runtime_primitives._run_summary_report_adapter` | Summary projection can be section/schema driven. |
| generic-cg-control | package-specific-judgment | `repo_memory_bootstrap.runtime_primitives._emit_memory_operation_output` | Output projection should be generic. |
| generic-cg-control | package-specific-judgment | `repo_planning_bootstrap.runtime_projection.emit_planning_operation_output` | Output projection should be generic. |
| generic-cg-control | package-specific-judgment | `agentic_workspace.workspace_runtime_primitives._append_workspace_operation_delegation_outcome` | Appends a structured record from schema-backed inputs. |
| generic-cg-control | package-specific-judgment | `agentic_workspace.workspace_runtime_primitives._emit_workspace_operation_output` | Output projection/field selection should be generic emit/render policy. |
| generic-cg-control | front-door-dispatch | `agentic_workspace.workspace_runtime_primitives._run_memory_front_door_adapter` | Front-door delegation envelope can be generic. |
| generic-cg-control | front-door-dispatch | `agentic_workspace.workspace_runtime_primitives._run_planning_front_door_adapter` | Front-door delegation envelope can be generic. |
| generic-cg-control | package-specific-judgment | `agentic_workspace.workspace_runtime_primitives._select_workspace_operation_fields` | Retired by the #1655/#1659 implementation: `config.report` now uses CG `payload.project` for exact selector projection, and the AW symbol is removed. |
| irreducible-domain-kernel | package-specific-judgment | `repo_memory_bootstrap.installer.promotion_report` | Memory promotion/remediation judgment. |
| irreducible-domain-kernel | package-specific-judgment | `repo_memory_bootstrap.installer.review_routes` | Memory route quality judgment. |
| irreducible-domain-kernel | package-specific-judgment | `repo_memory_bootstrap.installer.route_memory` | Memory note routing/relevance semantics. |
| irreducible-domain-kernel | package-specific-judgment | `repo_memory_bootstrap.installer.suggest_memory_note_capture` | Memory capture versus route-elsewhere judgment. |
| irreducible-domain-kernel | package-specific-judgment | `repo_memory_bootstrap.runtime_search.search_memory` | Search/ranking may remain code until a generic index boundary exists. |
| irreducible-domain-kernel | package-specific-judgment | `repo_planning_bootstrap.installer.planning_handoff` | Handoff semantics and sufficiency judgment. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_memory_bootstrap.installer.adopt_bootstrap` | Generic lifecycle mutation plus memory adoption policy. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_memory_bootstrap.installer.cleanup_bootstrap_workspace` | Generic cleanup plan plus memory-owned obsolete/current rules. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_memory_bootstrap.installer.create_memory_note` | Generic write scaffold plus memory note policy. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_memory_bootstrap.installer.install_bootstrap` | Generic payload install plus memory safety/provenance policy. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_memory_bootstrap.installer.migrate_layout` | Generic migration plan plus memory layout policy. |
| mixed-policy-plus-kernel | package-specific-judgment | `repo_memory_bootstrap.installer.sync_memory` | Generic sync/write plus memory layout/freshness policy. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_memory_bootstrap.installer.uninstall_bootstrap` | Generic lifecycle mutation plus memory safety policy. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_memory_bootstrap.installer.upgrade_bootstrap` | Generic lifecycle mutation plus memory upgrade policy. |
| mixed-policy-plus-kernel | package-specific-judgment | `repo_memory_bootstrap.runtime_primitives._load_memory_route_report` | Route-report has reusable projection plus memory route semantics. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_planning_bootstrap.installer.adopt_bootstrap` | Generic lifecycle mutation plus planning adoption policy. |
| mixed-policy-plus-kernel | package-specific-judgment | `repo_planning_bootstrap.installer.close_planning_item` | State transition mechanics declarative; closeout semantics remain planning-owned. |
| mixed-policy-plus-kernel | package-specific-judgment | `repo_planning_bootstrap.installer.create_review_record` | Generic record creation plus planning review policy. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_planning_bootstrap.installer.install_bootstrap` | Generic payload install plus planning safety/provenance policy. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_planning_bootstrap.installer.uninstall_bootstrap` | Generic lifecycle mutation plus planning safety policy. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_planning_bootstrap.installer.upgrade_bootstrap` | Generic lifecycle mutation plus planning upgrade policy. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_planning_bootstrap.runtime_projection.apply_planning_archive_plan_operation` | Generic state mutation plus planning archive semantics. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_planning_bootstrap.runtime_projection.apply_planning_closeout_operation` | Generic state mutation plus closeout semantics. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_planning_bootstrap.runtime_projection.apply_planning_delegation_decision_operation` | Generic append/update plus delegation semantics. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_planning_bootstrap.runtime_projection.apply_planning_intake_artifact_operation` | Generic file/record mutation plus intake semantics. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_planning_bootstrap.runtime_projection.apply_planning_lane_activate_operation` | Generic state transition plus lane activation policy. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_planning_bootstrap.runtime_projection.apply_planning_lane_archive_operation` | Generic state transition plus lane archive policy. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_planning_bootstrap.runtime_projection.apply_planning_lane_close_operation` | Generic state transition plus lane close policy. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_planning_bootstrap.runtime_projection.apply_planning_lane_create_operation` | Generic record creation plus lane policy. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_planning_bootstrap.runtime_projection.apply_planning_lane_promote_operation` | Generic state transition plus lane promotion policy. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_planning_bootstrap.runtime_projection.apply_planning_new_plan_operation` | Generic record creation plus plan policy. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_planning_bootstrap.runtime_projection.apply_planning_promote_to_plan_operation` | Generic state transition plus promotion policy. |
| mixed-policy-plus-kernel | mutation-orchestration | `repo_planning_bootstrap.runtime_projection.load_planning_reconcile_operation` | Generic projection plus planning reconcile semantics. |
| mixed-policy-plus-kernel | package-specific-judgment | `repo_verification_bootstrap.runtime_primitives.verification_report_payload` | Schema/report assembly plus verification evidence semantics. |
| mixed-policy-plus-kernel | package-specific-judgment | `agentic_workspace.workspace_runtime_primitives._read_or_create_workspace_operation_system_intent_mirror` | Generic read-or-create shell plus AW system-intent defaults. |
| mixed-policy-plus-kernel | package-specific-judgment | `agentic_workspace.workspace_runtime_primitives._refresh_workspace_operation_system_intent_metadata` | Generic metadata refresh plus AW source semantics. |
| mixed-policy-plus-kernel | package-specific-judgment | `agentic_workspace.workspace_runtime_primitives._run_implement_context_adapter` | Agent context semantics remain AW-owned; projection mechanics generic. |
| mixed-policy-plus-kernel | mutation-orchestration | `agentic_workspace.workspace_runtime_primitives._run_init_lifecycle_adapter` | Generic lifecycle plan/apply plus AW module safety policy. |
| mixed-policy-plus-kernel | mutation-orchestration | `agentic_workspace.workspace_runtime_primitives._run_lifecycle_mutation_adapter` | Mutation safety/provenance kernel remains AW-owned. |
| mixed-policy-plus-kernel | package-specific-judgment | `agentic_workspace.workspace_runtime_primitives._run_ownership_report_adapter` | Ownership semantics AW-owned; projection generic. |
| mixed-policy-plus-kernel | package-specific-judgment | `agentic_workspace.workspace_runtime_primitives._run_preflight_report_adapter` | Preflight policy semantics remain AW-owned; checks/projection generic. |
| mixed-policy-plus-kernel | package-specific-judgment | `agentic_workspace.workspace_runtime_primitives._run_proof_report_adapter` | Proof selection semantics remain AW-owned; report mechanics generic. |
| mixed-policy-plus-kernel | mutation-orchestration | `agentic_workspace.workspace_runtime_primitives._run_reconcile_report_adapter` | Reconciliation/mutation policy remains AW-owned. |
| mixed-policy-plus-kernel | live-workspace-inspection | `agentic_workspace.workspace_runtime_primitives._run_setup_guidance_adapter` | Setup guidance semantics remain AW-owned; selection/projection generic. |
| mixed-policy-plus-kernel | package-specific-judgment | `agentic_workspace.workspace_runtime_primitives._run_skills_report_adapter` | Skill ranking semantics AW-owned; catalog projection generic. |
| mixed-policy-plus-kernel | package-specific-judgment | `agentic_workspace.workspace_runtime_primitives._run_start_context_adapter` | Startup next-action semantics remain AW-owned. |
| provider-adapter | provider-integration | `agentic_workspace.workspace_runtime_primitives._run_external_intent_refresh_github_adapter` | GitHub/gh integration is provider owned. |
| schema-only | package-specific-judgment | `repo_planning_bootstrap.installer.verify_payload` | Payload verification should be schema plus declared payload policy. |

## Suggested First Implementation Slices

1. Add or generate an auditable classification report for all accepted hand-owned runtime boundaries.
2. Move the easiest `generic-cg-control` items first: field selection/output projection and front-door delegation envelope.
3. Move one `schema-only` or `declarative-policy` item next, such as Planning payload verification or report/view projection, to prove the schema/policy path.
4. Split one `mixed-policy-plus-kernel` lifecycle operation so generic plan/apply mechanics move to CG while package safety policy remains explicit.

## Review Notes

This artifact intentionally keeps package semantics in AW/package-owned surfaces. Command generation may gain generic control/dataflow operations, but those operations should stay strictly generic. The migration should reduce duplicated executable implementations without moving domain judgment into CG or replacing semantic review with mechanical category labels.
