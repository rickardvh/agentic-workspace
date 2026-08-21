# Module Extension Effort Ledger

This ledger records the non-module repository files touched while proving the `agentic-workspace/module-capability/v2` seam. It separates implementation of the generic public seam from wiring used only to prove it. A real external module installs through the `agentic_workspace.modules` entry-point group and requires no Agentic Workspace repository edit.

## Semantic core edits that established the public seam

| Repository surface | Classification | Why it changed |
| --- | --- | --- |
| `src/agentic_workspace/module_contract.py` | Generic public contract implementation | Validates, discovers, relevance-filters, and invokes any entry-point module without knowing its identity. |
| `src/agentic_workspace/workspace_runtime_core.py` | Generic kernel adapter | Converts any admitted public descriptor into the existing resolve/act/reconcile representation and enforces selection conflicts. |
| `src/agentic_workspace/contracts/schemas/module_capability.schema.json` | Public schema | Defines the identity-agnostic authoring contract. |
| `src/agentic_workspace/contracts/schemas/module_registry.schema.json` and `src/agentic_workspace/contracts/module_registry.json` | First-party parity metadata | Projects the same public contract for bundled modules; no external module identity is registered here. |
| `src/agentic_workspace/_schema.py` and `scripts/check/check_contract_tooling_surfaces.py` | Generic schema/tool discovery | Makes the public contract discoverable and checked without adding a module-specific branch. |

## Generic proof and package wiring

| Repository surface | Classification | Why it changed |
| --- | --- | --- |
| `tests/fixtures/external_signals_module/**` | External package fixture | Copied outside the checkout and installed as its own distribution during the conformance test. Its `pyproject.toml`, provider, resources, operation, and results are the complete external author work. |
| `tests/test_module_contract.py` | Generic conformance harness | Proves installed discovery, relevance/irrelevance, read-only resources, typed operation/results, incompatibility, ownership conflict, and clean removal/restart. |
| `tests/test_workspace_modules_cli.py` | Existing CLI compatibility proof | Confirms the generic registry remains inspectable; it contains no fixture identity switch. |
| `tests/test_workspace_skills_cli.py`, skill registry/schema/generated skill files, and plugin manifest | Generated/package synchronization | Keeps existing shipped projections consistent after contract generation; none are required when an external package is installed. |
| Documentation and generated schema references | Public explanation/reference | Explain the seam and derive exact contract fields; they do not register a module. |
| Planning and release metadata | Work tracking | Records the lane and release note only; it has no runtime role. |

## External-consumer result

The installed fixture is discovered from distribution metadata after its temporary install directory is added to the interpreter path. Removing that path and resolving again removes every fixture contribution. No core name list, enum, phase, slot, posture fragment, skill, proof branch, closeout branch, or registry entry names `external-signals`.

## Cost and trust review

The maintained scenario matrix is
`tools/model-cli-harness/external-agent-evaluation/module-extension-scenario-matrix.json`.
For agent use, a relevant module adds one bounded contribution through the
ordinary decision while an irrelevant module adds none; conflicts,
incompatibility, and removal retain one kernel-owned recovery boundary. For an
independent author, the required concepts stop at compatibility, ownership,
relevance, capabilities, and result semantics. The fixture needed no
identity-specific Workspace runtime, registry, canonical-skill, phase, proof,
or closeout edit.
