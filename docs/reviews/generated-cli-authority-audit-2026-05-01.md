# Generated CLI Authority Audit

Date: 2026-05-01.
Scope: post-#641 root, Planning, and Memory command/interface authority.

This is a current-state audit for generated CLI migration follow-ups #657-#660. It is evidence for reviewers, not the canonical command source. The canonical command/interface sources remain `src/agentic_workspace/contracts/command_adapter_generation.json`, `src/agentic_workspace/contracts/command_package_ir.json`, operation contracts, conformance contracts, and generated output freshness checks.

## Classification Model

| Classification | Meaning |
| --- | --- |
| `generated` | Command/interface truth is contract-backed and generated parser/dispatch is active for the Python package target. |
| `eligible-dry-run-refusal` | Lifecycle command has proved dry-run or refusal conformance and may expose generated no-write/refusal-safe interfaces, but apply/mutation dispatch remains deferred. |
| `procedural-owned` | The interface remains hand-authored because the command is a support procedure, prompt renderer, nested command family, or runtime-owned workflow surface. |
| `deferred-mutation` | Command writes repo state and must not become mutation-capable generated dispatch until safety gates pass. |
| `eligible-refusal-only` | Destructive command has proved refusal behavior that may mature separately, while destructive apply dispatch remains deferred. |
| `deferred-destructive` | Command may remove state and needs destructive/refusal proof plus review-required signaling before mutation-capable promotion. |
| `deferred-layout` | Generated Python output location is intentionally deferred until generated CLIs are fully landed; tracked by #661. |

## Root Workspace CLI

| Commands | Classification | Interface authority | Runtime owner | Next owner |
| --- | --- | --- | --- | --- |
| `defaults`, `config`, `modules`, `start`, `summary`, `implement`, `preflight`, `proof`, `ownership`, `skills`, `report`, `reconcile`, `setup`, `status`, `doctor` | `generated` | `command_package_ir.json` and `command_adapter_generation.json` | `src/agentic_workspace/cli.py` runtime handlers and module primitives | Current checks |
| `install`, `init`, `upgrade` dry-run/refusal-safe surface | `eligible-dry-run-refusal` | `lifecycle_generation_readiness.json`, operation contracts, conformance contracts | workspace lifecycle primitives | #659 |
| `uninstall` refusal-safe surface | `eligible-refusal-only` | `lifecycle_generation_readiness.json`, operation contracts, conformance contracts | workspace lifecycle primitives | #659 |
| `install`, `init`, `adopt`, `upgrade` apply behavior | `deferred-mutation` | hand-authored until mutation promotion gates pass | workspace lifecycle primitives | #660 |
| `uninstall` apply behavior | `deferred-destructive` | hand-authored until destructive promotion gates pass | workspace lifecycle primitives | #660 |
| Generated Python output under `src/agentic_workspace/generated_cli_package` | `deferred-layout` | generated output path is temporary package-integration shape | packaging/import glue | #661 |

## Planning Package CLI

| Commands | Classification | Interface authority | Runtime owner | Next owner |
| --- | --- | --- | --- | --- |
| `status`, `doctor`, `summary`, `report`, `reconcile` | `generated` | `command_package_ir.json` and `command_adapter_generation.json` | `packages/planning/src/repo_planning_bootstrap/cli.py` runtime handlers and installer/report primitives | Current checks |
| `install`, `init`, `adopt`, `upgrade`, `uninstall`, `handoff`, `promote-to-plan`, `archive-plan`, `create-review`, `list-files`, `verify-payload`, `prompt` | `procedural-owned` or mutation/deep workflow surface | hand-authored package CLI | planning installer and maintenance primitives | Future bounded issue only when stable command contracts are needed |

## Memory Package CLI

| Commands | Classification | Interface authority | Runtime owner | Next owner |
| --- | --- | --- | --- | --- |
| `status`, `doctor`, `report`, `route-report`, `promotion-report`, `list-files`, `list-skills` | `generated` | `command_package_ir.json` and `command_adapter_generation.json` | `packages/memory/src/repo_memory_bootstrap/cli.py` runtime handlers and installer/report primitives | Current checks |
| `install`, `init`, `adopt`, `upgrade`, `migrate-layout`, `uninstall`, `prompt`, `current`, `route`, `route-review`, `sync-memory`, `create-note`, `capture-note`, `search`, `verify-payload`, `bootstrap-cleanup` | `procedural-owned` or mutation/deep workflow surface | hand-authored package CLI | memory installer, routing, note, and maintenance primitives | Future bounded issue only when command contracts are stable enough to migrate |

## Enforcement

- Generated adapter metadata freshness is checked by `uv run python scripts/generate/generate_command_adapters.py --check`.
- Generated command package freshness is checked by `uv run python scripts/generate/generate_command_packages.py --check`.
- Contract parity is checked by `uv run python scripts/check/check_contract_tooling_surfaces.py --quiet-success`.
- Black-box process behavior is checked by `uv run pytest tests/test_generated_tool_conformance.py -q`.
- Mutation-capable promotion is blocked by `lifecycle_generation_readiness.json` until dry-run/apply/refusal/local-only/idempotency gates are explicit and proved.

## Follow-Ups

- #660 added mutation-capable lifecycle promotion gates.
- #661 owns moving generated Python outputs under `generated/python` after generated CLIs are truly landed.
- #627 owns large-file hotspot remediation and is intentionally not part of this authority audit.
