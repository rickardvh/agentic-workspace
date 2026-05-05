# Cold-Start Protocol

This protocol defines the fastest path for an agent to reach an actionable state in this workspace.

## 1. Protocol Objective

Orient and reach the first concrete `Immediate Next Action` in **under 3 turns**, without broad rereading of documentation prose.

## 2. High-Efficiency Entry Path

### Turn 1: Takeover Context

Query the one-call startup, config, and active-state bundle.

- **Command**: `agentic-workspace preflight --format json`
- **Output**: Bundles startup guidance, resolved config, and active planning state.

### Turn 2: Recover Active State Or Changed-Path Context

Query the current execution context, or use changed paths when the task already has a bounded surface.

- **Command**: `agentic-workspace summary --format json`
- **Output**: Identifies the active plan, current milestone, and any blockers.
- **Alternative command**: `agentic-workspace implement --profile tiny --changed <paths> --format json`
- **Output**: Returns bounded implementer context, proof routes, path authority, and projection shape for the changed surface.

### Turn 3: Activate and Execute

Load only the compact contract needed for the next action.

- **Command**: `agentic-workspace report --target ./repo --format json`
- **Action**: Read the relevant `planning_record`, `resumable_contract`, `handoff_contract`, or report section. Open raw planning files only when compact output points there or you are maintaining the checked-in planning record directly.

## 3. Machine-Readable Anchors

To support this protocol, the repository maintains the following machine-readable anchors:

- **`.agentic-workspace/config.toml`**: Authoritative entrypoint and capability posture.
- **`.agentic-workspace/planning/agent-manifest.json`**: Role-based mapping of documentation to agentic intents.
- **`agentic-workspace preflight --format json`**: First ordinary takeover query; use it when startup, config, and active state all matter.
- **`agentic-workspace summary --format json`**: Compact view over active work, roadmap promotion signals, canonical plan references, proof expectations, and continuation state.
- **`.agentic-workspace/planning/state.toml`**: Planning-managed state file containing repo-owned active items and roadmap content. Open it only when the compact summary points there or you are maintaining planning state directly.
- **`.agentic-workspace/planning/execplans/*.plan.json`**: Canonical active execplan records for planned lanes or bounded work.
- **`.agentic-workspace/planning/execplans/*.md`**: Human-readable compatibility views or fallback prose when no machine-first plan sidecar is present.

## 4. When to Diverge

Agents should fall back to the [Routing and Entry Contract](routing-contract.md) (Turn-heavy prose) only when:

- The "Cold Start" queries fail or return ambiguous state.
- The task requires deep architectural context not captured in the active plan.
- The agent is performing a repository-wide refactor or major structural change.
