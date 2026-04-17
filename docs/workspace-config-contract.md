# Workspace Config Contract

This page defines the repo-owned config contract for Agentic Workspace.

Use it when the repository wants to keep one checked-in source of truth for lifecycle defaults and update intent without turning the workspace layer into a second workflow engine.

## Purpose

- Keep repo-owned customization outside `.agentic-workspace/`.
- Let the repo select a default preset and module update intent.
- Keep normal update execution behind `agentic-workspace`.

## File Location

- Repo-owned config lives at `agentic-workspace.toml` when present.
- Product-managed workflow and ownership state still lives under `.agentic-workspace/`.

## Formal Schemas

The config shapes are now also defined formally in:

- `src/agentic_workspace/contracts/schemas/workspace_config.schema.json`
- `src/agentic_workspace/contracts/schemas/workspace_local_override.schema.json`

Treat those schemas as development-time contract artifacts and drift checks.
`docs/workspace-config-contract.md` remains the canonical semantic explanation, while the schemas make the supported shape explicit for tooling and future integrations.

## V1 Schema

```toml
schema_version = 1

[workspace]
default_preset = "full" # memory | planning | full
agent_instructions_file = "AGENTS.md" # AGENTS.md | GEMINI.md
workflow_artifact_profile = "repo-owned" # repo-owned | gemini
improvement_latitude = "conservative" # none | reporting | conservative | balanced | proactive
optimization_bias = "balanced" # agent-efficiency | balanced | human-legibility

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
- `workspace.agent_instructions_file` sets the canonical root startup-entrypoint filename for workspace lifecycle surfaces.
- If `workspace.agent_instructions_file` is omitted, the workspace defaults to `AGENTS.md` and may conservatively autodetect one existing supported startup file in the target repo.
- `workspace.workflow_artifact_profile` tells the workspace which native runtime artifacts may exist before the repo-owned planning surfaces must be updated.
- `workspace.improvement_latitude` sets how much bounded repo-friction initiative is welcome by default when the repo already has evidence that a local hotspot is expensive to keep extending.
- `workspace.optimization_bias` sets whether durable outputs and rendered views should lean toward agent efficiency, balance, or human legibility when canonical truth would stay unchanged.
- Improvement-latitude policy and repo-friction evidence stay workspace-level shared surfaces; they should not become a third core module unless a future independent lifecycle clearly justifies it.
- `repo-owned` means do not rely on native runtime artifacts at all; keep durable state directly in `TODO.md` and `docs/execplans/`.
- `gemini` allows Gemini-style files such as `implementation_plan.md`, `task.md`, or `walkthrough.md` as local execution aids, but durable cross-agent state must still be mirrored back into `TODO.md` and `docs/execplans/` before review, handoff, or session end.
- `none` means do not perform opportunistic repo-friction reduction outside the explicitly requested work.
- `reporting` means notice and surface notable repo friction through bounded reporting or residue, but do not act on it without explicit direction.
- `conservative` means reduce friction only inside already-touched scope unless the work is explicitly promoted.
- `balanced` means one evidence-backed hotspot may justify bounded cleanup when proof and ownership stay inside the current lane.
- `proactive` means small standalone cleanup slices are allowed when evidence is explicit and the work still stays bounded by delegated judgment, proof, and ownership.
- `reporting` findings belong in derived report output, review output, or planning residue that already exists for the current slice; they must not create active work on their own.
- `agent-efficiency` means prefer terse durable outputs, compact residue, and low-prose rendered views when machine-readable state already carries the contract safely.
- `balanced` means keep outputs compact by default while preserving enough explanation for routine human inspection.
- `human-legibility` means prefer clearer explanatory rendering and slightly more legible residue when truth would remain unchanged.
- `optimization_bias` may influence reporting density, rendered human-view density, and residue style, but it must not change execution method, reasoning depth, delegated-judgment limits, proof requirements, or canonical state semantics.
- Use `agentic-workspace defaults --section improvement_latitude --format json` to inspect the shipped decision test for when friction reduction still counts as local means versus a changed task.
- Use `agentic-workspace defaults --section optimization_bias --format json` to inspect the shipped output/residue bias contract and its semantic guardrails.
- Use `agentic-workspace report --target ./repo --format json` to inspect both workspace-derived evidence and any compatible external hotspot artifacts the repo already maintains.
- When `agentic-workspace.toml` is absent, product defaults remain authoritative and the config report should say so rather than implying a live repo policy.
- Update policy is module-specific in v1; there is no separate public module upgrade entrypoint.
- Normal update execution stays behind `agentic-workspace`.
- Config does not own active state, long instructions, free-form prompts, or scheduler semantics.

## Delegated Workflow

Use [`docs/orchestrator-workflow-contract.md`](docs/orchestrator-workflow-contract.md) for the agent-agnostic planner/worker contract that sits on top of this config.

- `agentic-workspace.local.toml` may say whether internal delegation is supported or preferred, but it stays a capability/cost posture file, not a scheduler.
- `agentic-planning-bootstrap handoff --format json` is the canonical worker-facing contract for the active delegated slice.
- The same handoff should work whether the executor is another internal subagent, a local model, or an external CLI/API target.
- The repo does not prescribe executor brand, vendor, or model name in checked-in policy.

## Mixed-Agent Expansion Discipline

Future config expansion should stay narrow.

- Repo-owned checked-in config should continue to own only stable repo policy that deserves review and portability.
- Improvement latitude belongs here as repo policy because it states what bounded initiative is welcome, not how the agent must reason or delegate internally.
- Optimization bias belongs here as repo policy because it states how shared durable outputs should lean by default, not how an agent must analyze or execute internally.
- The main motivation for any mixed-agent extension is lower long-run token cost plus smoother switching across subscriptions, agent tools, and future local models.
- Runtime model choice, internal delegation strategy, and reasoning-depth selection should remain tool-owned unless a future surface can express them as capability-oriented hints without turning the repo into a scheduler.
- The product should prefer task/runtime inference first, config second, and explicit prompting last.
- If a future local override is added for machine-, account-, or cost-profile-specific preferences, it should stay optional, untracked, layered on top of repo policy, and observable through effective reporting.
- Local override is for environment asymmetry and capability/cost posture, not a broad hidden user-preference layer.
- Local/runtime preferences must not silently rewrite ownership boundaries, delegated-judgment limits, done criteria, or other checked-in repo semantics.
- Mixed-agent config should describe capability and cost posture rather than vendor-specific routing rules.
- Persisted checked-in state should remain the primary way to make agent switching cheap; config should only tune stable preferences and capability asymmetries around that core contract.
- Mixed-agent extensions should be justified by measured or repeatedly observed restart, handoff, or token-cost improvement rather than preference alone.
- Those extensions should also stay aligned with the product boundary in [`docs/design-principles.md`](docs/design-principles.md): help the agent do the job, do not script the job.
- If a future local-only confidence map is used to label delegation targets as stronger or weaker on a task class, keep it advisory and local-only; do not fold target confidence into repo-owned policy.

## Local Override Contract

The workspace now supports one optional local-only mixed-agent override file:

- `agentic-workspace.local.toml`

This file is for machine-, account-, and cost-profile-specific capability posture.
It is not part of checked-in repo policy and should stay gitignored.

Current supported fields:

```toml
schema_version = 1

[runtime]
supports_internal_delegation = true
strong_planner_available = true
cheap_bounded_executor_available = true

[handoff]
prefer_internal_delegation_when_available = true

[safety]
safe_to_auto_run_commands = false
requires_human_verification_on_pr = true

[delegation_targets.fast_docs]
strength = "weak" # strong | medium | weak
confidence = 0.58
task_fit = ["bounded-docs", "narrow-tests"]
execution_methods = ["cli"] # internal | cli | api

[delegation_targets.primary_planner]
strength = "strong"
confidence = 0.92
execution_methods = ["internal", "api"]
```

Rules:

- The file is optional.
- Supported fields are intentionally narrow and capability-shaped.
- The local file may affect effective reporting, but it must not silently change repo-owned semantics.
- The current workspace surface reports these values; it does not turn them into scheduler control.
- `delegation_targets` is a local-only advisory inventory of available executors.
- Target names are local aliases, not checked-in repo policy.
- `strength` is a coarse capability hint, not a promise about all task classes.
- `confidence` is optional and should stay revisable by experience instead of being treated as stable truth.
- `task_fit` is optional and should name only the narrow classes of bounded work the local user actually trusts that target to handle cheaply.
- `execution_methods` tells the orchestrator whether the target is reachable through internal delegation, a CLI runner, an API runner, or more than one of those paths.
- These hints may influence handoff detail and review burden, but they must not become automatic routing policy.

## Effective Config

Use:

```bash
agentic-workspace config --target ./repo --format json
agentic-workspace defaults --section workflow_artifact_adapters --format json
```

That surface reports:

- whether `agentic-workspace.toml` exists
- whether repo policy is currently authoritative or defaults-only
- the resolved default preset
- the resolved canonical startup-entrypoint filename plus whether it came from repo config, autodetection, product defaults, or an explicit CLI override
- the effective improvement-latitude mode plus whether it came from repo config or product defaults
- the effective optimization-bias mode plus whether it came from repo config or product defaults
- the effective per-module update policy
- whether each module's `UPGRADE-SOURCE.toml` metadata matches the resolved policy
- the current mixed-agent reporting boundary: repo-policy source, reserved local-override status, and the fact that runtime orchestration remains tool-owned
- the effective local mixed-agent posture when `agentic-workspace.local.toml` is present
- the configured local delegation target profiles and their derived advisory handoff/review hints
- the effective workflow-artifact adapter profile and its sync rule

If mixed-agent policy grows beyond the v1 surface, effective reporting should also make clear:

- what comes from checked-in repo policy
- what comes from optional local override
- what comes from product defaults
- what is inferred from the current runtime or task shape

Use `agentic-workspace defaults --section delegation_posture --format json` to see how the current config and local override resolve into the current delegation posture.
Use `agentic-workspace defaults --section improvement_latitude --format json` to inspect the bounded initiative modes and their interaction with repo-friction evidence.
Use `agentic-workspace defaults --section optimization_bias --format json` to inspect which output/residue surfaces the current bias may influence without changing semantics.

When runtime inference materially changes behavior, reporting should make that inference auditable rather than hidden.

Do not add broader mixed-agent config without a reporting surface that preserves this distinction.

## Upgrade Semantics

- `agentic-workspace upgrade` is the normal update path.
- The workspace wrapper syncs module `UPGRADE-SOURCE.toml` metadata to the resolved repo policy before or alongside managed-surface refresh.
- `status` and `doctor` warn when repo-owned update intent and module metadata drift apart.
- Agents should treat `agentic-workspace.toml` as the checked-in source of lifecycle defaults and update intent, then run the workspace wrapper rather than updating modules directly.
