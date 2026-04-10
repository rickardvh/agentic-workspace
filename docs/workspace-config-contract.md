# Workspace Config Contract

This page defines the repo-owned config contract for Agentic Workspace.

Use it when the repository wants to keep one checked-in source of truth for lifecycle defaults and update intent without turning the workspace layer into a second workflow engine.

## Purpose

- Keep repo-owned customization outside `.agentic-workspace/`.
- Let the repo select a default preset and module update intent.
- Keep normal update execution behind `agentic-workspace`.

## File Location

- Repo-owned config lives at `agentic-workspace.toml`.
- Product-managed workflow and ownership state still lives under `.agentic-workspace/`.

## V1 Schema

```toml
schema_version = 1

[workspace]
default_preset = "full" # memory | planning | full

[update.modules.planning]
source_type = "git" # git | local
source_ref = "git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning"
source_label = "agentic-planning-bootstrap monorepo master"
recommended_upgrade_after_days = 30

[update.modules.memory]
source_type = "git" # git | local
source_ref = "git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/memory"
source_label = "agentic-memory-bootstrap monorepo master"
recommended_upgrade_after_days = 30
```

## Rules

- `schema_version` is required.
- Missing fields use product defaults.
- `workspace.default_preset` affects `init` and `prompt` only when the user does not pass `--preset` or `--modules`.
- Update policy is module-specific in v1; there is no separate public module upgrade entrypoint.
- Normal update execution stays behind `agentic-workspace`.
- Config does not own active state, long instructions, free-form prompts, or scheduler semantics.

## Effective Config

Use:

```bash
agentic-workspace config --target ./repo --format json
```

That surface reports:

- whether `agentic-workspace.toml` exists
- the resolved default preset
- the effective per-module update policy
- whether each module's `UPGRADE-SOURCE.toml` metadata matches the resolved policy

## Upgrade Semantics

- `agentic-workspace upgrade` is the normal update path.
- The workspace wrapper syncs module `UPGRADE-SOURCE.toml` metadata to the resolved repo policy before or alongside managed-surface refresh.
- `status` and `doctor` warn when repo-owned update intent and module metadata drift apart.
- Agents should treat `agentic-workspace.toml` as the checked-in source of lifecycle defaults and update intent, then run the workspace wrapper rather than updating modules directly.
