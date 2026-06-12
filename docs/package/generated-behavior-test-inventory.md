# Generated Behavior Test Inventory

This inventory closes the generated-behavior migration question for #1445. It accounts for the AW tests that mention generated command behavior and classifies each group by the owner that should keep proving it.

The rule is behavioral, not filename based. Tests stay in AW when they prove AW-specific operation contracts, proof routing, packaging, lifecycle behavior, wrapper boundaries, or runtime primitives. Generic generated-artifact conformance machinery belongs to `command-generation`.

The CLI wrapper boundary is defined in [CLI boundary tests](cli-boundary-tests.md). Use that page when deciding whether a CLI-heavy regression should remain as argv/help/error/exit/stdout proof or move to operation conformance.

## Migrated To Operation Conformance

These behaviors are represented as JSON operation conformance cases in `src/agentic_workspace/contracts/operation_conformance_test_ir.json` and executed by `scripts/check/run_operation_conformance_tests.py`.

| Behavior | Case | Owner | Rationale |
| --- | --- | --- | --- |
| Root `defaults` selected-output behavior | `defaults.selected-output.success` | AW operation conformance | AW-specific command contract and selected-output envelope. |
| Root `config` invalid-format behavior | `config.invalid-format.error` | AW operation conformance | AW-specific option contract; wrapper execution remains smoke until direct generated artifacts exist. |
| Memory `list-skills` generated target parity | `memory.list-skills.parity` | AW operation conformance | First-party module contract with Python/TypeScript parity proof. |

## Moved To Command-Generation Ownership

The shared package now owns the generic machinery that AW should not duplicate:

| Surface | Command-generation owner | AW usage |
| --- | --- | --- |
| CLI/process contract execution | `process_case_from_contract`, `CliConformanceTarget`, `run_cli_conformance_case` | Used for wrapper-smoke execution of AW-specific cases. |
| Direct JSON-shaped function execution | `operation_case_from_contract`, `FunctionConformanceTarget`, `run_function_conformance_case` | Used by AW runner for `python.function` artifacts when the registry declares an importable symbol. |
| Shared ownership/accounting | `conformance_ownership_inventory` | Records which conformance surfaces are generic and which remain consumer-owned. |
| Package-owned reusable conformance cases | `contract_conformance_cases_manifest`, `load_contract_conformance_case` from `rickardvh/command-generation#13` | Replaces repeated inline generic conformance payloads in command-generation tests; AW consumes the pinned revision instead of carrying generic cases. |
| Generated output staleness by target family | `generated_output_freshness_report` | AW consumes it for generated package freshness instead of owning generic hashing semantics. |
| Portable operation IR execution and composition | `run_operation_steps`, `PrimitiveRegistry`, `CommandGenerationHostManifest` | AW pins and tests the dependency; product primitives stay in AW. |
| Canonical generated command artifact projection | `canonical_command_artifacts` plus command-generation fixture tests | Former AW artifact tests were moved out of `tests/test_command_generation_artifacts.py`. |
| Portable primitive executor behavior | `tests/test_primitive_executor.py` in command-generation | Former duplicate AW primitive tests were removed; AW keeps only consumer integration coverage. |

## Retained In AW With Narrow Owners

| Test group | Owner | Why it remains handwritten in AW |
| --- | --- | --- |
| `tests/test_generated_command_package_proof_runner.py` proof-step, Docker, crash classification, retry, completion-gate, runtime-boundary, and projection-inventory tests | AW proof/routing and migration gates | These prove AW's proof selector, completion gates, Docker posture, and runtime-source boundaries, not generic command-generation behavior. |
| `tests/test_contract_tooling.py` command adapter generation, command package IR, operation conformance IR, artifact registry, generated package freshness, live CLI parity, and generated target tests | AW contract/source-of-truth checks | These validate AW contract manifests, generated mirrors, package resources, and live CLI compatibility. Generic renderer behavior is covered in command-generation. |
| `tests/test_workspace_proof_generated_packages_cli.py` | AW proof routing | These prove changed-path selection chooses generated-package and operation-conformance proof routes. |
| `tests/test_generated_tool_conformance.py` | AW black-box tool contracts | These cover AW tool contracts, filesystem side effects, and adapter write guards. The generic process runner is supplied by command-generation. |
| `tests/test_command_generation_integration.py` | AW dependency integration | This proves AW pins and consumes command-generation operation fragments and host primitive handlers correctly. Primitive internals and generic artifact projection are tested in command-generation. |
| Packaging, lifecycle, skills, start/implement/report/defaults tests that mention generated surfaces | AW installed-product behavior | These assert shipping, install/upgrade, ordinary routing, compact output, and generated-resource visibility in the AW product. |

## Rejected Or Not Migrated

No current test group was copied into operation conformance solely because it mentions generated files. The following are intentionally not migrated:

- parser/help/stdout/stderr/exit-code behavior when the CLI wrapper is the artifact under test;
- installed-package lifecycle and shipping checks;
- proof route selection and closeout/completion gates;
- runtime primitive and product integration tests;
- generated freshness and structured inventory checks whose subject is source-of-truth integrity rather than command behavior.

The previous AW-local generic command-generation primitive and artifact tests were not preserved as duplicate regression mass. Their generic behavior is now covered in command-generation, including package-owned reusable conformance case resources from `rickardvh/command-generation#13`, and AW retains only the dependency-integration checks named above.

## Remaining Trigger

The current registry has no real `python.function` or `typescript.function` implementation artifacts for the migrated AW cases, so direct operation conformance is installed as a runner path and tested with a synthetic artifact. When generated command packages expose importable operation functions, add registry `symbol` entries, promote the affected cases from `cli.process` wrapper-smoke to `*.function` operation-conformance, and demote the corresponding wrapper tests to boundary-only smoke.
