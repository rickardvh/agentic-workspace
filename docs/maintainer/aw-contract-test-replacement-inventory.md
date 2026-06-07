# AW Contract Test Replacement Inventory

This inventory is the #1374 AW-side implementation record for replacing generated-command behavior assertions with contract-owned conformance cases.

## Closure Decision

#1374 is complete for the AW repository when this inventory is current: stable generated-command success behavior has a contract-owned conformance owner, duplicate ordinary success-path regressions have been merged or deleted, and the remaining ordinary tests are explicitly retained because they cover runner internals, adapter error classification, proof/checker orchestration, schema/generator mechanics, high-risk workflow semantics, or command-generation-owned primitive behavior.

This inventory does not close `rickardvh/command-generation#9`; portable primitive and command-generation package test replacement remains owned by that repository.

The June 2026 audit found additional stable text-output tests that could not be migrated without weakening coverage because the shared `command-generation` conformance runner only compared JSON fields. `rickardvh/command-generation#10` adds required stdout substring checks, and this AW branch pins that dependency revision so the migrated text cases run through the same generated Python and TypeScript conformance proof as JSON cases.

## Converted Or Merged

| Old ordinary test | Replacement contract id and case id | Target adapters | Proof command | Remaining ordinary coverage |
| --- | --- | --- | --- | --- |
| `tests/test_workspace_cli_blackbox.py::test_blackbox_root_generated_command_executes_through_console_script` | `modules.report.process` / `minimal-repo` | generated workspace Python and TypeScript command packages | `uv run python scripts/check/check_generated_command_packages.py --python-conformance`; `uv run python scripts/check/check_generated_command_packages.py --conformance --require-node` | Deleted from ordinary black-box tests; `tests/test_workspace_cli_blackbox.py` keeps usage-error and recovery-message adapter mechanics. |
| `tests/test_workspace_cli_blackbox.py::test_blackbox_root_generated_command_executes_primitive_ir_through_console_script` | `defaults.root-cli-authority.process` / `minimal-repo` | generated workspace Python and TypeScript command packages | `uv run python scripts/check/check_generated_command_packages.py --python-conformance`; `uv run python scripts/check/check_generated_command_packages.py --conformance --require-node` | Deleted from ordinary black-box tests; `tests/test_workspace_cli_blackbox.py` keeps usage-error and recovery-message adapter mechanics. |
| `tests/test_workspace_defaults_cli.py::test_defaults_tiny_text_uses_generated_output` | `defaults.tiny-text.process` / `minimal-repo` | generated workspace Python and TypeScript command packages | `uv run python scripts/check/check_generated_command_packages.py --python-conformance`; `uv run python scripts/check/check_generated_command_packages.py --conformance --require-node` | Deleted from ordinary defaults tests; the text substrings are now contract-owned via `stdout.contains`. |
| `tests/test_workspace_defaults_cli.py::test_defaults_selected_section_text_uses_generated_output` | `defaults.selected-text.process` / `minimal-repo` | generated workspace Python and TypeScript command packages | `uv run python scripts/check/check_generated_command_packages.py --python-conformance`; `uv run python scripts/check/check_generated_command_packages.py --conformance --require-node` | Deleted from ordinary defaults tests; the selected-output text substrings are now contract-owned via `stdout.contains`. |
| `tests/test_workspace_config_cli.py::test_config_selected_text_uses_generated_output` | `config.selected-text.process` / `agent-efficiency-config` | generated workspace Python and TypeScript command packages | `uv run python scripts/check/check_generated_command_packages.py --python-conformance`; `uv run python scripts/check/check_generated_command_packages.py --conformance --require-node` | Deleted from ordinary config tests; the selected-output text substrings are now contract-owned via `stdout.contains`. |
| `tests/test_workspace_config_cli.py::test_note_delegation_outcome_text_uses_generated_output` | `delegation-outcome.append-text.process` / `minimal-repo` | generated workspace Python and TypeScript command packages | `uv run python scripts/check/check_generated_command_packages.py --python-conformance`; `uv run python scripts/check/check_generated_command_packages.py --conformance --require-node` | Deleted from ordinary config tests; the mutation output text substrings and allowed-write boundary are now contract-owned. |

## Deleted Ordinary Regressions

| Old ordinary test | Delete reason | Equivalent or stronger coverage |
| --- | --- | --- |
| `tests/test_workspace_cli_blackbox.py::test_blackbox_root_generated_command_executes_through_console_script` | Duplicate generated-command success-path black-box coverage. | Existing `modules.report.process` conformance runs through generated workspace Python and TypeScript command packages. |
| `tests/test_workspace_cli_blackbox.py::test_blackbox_root_generated_command_executes_primitive_ir_through_console_script` | Stable generated-command behavior belonged in a contract-owned defaults case. | New `defaults.root-cli-authority.process` conformance runs through generated workspace Python and TypeScript command packages. |
| `tests/test_workspace_defaults_cli.py::test_defaults_tiny_text_uses_generated_output` | Stable generated text output belonged in a contract-owned defaults case once `stdout.contains` was available. | New `defaults.tiny-text.process` conformance runs through generated workspace Python and TypeScript command packages. |
| `tests/test_workspace_defaults_cli.py::test_defaults_selected_section_text_uses_generated_output` | Stable generated selected-output text belonged in a contract-owned defaults case once `stdout.contains` was available. | New `defaults.selected-text.process` conformance runs through generated workspace Python and TypeScript command packages. |
| `tests/test_workspace_config_cli.py::test_config_selected_text_uses_generated_output` | Stable generated selected-output text belonged in a contract-owned config case once `stdout.contains` was available. | New `config.selected-text.process` conformance runs through generated workspace Python and TypeScript command packages. |
| `tests/test_workspace_config_cli.py::test_note_delegation_outcome_text_uses_generated_output` | Stable generated mutation-output text and write boundary belonged in a contract-owned delegation outcome case once `stdout.contains` was available. | New `delegation-outcome.append-text.process` conformance runs through generated workspace Python and TypeScript command packages. |

## Kept Ordinary

| Surface | Keep reason | Future conversion condition |
| --- | --- | --- |
| `tests/test_generated_tool_conformance.py` | Conformance harness, registry, and forbidden-write mechanics. These tests validate the runner itself rather than generated command behavior. | Keep ordinary unless a runner contract format is introduced. |
| `tests/test_generated_command_package_proof_runner.py` | Proof-step selection, crash classification, retry recovery, Docker routing, static drift checks, and checker internals. | Convert only stable command-output examples; keep proof/checker orchestration ordinary. |
| `tests/test_workspace_proof_generated_packages_cli.py` | AW proof routing and verification-lane semantics for generated package proof. | Keep ordinary because it tests AW proof selection, not generated command behavior. |
| `tests/test_command_generation_primitive_executor.py` | AW dependency wiring and temporary mirror coverage for command-generation primitive behavior. | Move portable primitive behavior upstream under `rickardvh/command-generation#9`; keep only AW integration wiring here. |
| `tests/test_command_generation_artifacts.py` | Artifact ownership, freshness, and operation fragment support checks. | Keep ordinary as contract/generator integrity checks. |
| `tests/test_workspace_cli_blackbox.py` | Remaining cases cover invalid target usage errors, near-miss command guidance, selector conflicts, and memory-route misuse. | Keep ordinary because these are adapter error classification and recovery-message surfaces. |
| `tests/test_workspace_cli.py` | Mixed CLI compatibility, selectors, and orchestration behavior. | Convert stable command-output examples only after operation owners are explicit and the case can name a contract owner. |
| `tests/test_workspace_config_cli.py` | Detailed config policy, local override, mixed-agent, and authority reporting semantics. Existing `config.report.process` and `config.selected-text.process` own stable generated command examples. | Convert additional stable compact-output examples only when they can be expressed as operation-owned cases without preserving transient policy seams. |
| `tests/test_workspace_defaults_cli.py` | Large defaults payload semantics and policy/authority regression checks. Existing `defaults.report.process`, `defaults.root-cli-authority.process`, `defaults.selected-text.process`, and `defaults.tiny-text.process` own stable generated command examples. | Convert additional stable section outputs only when they reduce duplicate assertions without hiding policy-review coverage. |
| `tests/test_workspace_implement_cli.py` | Planning safety, intent, proof, delegation, and generated-conformance proof guidance semantics. | Keep high-risk workflow trust regressions ordinary until operation or fragment owners settle. |
| `tests/test_workspace_proof_cli.py` | Proof-selection semantics, verification integration, and completion-claim safety. | Keep ordinary until stable proof/report contract owners can express the behavior. |
| `tests/test_workspace_report_cli.py` | Report UX, closeout, authority boundary, and semantic caveat behavior. | Keep ordinary while report semantics are evolving; convert stable command-facing examples only. |
| `tests/test_workspace_start_preflight_cli.py` | Startup/preflight routing, intent preservation, and generated-package proof recommendations. | Keep ordinary while startup safety and routing semantics are high-risk. |

## Boundary

This inventory does not claim every ordinary test should disappear. Ordinary tests remain legitimate when they prove runner internals, adapter error classification, proof/checker orchestration, schema/generator mechanics, high-risk workflow semantics, or a narrow bug repro that cannot yet be expressed as a stable operational contract.

## Drift Guard

`tests/test_maintainer_surfaces.py::test_testing_strategy_guides_against_one_off_regression_sprawl` keeps this inventory visible from the maintainer test strategy. It asserts the converted old test names, replacement contract ids, and retained generated-command proof surfaces so a future PR cannot silently remove the #1374 implementation record while keeping ordinary regressions.
