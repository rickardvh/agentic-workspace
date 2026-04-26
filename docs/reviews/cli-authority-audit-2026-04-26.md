# CLI Authority Audit

Date: 2026-04-26

Issue: #357

Purpose: classify remaining hand-authored CLI authority before any generated shipped CLI adapter work under #356. This is a review/evidence artifact, not ordinary startup input.

## Summary

The root `agentic-workspace` CLI is the only inspected CLI with contract-backed command and option shape today. Its parser is assembled from `src/agentic_workspace/contracts/cli_commands.json` and shared option groups, and every root command has a draft operation contract. Runtime dispatch is still hand-authored in Python, which is acceptable for primitive behavior but means no command is yet a generated adapter end to end.

The planning and memory package CLIs still own their interface shape directly in argparse. Some commands are good future candidates for contract extraction, but neither package currently has enough command/option/operation contract detail to generate an adapter without first moving interface authority out of the CLI module.

First low-risk generated adapter candidate: root `agentic-workspace defaults`. It is read-only, already has manifest-backed command/options, has a draft operation contract and primitive mapping, and has no target repository mutation path. It should prove adapter generation on the smallest surface before touching planning or memory lifecycle commands, after #358 defines the command-adapter generation contract.

## Root CLI: `src/agentic_workspace/cli.py`

Authority state:

- Parser/interface shape: manifest-backed by `cli_commands.json` plus option groups.
- Operation descriptions: present for root commands in `operation_contracts.json`, all currently marked `draft-contract-only`.
- Primitive vocabulary: present in `operation_primitives.json`.
- Runtime dispatch: still hand-authored in `main`.

Command classification:

| Command group | Classification | Reason |
| --- | --- | --- |
| `defaults` | generation-ready as first adapter candidate | Read-only, no target mutation, command/options are manifest-backed, operation contract maps to defaults load/select plus output emit. Runtime implementation can remain a primitive call. |
| `modules`, `config`, `summary`, `proof`, `ownership`, `reconcile` | missing dispatch or primitive mapping | Interface and draft operation contracts exist, but generated dispatch has not been introduced and the current command-to-call mapping remains Python-owned. |
| `start`, `implement`, `preflight`, `report` | missing schema or operation contract detail | These aggregate multiple surfaces and selection rules. Contracts exist, but generated adapters need tighter output/selector expectations before they should become early candidates. |
| `skills`, `system-intent`, `note-delegation-outcome` | intentionally runtime-owned primitive behavior | Interface can be generated later, but registry inspection, metadata refresh, and local-only append behavior should stay runtime primitives. |
| `setup`, `prompt` | still hand-authored interface authority | The command shape is in the manifest, but the behavior is mostly rendered guidance and should wait until generated-adapter rendering rules are proven on smaller read-only report commands. |
| `install`, `init`, `upgrade`, `uninstall`, `doctor`, `status` | defer with reason | Lifecycle and health commands cross module orchestration, preflight gating, and mutation policy. Do not use these as the first adapter-generation proof. |

## Planning CLI: `packages/planning/src/repo_planning_bootstrap/cli.py`

Authority state:

- Parser/interface shape: still hand-authored argparse.
- Operation descriptions: no package-local command manifest or operation-contract registry equivalent was found for this CLI.
- Runtime dispatch: hand-authored `if args.command` chain.

Command classification:

| Command group | Classification | Reason |
| --- | --- | --- |
| `summary`, `report`, `reconcile`, `handoff` | missing schema or operation contract detail | Read-only and plausible future candidates, but command/options and output contracts must be extracted before adapter generation. |
| `list-files`, `verify-payload`, `prompt` | still hand-authored interface authority | Small support commands, but currently encoded directly in the CLI module. They can follow after a shared package-CLI manifest pattern exists. |
| `promote-to-plan`, `archive-plan` | intentionally runtime-owned primitive behavior | These mutate planning state and encode closeout/cleanup policy. Interface extraction is possible later, but behavior should stay implementation-owned. |
| `install`, `init`, `adopt`, `upgrade`, `uninstall`, `doctor`, `status` | defer with reason | Lifecycle and diagnostic commands should wait until read-only adapter generation is proven. |

## Memory CLI: `packages/memory/src/repo_memory_bootstrap/cli.py`

Authority state:

- Parser/interface shape: still hand-authored argparse.
- Operation descriptions: no package-local command manifest or operation-contract registry equivalent was found for this CLI.
- Runtime dispatch: handler table exists, but command and option authority still lives in Python.

Command classification:

| Command group | Classification | Reason |
| --- | --- | --- |
| `report`, `route`, `route-review`, `route-report`, `current show`, `current check`, `promotion-report`, `search` | missing schema or operation contract detail | These are mostly read-only and good later candidates, but need extracted command/option manifests and operation contracts first. |
| `list-files`, `list-skills`, `verify-payload`, `prompt` | still hand-authored interface authority | Support commands remain argparse-owned and should follow a shared package-CLI manifest pattern. |
| `sync-memory` | intentionally runtime-owned primitive behavior | It proposes repository memory changes and improvement candidates; generation should only cover interface wiring after behavior remains primitive-owned. |
| `install`, `init`, `adopt`, `upgrade`, `migrate-layout`, `uninstall`, `doctor`, `status`, `bootstrap-cleanup` | defer with reason | Lifecycle, migration, cleanup, and health commands are higher-risk and should not be early generated-adapter candidates. |

## Recommended Next Slice

Use #358 to define the command-adapter generation contract, then use #359 to generate or mechanically assemble the root `defaults` adapter from existing root command and operation contracts. #360, #361, #362, and #363 are follow-on guardrail, package-extension, and projection slices that should preserve this audit's boundary between interface authority and runtime primitive implementation.

The first implementation proof should verify that:

- Help/arguments still match `cli_commands.json`.
- Runtime behavior still calls the existing defaults primitive path.
- The generated layer owns interface wiring only, not business logic.
- No planning or memory package CLI migration begins until the root pattern is reviewed.
