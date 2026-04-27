# Multi-Language CLI Generation Gap Audit

Date: 2026-04-27

Issues: #394, parent #393

Purpose: identify what remains before Python and TypeScript CLI packages can be generated from implementation-independent definitions. This is evidence/history, not ordinary startup input.

## Summary

The current repo has enough contract machinery to start a multi-language generated-package proof, but not enough to generate complete CLI packages without an explicit command-package view.

Already present:

- Root `agentic-workspace` command shape lives in `src/agentic_workspace/contracts/cli_commands.json` plus `cli_option_groups.json`.
- Root executable commands have operation contract entries under `src/agentic_workspace/contracts/operation_contracts.json` and `operations/`.
- Command adapter generation metadata exists at `src/agentic_workspace/contracts/command_adapter_generation.json`.
- Generated process adapters already exist for root `defaults`, planning `status`, and memory `status`.
- Conformance contracts exist for generated process adapters.

Still missing:

- One compact command-package definition that joins command shape, operation ref, primitive binding, conformance refs, package target metadata, and adapter projection constraints.
- Package-local command manifests for planning and memory equivalent to root `cli_commands.json`.
- A generated package target model that distinguishes universal command truth from language/package-specific files.
- Docker-isolated proof for generated non-Python targets.
- Contribution guardrails that classify direct CLI edits as runtime-primitive work or migration exceptions.

## Current Surface Classification

| Surface | Current authority | Multi-language readiness |
| --- | --- | --- |
| Root command names/options | `cli_commands.json` and option groups | Good for Python/TypeScript parser generation after joining with operation refs. |
| Root operations | `operation_contracts.json` and `operations/*.json` | Good enough for read-only surfaces; lifecycle mutation still deferred. |
| Root generated adapter metadata | `command_adapter_generation.json` | Useful seed, but it is adapter-centric rather than package-centric. |
| Planning CLI parser | `packages/planning/src/repo_planning_bootstrap/cli.py` | Partially generated dispatch for `status`; most command shape remains Python-owned. |
| Memory CLI parser | `packages/memory/src/repo_memory_bootstrap/cli.py` | Partially generated dispatch for `status`; most command shape remains Python-owned. |
| Conformance | `conformance_contracts.json` plus per-operation files | Good for process adapters; needs generated-package target grouping. |
| Generated adapter files | generated Python modules | Good no-direct-edit precedent; not yet a package output. |

## Blockers To Python Package Generation

1. Root command generation needs one input that already knows which commands are generation eligible.
2. Generated Python package output needs target metadata: package name, entrypoints, generated files, and primitive binding module.
3. Direct edits to `src/agentic_workspace/cli.py` remain normal for non-generated command wiring.

Smallest safe proof: keep runtime primitives in the existing Python package, but generate a package adapter module for read-only command metadata and dispatch for `defaults`, planning `status`, and memory `status`.

## Blockers To TypeScript Package Generation

1. The universal command definition must avoid Python-specific argparse/module references.
2. TypeScript package output needs isolated generated files and a runtime-binding strategy. For first proof, use read-only commands with deterministic fixture/stub bindings instead of reimplementing live Python workspace inspection.
3. Tests must run in a container so ordinary repo development does not require Node.

Smallest safe proof: generate a TypeScript package fixture for the same eligible commands with conformance over command shape/help/metadata and any deterministic read-only fixture output that does not require Python runtime primitives.

## Blockers To Shell Adapters

Bash and PowerShell should wait until Python and TypeScript prove the IR. Shell adapters are plausible for thin wrappers, help/completion, and delegation to runtime packages. They should not embed runtime primitive behavior.

## Recommended First Implementation Slice

1. Define a command-package IR derived from existing contracts.
2. Validate that IR against a schema.
3. Generate small Python and TypeScript package fixtures from the IR.
4. Add Docker-isolated tests for the TypeScript fixture and Python generated package proof.
5. Add proof routing and direct-edit guidance.

## Off-The-Shelf Candidates To Evaluate

- JSON Schema validation: continue using `jsonschema` in Python.
- TypeScript types: use `json-schema-to-typescript` or `quicktype` if a real TypeScript package target grows beyond a tiny fixture.
- TypeScript CLI parser: prefer Commander.js or Yargs over custom option parsing.
- Python CLI parser: keep argparse for runtime compatibility, but derive parser metadata from the command-package IR.
- Containerized proof: use Docker Compose or plain Dockerfiles invoked by a Python check wrapper.

## Acceptance Evidence

#394 is satisfied when this audit is reviewed with #395's strategy record: the exact blockers, first safe slice, and off-the-shelf candidates are named without starting broad generation work.
