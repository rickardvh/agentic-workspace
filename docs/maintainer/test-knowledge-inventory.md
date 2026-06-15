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

## Verification Dogfood Notes

The Verification `evidence_strategy` report should surface this file as a
candidate test-knowledge inventory source with `authority:
uninterpreted-source`. It should ask the agent what behavior claim, owner, and
replacement evidence apply to each candidate. It must not treat these rows as a
policy engine, infer dispositions from prose, or mark tests safe to delete.
