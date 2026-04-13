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

## Mixed-Agent Expansion Discipline

Future config expansion should stay narrow.

- Repo-owned checked-in config should continue to own only stable repo policy that deserves review and portability.
- The main motivation for any mixed-agent extension is lower long-run token cost plus smoother switching across subscriptions, agent tools, and future local models.
- Runtime model choice, internal delegation strategy, and reasoning-depth selection should remain tool-owned unless a future surface can express them as capability-oriented hints without turning the repo into a scheduler.
- The product should prefer task/runtime inference first, config second, and explicit prompting last.
- If a future local override is added for machine-, account-, or cost-profile-specific preferences, it should stay optional, untracked, layered on top of repo policy, and observable through effective reporting.
- Local override is for environment asymmetry and capability/cost posture, not a broad hidden user-preference layer.
- Local/runtime preferences must not silently rewrite ownership boundaries, delegated-judgment limits, done criteria, or other checked-in repo semantics.
- Mixed-agent config should describe capability and cost posture rather than vendor-specific routing rules.
- Persisted checked-in state should remain the primary way to make agent switching cheap; config should only tune stable preferences and capability asymmetries around that core contract.
- Mixed-agent extensions should be justified by measured or repeatedly observed restart, handoff, or token-cost improvement rather than preference alone.

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
- the current mixed-agent reporting boundary: repo-policy source, reserved local-override status, and the fact that runtime orchestration remains tool-owned

If mixed-agent policy grows beyond the v1 surface, effective reporting should also make clear:

- what comes from checked-in repo policy
- what comes from optional local override
- what comes from product defaults
- what is inferred from the current runtime or task shape

When runtime inference materially changes behavior, reporting should make that inference auditable rather than hidden.

Do not add broader mixed-agent config without a reporting surface that preserves this distinction.

## Upgrade Semantics

- `agentic-workspace upgrade` is the normal update path.
- The workspace wrapper syncs module `UPGRADE-SOURCE.toml` metadata to the resolved repo policy before or alongside managed-surface refresh.
- `status` and `doctor` warn when repo-owned update intent and module metadata drift apart.
- Agents should treat `agentic-workspace.toml` as the checked-in source of lifecycle defaults and update intent, then run the workspace wrapper rather than updating modules directly.
