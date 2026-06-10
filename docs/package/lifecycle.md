# Lifecycle And Context Commands

The `agentic-workspace` CLI has two jobs:

- mutate managed repository surfaces through explicit lifecycle commands;
- answer compact context questions so agents do not need to scan raw files first.

## Lifecycle Commands

| Command | Role | Mutates files | Use when |
| --- | --- | --- | --- |
| `init` | conservative bootstrap or adopt front door | yes | setting up a repo from a preset |
| `install` | install selected modules | yes | adding one or more modules explicitly |
| `upgrade` | refresh managed surfaces | yes | updating package-managed files in an installed repo |
| `uninstall` | remove managed surfaces conservatively | yes | removing the workspace install or selected modules |
| `status` | read installed module state | no | checking what is installed |
| `doctor` | inspect drift and remediation | no | diagnosing missing, stale, or conflicting surfaces |

Mutating commands are conservative. They operate on package-owned surfaces, managed fences, and module-owned directories, and report manual-review cases instead of blindly rewriting repo-owned content.

## Context Commands

| Command | First question answered |
| --- | --- |
| `start` | What is the minimum safe startup context for this repository? |
| `summary` | What active planning or handoff state matters now? |
| `preflight` | What startup, config, and active state should a takeover load together? |
| `report` | What installed modules, warnings, selectors, and next actions are visible? |
| `proof` | Which proof or validation lane fits these changed paths? |
| `ownership` | Which surface owns this concern or path? |
| `config` | What repo and local workspace posture is resolved now? |
| `defaults` | What default policy or routing contract answers this class of question? |
| `modules` | Which modules are available or installed? |
| `skills` | Which package or repo skills are registered for this task? |

These commands are router views over checked-in state and package contracts. They should be queried before opening raw planning, memory, ownership, or contract files. When known sources may change task interpretation, proof, work shape, or completion claims, commands may surface compact [pre-work knowledge gates](knowledge-gates.md) instead of broad reading lists.

The command list is not the ordinary workflow. The reviewed operating model in
[Ordinary continuity loop and surface classification](ordinary-continuity-loop.md)
classifies these commands as loop entrypoints, routed aids, diagnostics,
lifecycle mutations, or advanced/module surfaces.

Exact output contracts are documented in the generated [Startup context](../reference/startup-context.md), [Workspace report](../reference/workspace-report.md), [Workspace config](../reference/workspace-config.md), [Workspace local override](../reference/workspace-local-override.md), [Proof selection rules](../reference/proof-selection-rules.md), and [Preflight policy](../reference/preflight-policy.md) references.

## Optional Diagnostic Commands

Some commands are useful in advanced host repositories but are not ordinary startup input:

- `setup`: post-bootstrap setup findings and guidance.
- `reconcile`: stale planning state against provider-agnostic external work evidence.
- `external-intent refresh-github`: optional GitHub issue evidence refresh.
- `note-delegation-outcome`: local-only delegation outcome tuning.

## Command Contracts

The declared root command surface lives in `src/agentic_workspace/contracts/cli_commands.json` and is documented in [CLI commands](../reference/cli-commands.md). Runtime behavior remains in the package code; the contract makes command roles, audiences, and options inspectable without reading the CLI implementation.
