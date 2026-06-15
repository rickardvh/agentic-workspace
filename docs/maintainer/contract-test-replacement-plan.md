# Contract-Owned Test Replacement Plan

This plan sequences the post-migration replacement of ordinary regression tests with contract-owned conformance cases. It is the implementation plan for #1373 and the coordination surface for AW #1374 and `rickardvh/command-generation#9`.

## Target Shape

Operational contracts own canonical behavior examples. Python owns one authoritative runner. Generated CLIs, future MCP targets, and other transports provide thin adapters that execute the same cases and normalize results.

Do not preserve the current test layout by renaming ordinary tests into contract-shaped files. Convert behavior only when the primitive, fragment, operation, or command boundary is stable enough that the case will not encode a temporary implementation seam.

## Readiness Gates

Start broad conversion only when all gates are true:

- Portable primitive migration is stable enough that primitive behavior belongs in command-generation-owned contracts.
- Fragment or composite operation structure is stable enough that reusable workflow behavior can attach below command-level black-box tests.
- Generated Python and TypeScript targets are fresh and covered by shared conformance runner proof.
- A converted case can name one behavior owner: primitive, fragment/subflow, operation, command adapter, runner internals, or host-specific orchestration.

If a behavior cannot name one owner yet, keep the ordinary test and mark the blocker in the inventory.

## AW Inventory

| Surface | Current role | Replacement category | Owner |
| --- | --- | --- | --- |
| `src/agentic_workspace/contracts/conformance/*.json` | 85 existing process-level conformance cases as of the June 15, 2026 #1525 refresh | Keep and expand as contract-owned command/process cases | AW contracts |
| `tests/test_generated_tool_conformance.py` | Harness and registry checks for process conformance | Keep ordinary runner/harness tests; add converted cases under contracts | AW |
| `tests/test_generated_command_package_proof_runner.py` | Generated package proof orchestration, freshness, boundary checks, and conformance routing | Keep proof/checker internals ordinary; convert stable command behavior assertions to operation conformance cases | AW |
| `tests/test_workspace_proof_generated_packages_cli.py` | Proof route selection for generated package paths | Keep ordinary proof-routing tests | AW |
| `tests/test_command_generation_primitive_executor.py` | AW mirror of command-generation portable primitive behavior and operation fragment execution | Convert portable primitive behavior to command-generation contract cases; keep only AW integration tests that prove dependency wiring | command-generation plus AW integration |
| `tests/test_command_generation_artifacts.py` | Artifact ownership, generated target freshness, operation fragment support | Keep ordinary artifact/freshness checks | AW |
| `tests/test_workspace_cli_blackbox.py` | Console-script and adapter behavior | Keep minimal representative adapter tests; convert stable command outputs to operation cases | AW |
| `tests/test_workspace_cli.py` | Mixed CLI compatibility, selectors, and orchestration behavior | Split: convert stable command outputs; keep selector/orchestration/error-route tests ordinary | AW |
| `tests/test_workspace_config_cli.py`, `tests/test_workspace_defaults_cli.py` | Command behavior and output shaping | Convert stable output examples to operation cases; keep policy edge cases ordinary until fragments own them | AW |
| `tests/test_workspace_implement_cli.py`, `tests/test_workspace_proof_cli.py`, `tests/test_workspace_report_cli.py`, `tests/test_workspace_start_preflight_cli.py` | High-risk workflow/report/proof surfaces with many semantic edge cases | Convert only stable command-facing examples first; keep assurance, intent, proof, and closeout trust regressions ordinary until owner contracts are settled | AW |

## Command-Generation Inventory

| Surface | Current role | Replacement category | Owner |
| --- | --- | --- | --- |
| `tests/test_public_api.py` | Package API, generated package behavior, conformance runner drift examples, registry checks | Keep API/schema/generator mechanics ordinary; convert generated command behavior examples to package-owned contract cases | command-generation |
| `tests/test_primitive_executor.py` | Portable primitive behavior, fragments, primitive errors, operation dataflow | Convert stable primitive and fragment behavior to primitive/composite contract cases; keep executor internals and narrow bug repros ordinary | command-generation |
| `tests/primitive_conformance.py` | Python conformance runner support | Keep runner internals ordinary; consume contract cases from package resources | command-generation |

## Conversion Order

1. Stabilize owner boundaries.

   Confirm which primitive and fragment behaviors live in command-generation versus AW. Do this before moving tests so converted cases do not preserve pre-migration runtime seams.

2. Convert portable primitive behavior in command-generation.

   Move stable examples for filesystem, JSON, TOML, payload assembly, payload verification, output emit, fragment execution, and operation dataflow into contract-owned cases. Keep executor error mechanics ordinary where they are testing runner implementation rather than public behavior.

3. Convert AW generated-command behavior.

   Move stable generated command examples into `src/agentic_workspace/contracts/conformance/*.json` or the owning operation/composite contract surface. Execute them through the shared runner for Python and TypeScript generated targets.

4. Collapse duplicated ordinary tests.

   For each converted behavior, delete or merge the old regression only after the contract case proves the same behavior through the shared runner. Leave one representative adapter/black-box test per transport risk.

5. Reclassify remaining tests.

   Remaining ordinary tests must be explicitly one of: runner internals, adapter mechanics, proof/checker orchestration, schema/generator mechanics, high-risk semantic workflow, or temporary bug repro with a named blocker.

## Keep Ordinary

Keep ordinary pytest coverage for:

- runner internals and diff reporting;
- schema loading and generator mechanics;
- adapter argument mapping, result extraction, exit/error normalization, and capability reporting;
- proof/checker orchestration and generated target freshness;
- high-risk semantic workflow surfaces that do not yet have stable operation or fragment owners;
- narrow bug repros where the contract boundary is not stable enough yet.

## Delete Or Merge Only With Equivalent Coverage

Before deleting an ordinary regression, record:

- old test name;
- replacement contract id and case id;
- target adapters that execute it;
- proof command that ran it;
- remaining ordinary test, if any, that still covers adapter mechanics.

If that mapping cannot be written, do not delete the test.

## Issue Handoff

#1374 owns AW-side implementation using this plan.

`rickardvh/command-generation#9` owns command-generation implementation using this plan. `rickardvh/command-generation#13` implements the current package-owned reusable conformance case resource surface consumed by AW's #1446 simplification slice.

When either issue closes, its PR body should include an inventory table with `keep`, `convert`, `merge`, and `delete` rows plus proof that generated Python and TypeScript conformance remain green.
