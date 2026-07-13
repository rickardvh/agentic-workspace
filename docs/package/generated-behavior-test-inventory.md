# Generated Behavior Test Inventory

This inventory closes the generated-behavior migration question for #1445. It accounts for the AW tests that mention generated command behavior and classifies each group by the owner that should keep proving it.

The rule is behavioral, not filename based. Tests stay in AW when they prove AW-specific operation contracts, proof routing, packaging, lifecycle behavior, wrapper boundaries, or runtime primitives. Generic generated-artifact conformance machinery belongs to `command-generation`.

The CLI wrapper boundary is defined in [CLI boundary tests](cli-boundary-tests.md). Use that page when deciding whether a CLI-heavy regression should remain as argv/help/error/exit/stdout proof or move to operation conformance.

## Migrated To Operation Conformance

These behaviors are represented as JSON operation conformance cases in `src/agentic_workspace/contracts/operation_conformance_test_ir.json` and executed by `scripts/check/run_operation_conformance_tests.py`.

| Behavior | Case | Owner | Rationale |
| --- | --- | --- | --- |
| Root `modules` generated router behavior | `modules.report-router.success` | AW operation conformance | AW-specific modules router fields represented by an IR-backed wrapper-smoke case until direct artifacts exist. |
| Root `defaults` root authority JSON behavior | `defaults.root-cli-authority.success` | AW operation conformance | AW-specific defaults contract fields through direct Python/TypeScript operation callables. |
| Root `defaults` tiny text behavior | `defaults.tiny-router-text.success` | AW operation conformance | Generated tiny-router text represented as wrapper-boundary output, not ordinary regression bulk. |
| Root `defaults` selected-output behavior | `defaults.selected-output.success` | AW operation conformance | AW-specific command contract and selected-output envelope. |
| Root `config` selected-output behavior | `config.selected-output.success` | AW operation conformance | AW-specific config contract and selected-output envelope through direct Python/TypeScript operation callables. |
| Root `config` invalid-format behavior | `config.invalid-format.error` | AW wrapper boundary | AW-specific option contract; invalid generated parser choice handling remains wrapper-smoke because direct JSON-shaped operation callables do not own argv choice rejection. |
| Delegation outcome generated text behavior | `delegation-outcome.append-text.boundary` | AW operation conformance | Generated text envelope and declared local-write effect represented as a boundary case. |
| Delegation outcome Python write behavior | `delegation-outcome.append-write.boundary` | AW operation conformance | Python wrapper target proves the local-only file write effect; TypeScript currently owns text-envelope parity only. |
| Memory `list-skills` generated target parity | `memory.list-skills.parity` | AW operation conformance | First-party module contract with Python/TypeScript parity proof. |

## Moved To Command-Generation Ownership

The shared package now owns the generic machinery that AW should not duplicate:

| Surface | Command-generation owner | AW usage |
| --- | --- | --- |
| CLI/process contract execution | `process_case_from_contract`, `CliConformanceTarget`, `run_cli_conformance_case` | Used for wrapper-smoke execution of AW-specific cases. |
| Direct JSON-shaped function execution | `operation_case_from_contract`, `FunctionConformanceTarget`, `run_function_conformance_case` | Used by AW runner for `python.function` artifacts when the registry declares an importable symbol. |
| TypeScript direct operation execution | `TypescriptFunctionConformanceTarget`, `run_typescript_function_conformance_case` | Used by AW runner for `typescript.function` artifacts through generated `invokeGeneratedOperation(...)` runtime exports. |
| Shared ownership/accounting | `conformance_ownership_inventory` | Records which conformance surfaces are generic and which remain consumer-owned. |
| Package-owned reusable conformance cases | `contract_conformance_cases_manifest`, `load_contract_conformance_case` from `rickardvh/command-generation#13` | Replaces repeated inline generic conformance payloads in command-generation tests; AW consumes the pinned revision instead of carrying generic cases. |
| Generated output staleness by target family | `generated_output_freshness_report` | AW consumes it for generated package freshness instead of owning generic hashing semantics. |
| Portable operation IR execution and composition | `run_operation_steps`, `PrimitiveRegistry`, `CommandGenerationHostManifest` | AW pins and tests the dependency; product primitives stay in AW. |
| Canonical generated command artifact projection | `canonical_command_artifacts` plus command-generation fixture tests | Former AW artifact tests were moved out of `tests/test_command_generation_artifacts.py`. |
| Portable primitive executor behavior | `tests/test_primitive_executor.py` in command-generation | Former duplicate AW primitive tests were removed; AW keeps only consumer integration coverage. |

## Retained In AW With Narrow Owners

The mechanically checked source for this section is `src/agentic_workspace/contracts/generated_behavior_stratification.json`, under `retained_ordinary_test_groups`. Each retained group must name its owner, proof route, keep reason, future conversion condition, and durable boundary rationale.

| Test group | Owner | Why it remains handwritten in AW | Future conversion | Durable boundary rationale |
| --- | --- | --- | --- | --- |
| `tests/test_generated_command_package_proof_runner.py` proof-step, Docker, crash classification, retry, completion-gate, runtime-boundary, and projection-inventory tests | AW proof/routing and migration gates | These prove AW's proof selector, completion gates, Docker posture, and runtime-source boundaries, not generic command-generation behavior. | Move deterministic adapter execution or primitive behavior to command-generation or operation conformance when the test no longer depends on AW proof-routing posture. | AW owns when generated package proof is adequate for workspace completion; command-generation owns reusable execution primitives. |
| `tests/test_contract_tooling.py` command adapter generation, command package IR, operation conformance IR, artifact registry, generated package freshness, live CLI parity, and generated target tests | AW contract/source-of-truth checks | These validate AW contract manifests, generated mirrors, package resources, and live CLI compatibility. Generic renderer behavior is covered in command-generation. | Move generic renderer, primitive, or adapter mechanics to command-generation tests; move stable black-box operation behavior to operation conformance cases. | AW retains package-specific contract integrity and generated-resource visibility tests even when behavior execution is IR-backed. |
| `tests/test_workspace_proof_generated_packages_cli.py` | AW proof routing | These prove changed-path selection chooses generated-package and operation-conformance proof routes. | Collapse into generated proof-routing contract cases when route selection is fully represented as declarative source-path to proof-lane mappings; move any reusable route-evaluation machinery to command-generation. | AW owns proof selection for its installed workspace lifecycle; reusable conformance execution alone cannot prove the routing decision. |
| `tests/test_generated_tool_conformance.py` | AW black-box tool contracts | These cover AW tool contracts, filesystem side effects, and adapter write guards. The generic process runner is supplied by command-generation. | Convert stable command behavior to operation conformance and move generic process-runner assertions to command-generation when filesystem safety is not the subject. | The retained behavior is local workspace safety and write-guard policy, not generic command invocation. |
| `tests/test_command_generation_integration.py` | AW dependency integration | This proves AW pins and consumes command-generation operation fragments and host primitive handlers correctly. Primitive internals and generic artifact projection are tested in command-generation. | Move behavior to command-generation when it proves generic package capability; keep only consumer pinning, projection, and host-manifest integration in AW. | AW must prove the specific dependency boundary it consumes even when the upstream package owns reusable implementation semantics. |
| Packaging, lifecycle, skills, start/implement/report/defaults tests that mention generated surfaces | AW installed-product behavior | These assert shipping, install/upgrade, ordinary routing, compact output, and generated-resource visibility in the AW product. | Move stable operation input-output behavior to conformance cases and move reusable generated artifact checks to command-generation once the installed-product posture is no longer the subject. | Installed-product behavior is an AW domain boundary: users experience generated resources through AW startup, proof, lifecycle, and package surfaces. |

## Rejected Or Not Migrated

No current test group was copied into operation conformance solely because it mentions generated files. The following are intentionally not migrated:

- parser/help/stdout/stderr/exit-code behavior when the CLI wrapper is the artifact under test;
- installed-package lifecycle and shipping checks;
- proof route selection and closeout/completion gates;
- runtime primitive and product integration tests;
- generated freshness and structured inventory checks whose subject is source-of-truth integrity rather than command behavior.

The previous AW-local generic command-generation primitive and artifact tests were not preserved as duplicate regression mass. Their generic behavior is now covered in command-generation, including package-owned reusable conformance case resources from `rickardvh/command-generation#13`, and AW retains only the dependency-integration checks named above.

## Conversion Closure

The ordinary generated-behavior regressions previously identified in the AW contract-test replacement inventory are now accounted for by operation-conformance IR cases: modules report, defaults root authority, defaults tiny text, defaults selected text, config selected text, delegation outcome text/write behavior, and memory list-skills parity. Remaining ordinary tests that mention generated surfaces are retained only under the narrow owners above: proof/checker routing, source-of-truth contract checks, adapter/write-guard mechanics, installed-product behavior, lifecycle behavior, runtime primitive integration, or high-risk workflow trust semantics.

The `defaults.selected-output.success`, `defaults.root-cli-authority.success`, and `config.selected-output.success` cases have real `python.function` and `typescript.function` artifacts in the registry, with TypeScript routed through the generated `invokeGeneratedOperation(...)` callable rather than the CLI writer path. Other converted cases stay wrapper-smoke only where the behavior is wrapper presentation, generated process conformance, target-specific mutation effect coverage, or where direct operation artifacts do not exist yet. Future migrations should promote additional behavior only when a direct operation artifact exists for that behavior; otherwise keep CLI coverage as wrapper-smoke proof and leave semantic completion claims on direct operation adapters.
