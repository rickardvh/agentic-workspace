# Command Map

Commands are affordances for the current `resolve -> act -> reconcile` question, not a workflow agents must memorize.

For every current root command, nested subcommand, flag, default, choice, audience, role, and shared-state effect, use the generated [current CLI catalogue](../reference/cli-catalogue.md). The separate [CLI commands schema](../reference/cli-commands.md) and [option-group schema](../reference/cli-option-groups.md) explain data shape; they are not current-value catalogues.

## Ordinary routes

| Need | Route |
| --- | --- |
| Resolve first contact | `agentic-workspace start --target . --task "<task>" --format json` |
| Resolve known changed paths | `agentic-workspace implement --target . --changed <paths> --format json` |
| Inspect selected continuity | `agentic-workspace summary --target . --format json` |
| Select proof for changed paths | `agentic-workspace proof --target . --changed <paths> --format json` |
| Inspect a routed subsystem or contract | use the exact selector/operation named by the current decision |
| Diagnose installed state | `agentic-workspace doctor --target . --format json` |

Lifecycle mutation, Planning operations, module commands, and source-checkout diagnostics remain progressively disclosed in the generated catalogue. Package-level module CLIs are for explicit domain maintenance/debugging; the root Workspace CLI is the ordinary host-repo front door.

## Effect boundary

The command contract distinguishes shared workspace mutation from possible ignored local diagnostics. A command classified as shared-nonmutating may still append a machine-local session/log/cache record when the local runtime enables that feature. Those local effects do not become Planning, proof, configuration, or claim authority merely because they exist.

For exact output shapes, follow the generated catalogue into the relevant runtime/schema reference. Prefer compact default output and exact `--select` drill-down; use `--verbose` only when broad diagnostics are material.
