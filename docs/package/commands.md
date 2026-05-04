# Command Map

This page is a human navigation map for the shipped `agentic-workspace` command surface. For exact option shapes, see the generated [CLI commands reference](../reference/cli-commands.md) and [CLI option groups](../reference/cli-option-groups.md).

## Ordinary Host-Repo Commands

| Command | Use when |
| --- | --- |
| `agentic-workspace init --target ./repo --preset memory` | bootstrap the smallest common durable-knowledge install |
| `agentic-workspace start --target ./repo --format json` | begin ordinary work from compact startup context |
| `agentic-workspace summary --target ./repo --format json` | inspect active planning, handoff, and continuation state |
| `agentic-workspace preflight --target ./repo --format json` | bundle startup defaults, config, and active state for takeover |
| `agentic-workspace implement --target ./repo --changed <paths> --format json` | inspect bounded changed-path context, path authority, projection shape, and proof routes before editing |
| `agentic-workspace proof --target ./repo --changed <paths> --format json` | choose validation and proof routes for changed paths |
| `agentic-workspace report --target ./repo --format json` | inspect combined module health, warnings, and next actions |
| `agentic-workspace planning --target ./repo --format json` | inspect planning lifecycle guidance before creating or mutating checked-in planning state |
| `agentic-workspace doctor --target ./repo --format json` | diagnose missing, stale, or conflicting installed surfaces |

## Planning Lifecycle Commands

| Command | Use when |
| --- | --- |
| `agentic-planning-bootstrap new-plan --id <id> --title <title> --target ./repo --activate --format json` | create and register a schema-backed execplan scaffold for active planned work |
| `agentic-planning-bootstrap promote-to-plan <item-id> --target ./repo --format json` | promote one selected planning item or lane into active checked-in execution state |
| `agentic-planning-bootstrap archive-plan <plan> --target ./repo --format json` | archive a completed plan after proof, intent satisfaction, closeout, and residue routing are explicit |

`new-plan` creates a valid scaffold, not a finished implementation contract. Tighten goal, non-goals, intent continuity, execution bounds, touched paths, validation commands, completion criteria, and assurance before implementation.

For ordered roadmap lanes, promote and complete one lane at a time. A lane may need multiple execplans, but one execplan should not span unrelated lanes.

## Workspace Lifecycle Mutation Commands

| Command | Use when |
| --- | --- |
| `init` | set up a repo from a preset, choosing conservative install or adopt behavior |
| `install` | add selected modules explicitly |
| `upgrade --dry-run` | preview managed-surface refreshes |
| `upgrade` | apply managed-surface refreshes |
| `uninstall --dry-run` | preview conservative removal |
| `uninstall` | remove managed surfaces when ownership is clear |

## Routing And Inspection Commands

| Command | Use when |
| --- | --- |
| `defaults` | inspect policy, startup, validation, and preset defaults |
| `config` | inspect resolved repo and local workspace posture |
| `ownership` | answer which surface owns a path or concern |
| `modules` | list available or installed modules |
| `skills` | list registered package or repo skills |
| `status` | summarize installed module state |

## Advanced Diagnostics

| Command | Use when |
| --- | --- |
| `setup` | inspect bounded post-bootstrap setup findings |
| `reconcile` | compare planning state with optional external work evidence |
| `external-intent refresh-github` | refresh optional GitHub issue evidence through the adapter |
| `note-delegation-outcome` | record local-only delegation calibration data |

The deeper model for these groups is described in [Lifecycle and context commands](lifecycle.md).

## Exact Result Shapes

- `start --format json`: [Startup context](../reference/startup-context.md).
- `preflight --format json`: [Preflight policy](../reference/preflight-policy.md) plus startup, config, and planning state projections.
- `report --format json`: [Workspace report](../reference/workspace-report.md).
- `proof --format json`: [Proof selection rules](../reference/proof-selection-rules.md) and [Proof routes manifest](../reference/proof-routes-manifest.md).
- `config --format json`: [Workspace config](../reference/workspace-config.md) and [Workspace local override](../reference/workspace-local-override.md).
- generated adapter and operation contracts: [Operation contracts](../reference/operation-contracts.md), [Operation primitives](../reference/operation-primitives.md), and [Command adapter generation](../reference/command-adapter-generation.md).
