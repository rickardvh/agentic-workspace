# Contract Schema Index

This page indexes the first shared schemas and manifests for workspace contract tooling.

Use it when you need to know which checked-in file owns a machine-readable contract shape, who consumes it, and which validation lane should catch drift.

## Ownership

- Manifests live under [`src/agentic_workspace/contracts/`](../src/agentic_workspace/contracts/).
- Schemas live under [`src/agentic_workspace/contracts/schemas/`](../src/agentic_workspace/contracts/schemas/).
- Runtime consumers live in [`src/agentic_workspace/cli.py`](../src/agentic_workspace/cli.py).
- Development-time validation lives in `scripts/check/check_contract_tooling_surfaces.py`.

## First Manifest Set

| Manifest | Owns | Primary consumers |
| --- | --- | --- |
| `compact_contract_profile.json` | compact answer envelope metadata and selector definitions | `defaults`, compact selector answers |
| `proof_routes.json` | stable proof route ids and commands | `defaults`, `proof` |
| `report_contract.json` | stable report schema metadata | `report` |
| `contract_inventory.json` | declarative/procedural/derived boundary inventory | docs and contract-tooling checker |

## First Schema Set

| Schema | Validates |
| --- | --- |
| `compact_contract_answer.schema.json` | emitted compact selector answers |
| `selector_contracts_manifest.schema.json` | selector manifest |
| `proof_routes_manifest.schema.json` | proof routes manifest |
| `report_contract_manifest.schema.json` | report contract manifest |
| `workspace_report.schema.json` | emitted workspace report envelope |
| `contract_inventory.schema.json` | boundary inventory |
| `workspace_config.schema.json` | `.agentic-workspace/config.toml` |
| `workspace_local_override.schema.json` | `.agentic-workspace/config.local.toml` |
| `setup_findings.schema.json` | `tools/setup-findings.json` |
| `delegation_outcomes.schema.json` | `.agentic-workspace/delegation-outcomes.json` |

## Guardrails

- These schemas are for development-time validation and drift checks, not adopter runtime requirements.
- Keep manifest scope narrow and stable.
- Keep canonical docs authoritative for semantics; schemas and manifests make the shape inspectable and checkable.

## Relationship To Other Docs

- Use [`docs/declarative-contract-boundary.md`](declarative-contract-boundary.md) for the boundary between declarative, procedural, and derived behavior.
- Use [`docs/contributor-playbook.md`](contributor-playbook.md) for the maintainer validation lane that should run the contract-tooling check after edits here.
