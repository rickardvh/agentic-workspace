# Test Knowledge Inventory

Date: 2026-06-15

This inventory records behavior knowledge currently embedded in executable tests
before the suite is rebuilt or reduced. It is a decision aid, not deletion
authorization. Removing, merging, moving, or converting a test still requires an
agent to identify the behavior claim, the owner that should carry it, and the
replacement evidence or historical record that preserves it.

## Migration Rules

- Preserve behavior knowledge before reducing executable count.
- Keep scenario labels or regression names visible when they explain distinct
  history.
- Prefer replacement evidence owned by the behavior surface, not by the old test
  file layout.
- Treat this file as host-owned context for the agent; Verification may surface
  it but must not infer policy from its prose.

## Historical Regression Migration Path

When a test mainly preserves a past failure, migrate it through this record
before removing the standalone executable test:

1. Name the failure mode and trigger.
2. Name the replacement evidence owner: scenario matrix, conformance case,
   Verification evidence, Memory lesson, maintainer doc, or issue/PR record.
3. Keep any label needed to find the incident again.
4. State why the executable test is no longer the right permanent proof.
5. Record whether any high-risk workflow semantics remain executable elsewhere.

## Seed Clusters

| Cluster | Preserved Knowledge | Current Evidence Shape | Owner Questions | First Replacement Evidence |
| --- | --- | --- | --- | --- |
| `tests/test_model_cli_harness.py` | Adapter scoring, warning visibility, quality-signal preservation, raw-read diagnostics, and model-output shape handling. | Root harness tests with repeated setup and variant-specific assertions. | Which claims are product orchestration, and which belong in Verification or package-local scorer behavior? | Scenario matrix for adapter/warning variants plus a retained historical note for incidents that no longer need executable coverage. |
| `tests/test_workspace_report_cli.py` | Report selector behavior, section routing, active/current/external work summaries, and JSON/text output contracts. | Root CLI tests with selector aliases and repeated report setup. | Which report behaviors are stable contracts versus UI-level aliases? | Root black-box scenario matrix for representative selectors plus lower-level contract evidence for stable report payloads. |
| `tests/test_workspace_start_preflight_cli.py` | Startup preflight routing, recovery diagnostics, config authority, and safe next-action behavior. | Root workflow tests around startup and preflight branches. | Which checks are high-risk orchestration semantics that should remain root-level? | Minimal root workflow matrix that preserves each distinct recovery branch label. |
| `tests/test_workspace_implement_cli.py` | Implement routing, planning interaction, deferred diagnostics, and changed-path proof hints. | Root implement command tests with several branch-shaped cases. | Which branches are user-visible workflow guarantees rather than implementation residue? | Scenario matrix by workflow branch and a compact historical record for retired diagnostics. |
| `tests/test_workspace_proof_cli.py` | Proof-route selection, missing evidence behavior, checker orchestration, and closeout safety signals. | Root proof command tests and proof/checker orchestration cases. | Which proof semantics require executable integration coverage? | Retain representative root proof routes and move stable payload claims to package or Verification-owned evidence. |
| `tests/test_generated_command_package_proof_runner.py` | Generated-package proof runner gates, missing evidence diagnostics, and command-generation compatibility boundaries. | Root/package bridge tests with repeated completion-gate shapes. | Which generated behavior has a named conformance owner? | Conformance cases for stable generated output plus a small bridge test for AW proof-runner orchestration. |
| `packages/planning/tests/test_summary.py` | Planning summary invariants, active plan state rendering, and operator-facing plan status text. | Package-local unit tests with scenario-specific state fixtures. | Which summaries are package-owned behavior versus root report presentation? | Package scenario matrix retaining all state labels. |
| `packages/planning/tests/test_archive.py` | Archive lifecycle, planning residue cleanup, and migration of completed plan records. | Package-local archive tests with several filesystem state variants. | Which cases encode historical migration knowledge that should be documented after cleanup? | Package scenario matrix plus historical notes for one-time migration residue. |

## Migrated Historical Records

| Former Standalone Tests | Failure Mode And Trigger | Replacement Evidence | Why The Standalone Tests Were Retired |
| --- | --- | --- | --- |
| `test_model_cli_harness_scores_native_plan_without_bridge_as_semantic_failure`, `test_model_cli_harness_scores_native_plan_misplaced_workspace_artifact`, `test_model_cli_harness_scores_native_plan_workflow_mutation`, `test_model_cli_harness_scores_native_plan_freehand_root_plan` | Agents sometimes used runtime-native plans or freehand planning artifacts instead of bridging through canonical AW planning surfaces. | `test_model_cli_harness_scores_native_plan_bridge_failures` keeps all four labels as scenario rows and checks the same warning fragments. | The behavior class is one model-harness scoring contract: native plan bridge failures. Separate executable tests only preserved incident shape. |
| `test_archive_execplan_apply_cleanup_removes_active_execplan_pointer`, `test_archive_execplan_apply_cleanup_removes_active_execplan_and_work_item_pointer`, `test_archive_execplan_apply_cleanup_removes_active_execplan_field_pointer`, `test_archive_execplan_apply_cleanup_removes_work_item_and_string_execplan_pointer` | Archive cleanup had to remove several live-state pointer shapes after plan closeout. | `test_archive_execplan_apply_cleanup_removes_active_execplan_pointer_variants` keeps each pointer-shape label and assertion in one package-local scenario matrix. | The permanent behavior is cleanup across pointer representations; the individual tests were fixture variants. |
| `test_generated_operation_cli_input_proof_accepts_current_interfaces`, `test_generated_operation_cli_input_proof_rejects_missing_visible_option`, `test_generated_operation_cli_input_proof_allows_explicit_runtime_only_input` | Generated operation CLI input proof must accept current interfaces, reject missing visible options, and ignore explicit runtime-only inputs. | `test_generated_operation_cli_input_proof_scenarios` keeps all three cases in the generated proof-runner matrix. | The stable behavior belongs to generated-command proof/conformance ownership, not three ordinary test functions. |
| Static generated-package proof rejection tests for read-only mutating targets, Python completion proof-surface drift, missing runtime projection inventory, shipped-source CLI backslide, non-full satisfied gates, and missing primitive conformance cases. | Static proof must reject generated-command and runtime-boundary drift before claiming full completion. | `test_static_generated_package_proof_rejects_static_surface_regressions` keeps the scenario labels and expected error fragments as a checker-internal matrix. | The retained proof owner is the static checker; standalone tests were repeated error-path fixtures. |

## Verification Dogfood Notes

The Verification `evidence_strategy` report should surface this file as a
candidate test-knowledge inventory source with `authority:
uninterpreted-source`. It should ask the agent what behavior claim, owner, and
replacement evidence apply to each candidate. It must not treat these rows as a
policy engine, infer dispositions from prose, or mark tests safe to delete.
