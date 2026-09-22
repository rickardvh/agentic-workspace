# Test Knowledge Inventory

Date: 2026-06-15

This inventory records behaviour knowledge currently embedded in executable tests
before the suite is rebuilt or reduced. It is a decision aid, not deletion
authorisation. Removing, merging, moving, or converting a test still requires an
agent to identify the behaviour claim, the owner that should carry it, and the
replacement evidence or historical record that preserves it.

## Migration Rules

- Preserve behaviour knowledge before reducing executable count.
- Keep scenario labels or regression names visible when they explain distinct
  history.
- Prefer replacement evidence owned by the behaviour surface, not by the old test
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
| `tests/test_model_cli_harness.py` | Adapter scoring, warning visibility, quality-signal preservation, raw-read diagnostics, and model-output shape handling. | Root harness tests with repeated setup and variant-specific assertions. | Which claims are product orchestration, and which belong in Verification or package-local scorer behaviour? | Scenario matrix for adapter/warning variants plus a retained historical note for incidents that no longer need executable coverage. |
| `tests/test_workspace_report_cli.py` | Report selector behaviour, section routing, active/current/external work summaries, and JSON/text output contracts. | Root CLI tests with selector aliases and repeated report setup. | Which report behaviours are stable contracts versus UI-level aliases? | Root black-box scenario matrix for representative selectors plus lower-level contract evidence for stable report payloads. |
| `tests/test_workspace_start_preflight_cli.py` | Startup preflight routing, recovery diagnostics, config authority, and safe next-action behaviour. | Root workflow tests around startup and preflight branches. | Which checks are high-risk orchestration semantics that should remain root-level? | Minimal root workflow matrix that preserves each distinct recovery branch label. |
| `tests/test_workspace_implement_cli.py` | Implement routing, planning interaction, deferred diagnostics, and changed-path proof hints. | Root implement command tests with several branch-shaped cases. | Which branches are user-visible workflow guarantees rather than implementation residue? | Scenario matrix by workflow branch and a compact historical record for retired diagnostics. |
| `tests/test_workspace_proof_cli.py` | Proof-route selection, missing evidence behaviour, checker orchestration, and closeout safety signals. | Root proof command tests and proof/checker orchestration cases. | Which proof semantics require executable integration coverage? | Retain representative root proof routes and move stable payload claims to package or Verification-owned evidence. |
| `tests/test_generated_command_package_proof_runner.py` | Generated-package proof runner gates, missing evidence diagnostics, and command-generation compatibility boundaries. | Root/package bridge tests with repeated completion-gate shapes. | Which generated behaviour has a named conformance owner? | Conformance cases for stable generated output plus a small bridge test for AW proof-runner orchestration. |
| `packages/planning/tests/test_summary.py` | Planning summary invariants, active plan state rendering, and operator-facing plan status text. | Package-local unit tests with scenario-specific state fixtures. | Which summaries are package-owned behaviour versus root report presentation? | Package scenario matrix retaining all state labels. |
| `packages/planning/tests/test_archive.py` | Archive lifecycle, planning residue cleanup, and migration of completed plan records. | Package-local archive tests with several filesystem state variants. | Which cases encode historical migration knowledge that should be documented after cleanup? | Package scenario matrix plus historical notes for one-time migration residue. |

## Migrated Historical Records

| Former Standalone Tests | Behaviour Claim | Failure Mode And Trigger | Current Proof Owner | Proposed Future Owner | Replacement Evidence | Why The Standalone Tests Were Retired |
| --- | --- | --- | --- | --- | --- | --- |
| `tests/test_workspace_report_cli.py` | Report and closeout rendering should expose selector, trust, caveat, projection, and JSON/text output semantics without depending on one historical fixture layout. | Report and closeout rendering accumulated many one-off regressions around selector aliases, trust packets, caveats, current/external work summaries, and projection shapes. | Root workspace report/summary/proof CLI tests, generated report conformance cases, maintainer surface checks, and this compact migration record. | Report payload contracts and focused root black-box scenario matrices for high-risk user-visible report behaviour. | `tests/test_workspace_summary_cli.py`, `tests/test_workspace_proof_cli.py`, `tests/test_generated_tool_conformance.py`, `make maintainer-surfaces`, and future report contract cases. | The legacy source file was deleted. New report behaviour should be proven by contract or focused scenario tests instead of reviving a broad regression cluster. |
| `tests/test_model_cli_harness.py` | Model-harness scoring should preserve adapter diagnostics, warning visibility, quality-signal handling, raw-read detection, and AW planning-boundary signals. | Dogfooding scorer and adapter incidents accumulated as many narrow fixture-specific checks. | Compact migration record in this table, model-harness code review, and future focused harness/scorer tests when that surface changes. | Harness-owned scorer/adapter tests or Verification evidence records for model-evaluation behaviour. | `test_model_cli_harness_scores_native_plan_bridge_failures` was retained before deletion as the named scenario matrix for native-plan bridge failures; this record preserves the retired broad-cluster knowledge. | The legacy source file was deleted so the evaluator harness cannot dominate ordinary suite count. Future harness work should add targeted owner-local evidence. |
| `tests/test_workspace_start_preflight_cli.py` | Startup and preflight should route recovery, config authority, safe next action, and takeover diagnostics correctly through the root workflow front door. | Startup and preflight routing behaviour accumulated many branch-shape regressions and mode-specific fixture variants. | Startup behaviour remains covered by root generated conformance, workspace CLI tests, implement/proof routing tests, and maintainer surface checks. | Workflow contract cases plus small root matrices for high-risk startup/preflight branches. | `tests/test_generated_tool_conformance.py` start/preflight cases, `tests/test_workspace_cli.py`, `tests/test_workspace_implement_cli.py`, and future startup/preflight scenario matrices. | The legacy source file was deleted; permanent proof should be narrower and owner-driven while preserving high-risk workflow semantics. |
| `packages/planning/tests/test_summary.py` | Planning summary should project active state, plan status, lane/decomposition state, and operator-facing guidance from package-owned state. | Planning summary tests accumulated many projection and historical-state variants. | Focused package-local planning tests, planning surface checks, generated planning conformance, and this migration record. | Planning package summary/report contracts and package-local scenario matrices. | `packages/planning/tests/test_promote.py`, `packages/planning/tests/test_lanes.py`, `packages/planning/tests/test_check_planning_surfaces.py`, generated planning report conformance, and `make check-planning`. | The legacy source file was deleted while package-local executable proof stays closer to current contracts. |
| `tests/test_contract_tooling.py` | Contract tooling should keep generated adapters, schemas, IR, artefact registries, generated package freshness, and target parity honest. | Contract tooling tests accumulated generated-adapter and schema-history assertions that overlapped static generated-package checks and conformance. | Generated package static proof, generated tool conformance, schema/reference checks, maintainer surface checks, and command-generation integration tests. | Generated package checker, operation conformance cases, schema/reference generation checks, and command-generation-owned tests for generic behaviour. | `uv run python src/tooling/check/check_generated_command_packages.py`, `tests/test_generated_tool_conformance.py`, `tests/test_generated_command_package_proof_runner.py`, `tests/test_command_generation_integration.py`, and maintainer surface checks. | Stable generated behaviour should move to conformance/checker ownership instead of one large ordinary regression file. |
| `tests/test_workspace_lifecycle_cli.py` | Lifecycle commands should preserve dry-run safety, strict preflight refusal, install/upgrade/uninstall routing, and module payload boundaries. | Lifecycle command behaviour accumulated broad workflow regressions across root and module install paths. | Package install tests, generated lifecycle conformance cases, root packaging smoke tests, and this migration record. | Lifecycle operation contracts, package-local install tests, and a small number of root smoke paths for front-door integration. | `packages/memory/tests/test_install.py`, `packages/planning/tests/test_install.py`, `tests/test_workspace_packaging.py`, lifecycle cases in `tests/test_generated_tool_conformance.py`, and `make sync-all`/package checks. | The legacy source file was deleted while the executable suite keeps only current high-value proof. |
| `test_model_cli_harness_scores_native_plan_without_bridge_as_semantic_failure`, `test_model_cli_harness_scores_native_plan_misplaced_workspace_artifact`, `test_model_cli_harness_scores_native_plan_workflow_mutation`, `test_model_cli_harness_scores_native_plan_freehand_root_plan` | Model-harness scoring should flag native or freehand planning artefacts that bypass canonical AW planning surfaces. | Agents sometimes used runtime-native plans or freehand planning artefacts instead of bridging through canonical AW planning surfaces. | Scenario matrix retained before legacy-file deletion and this migration record. | Harness-owned scorer tests or Verification evidence for model-output review. | `test_model_cli_harness_scores_native_plan_bridge_failures` kept all four labels as scenario rows and checked the same warning fragments before the broad harness file was retired. | The behaviour class is one model-harness scoring contract: native plan bridge failures. Separate executable tests only preserved incident shape. |
| `test_archive_execplan_apply_cleanup_removes_active_execplan_pointer`, `test_archive_execplan_apply_cleanup_removes_active_execplan_and_work_item_pointer`, `test_archive_execplan_apply_cleanup_removes_active_execplan_field_pointer`, `test_archive_execplan_apply_cleanup_removes_work_item_and_string_execplan_pointer` | Planning archive cleanup should remove all supported active execplan pointer representations after plan closeout. | Archive cleanup had to remove several live-state pointer shapes after plan closeout. | Planning package archive scenario matrix. | Planning package archive contract tests. | `test_archive_execplan_apply_cleanup_removes_active_execplan_pointer_variants` keeps each pointer-shape label and assertion in one package-local scenario matrix. | The permanent behaviour is cleanup across pointer representations; the individual tests were fixture variants. |
| `test_generated_operation_cli_input_proof_accepts_current_interfaces`, `test_generated_operation_cli_input_proof_rejects_missing_visible_option`, `test_generated_operation_cli_input_proof_allows_explicit_runtime_only_input` | Generated operation CLI input proof should accept current interfaces, reject missing visible options, and allow explicit runtime-only inputs. | Generated operation CLI input proof had separate regressions for accepted interfaces, missing visible options, and runtime-only input. | Generated command package proof-runner scenario matrix. | Generated operation conformance and proof-runner contract tests. | `test_generated_operation_cli_input_proof_scenarios` keeps all three cases in the generated proof-runner matrix. | The stable behaviour belongs to generated-command proof/conformance ownership, not three ordinary test functions. |
| Static generated-package proof rejection tests for read-only mutating targets, Python completion proof-surface drift, missing runtime projection inventory, shipped-source CLI backslide, non-full satisfied gates, and missing primitive conformance cases. | Static proof should reject generated-command and runtime-boundary drift before claiming full completion. | Static proof had separate error-path regressions for generated-command, runtime-boundary, and completion-gate drift. | Static generated package checker scenario matrix. | Generated package checker and operation conformance cases. | `test_static_generated_package_proof_rejects_static_surface_regressions` keeps the scenario labels and expected error fragments as a checker-internal matrix. | The retained proof owner is the static checker; standalone tests were repeated error-path fixtures. |

## Verification Dogfood Notes

The Verification `evidence_strategy` report should surface this file as a
candidate test-knowledge inventory source with `authority:
uninterpreted-source`. It should ask the agent what behaviour claim, owner, and
replacement evidence apply to each candidate. It must not treat these rows as a
policy engine, infer dispositions from prose, or mark tests safe to delete.

## Native host contraction (#3550, #3565)

The former Python host and generated runtime tests no longer establish the product
contract. Their durable failure classes now belong to these current owners:

| Failure class | Current executable evidence / disposition |
| --- | --- |
| Python/Node fallback or source/install divergence | `test_native_public_cli`, `test_native_npm_routes`, `test_language_facade`, and isolated wheel lifecycle in `test_workspace_packaging` |
| Lost Planning selection, provenance or material | `test_native_planning_create`, `test_native_planning_lifetime`, and native shared-core vectors |
| Proof laundering, wrong source identity or stale publication | `test_native_proof_producer`, `test_native_proof_scope`, `test_proof_publication`, `test_proof_receipt_owner`, and `test_source_request_dependencies` |
| Provider timeout, process cleanup, lineage or transcript privacy | Provider-mechanics cases in `test_native_transport`; assignment admission stays in the native assignment suites |
| Diagnostic source selection, raw-byte preservation or unsafe export | `test_native_maintainer_logging`, using the tooling-owned reader/exporter |
| Wrong distribution identity or release normalization | `test_package_identity`, `test_coordinated_release`, and release workflow guards against actual packed npm metadata |
| Python module entrypoint discovery and generated operation composition | Retired implementation mechanisms. Current extensibility is native independent-owner ingress; no compatibility promise is inferred for Python plugins. |
| Historical consequence tuples and Python final-response auto-resume | Retired host semantics. A tuple-shaped file or model transport exit cannot attest current native custody or task completion. Harness observations preserve that distinction. |

Old installer, duplicate generated-schema, generated fingerprint and Python/native
comparison fixtures are removed where the current owner cases above establish the
relevant contract. This disposition does not establish independent PR acceptance
or completion of the topology and bounded-residue work in #3551/#3552.

The #2435 fixed package/generator validation graph is retired as a current gate.
Its historical timing records are not rewritten as present-day evidence. Current
Makefile/CI boundary tests and compact-runner run/join/retry/conflict cases preserve
the reusable failure classes without requiring deleted package targets or an
old measured graph to match today's source tree.

The former Python startup variable-name marker ratchet and optional legacy
recurring-friction ledger checker are also retired. The former semantic host is
absent, and this repository has no current ledger at that old optional path.
Current route admission and Memory note validity remain native owner contracts;
these deletions do not assert that the legacy ledger format has native support.
Shared Git/instruction fixture builders used by native invocation and delegation
cases remain in `tests/native_instruction_support.py` without a Python interpreter.

## Native source topology (#3551, #3568)

Native module semantics retain their Rust tests under `src/core/src/modules/`.
Native public, installed artifact and schema consumers now read the canonical
core resources. Obsolete standalone package installers, their generated operation
contracts and conformance metadata are removed; their catalogue-residency and
historical cleanup-issue assertions establish no current native behavior. The
current native command catalogue, structured-source validation, release identity
and source/archive rebuild checks retain those present boundaries. Fixture
procedure delivery reads the current repository procedures rather than deleted
installer copies.

## Maintainer source topology (#3551, #3572)

Existing tooling, release, harness and hook cases now exercise their canonical
`src/tooling` sources. Fixture paths follow the current layout; historical run
records retain their original provenance. The supply-chain guard parses actual
Python calls so its own source does not trigger a textual `shell=True` match.
Isolated external-consumer tests clear source binary overrides as well as
`PYTHONPATH`, preserving the installed-artifact boundary.

The completion-cost schema estimator and its tests are retired: they described
removed Python operation schemas, not current native output. Native output and
contract budget evidence remains with the native owner suites. No replacement
historical cost taxonomy or duplicate relocation-only tests are introduced.

## Native proof retention (#3552, #3566)

The existing publication interruption and source-reconciliation suites remain the
producer owners. Their retained-history expectation now distinguishes current
referenced evidence from authenticated superseded groups. Native disposition
cases cover exact legacy index transfer, consumer drift across owner roots and
partial index/deletion recovery. Planning and Verification share only confined
bounded filesystem enumeration; the existing cross-platform link/junction case
continues to exercise that primitive.

The hundreds-cycle exercise is a bounded implementation experiment, not another
permanent ordinary-suite workload. Its file/byte plateau and elapsed time belong
in the PR evidence. These checks do not establish independent acceptance or
currentness of every historical source; actual migration and preserved consumers
are reported separately.

The migrated legacy failure `edfc5fcd80bdec7d` concerned the retired generated
Python command conformance check. Its boundary remains represented by current
native command and adapter contract checks; its failed historical execution is
not a current native failure or a reusable proof result.

## Planning history disposition (#3552, #3574)

Stable former-Planning inputs now live in `tests/fixtures/native_planning`, so
native owner migration can retire dogfood records without invalidating transport
or reconciliation fixtures. Historical Memory/decision tests use their admitted
scope; moving product paths does not silently rewrite source authority.

The existing terminal-lifetime case now includes Assignment judgment, actual
native proof, Planning closeout and proof expiry, with an unresolved-owner control
and a bounded tracked footprint. Closed-group, outside-consumer and read-only
nomination cases cover the new selection boundaries. Long cycle counts remain an
explicit proof run, rather than a permanent expensive default for every test run.
