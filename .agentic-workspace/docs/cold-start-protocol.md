# Cold-Start Protocol

This protocol defines the fastest path for an agent to reach an actionable state in this workspace.

## 1. Protocol Objective

Orient and reach the first concrete `Immediate Next Action` in **under 3 turns**, without broad rereading of documentation prose.

## 2. High-Efficiency Entry Path

### Turn 1: Orient and Load Policy

Query the workspace configuration and startup defaults.

- **Command**: `agentic-workspace defaults --section startup --format json`
- **Output**: Defines the entrypoint (usually `AGENTS.md`) and the roles of key planning surfaces.

### Turn 2: Recover Active State

Query the current execution context and milestone status.

- **Command**: `agentic-workspace summary --format json`
- **Output**: Identifies the active plan, current milestone, and any blockers.

### Turn 3: Activate and Execute

Load the active plan's compact contract and execute the next action.

- **Command**: `agentic-workspace report --target ./repo --format json`
- **Action**: Read the `Immediate Next Action` from the identified active plan and begin execution.

## 3. Machine-Readable Anchors

To support this protocol, the repository maintains the following machine-readable anchors:

- **`.agentic-workspace/config.toml`**: Authoritative entrypoint and capability posture.
- **`.agentic-workspace/planning/agent-manifest.json`**: Role-based mapping of documentation to agentic intents.
- **`.agentic-workspace/planning/state.toml` / `.agentic-workspace/planning/execplans/*.md`**: Contract-shaped execution surfaces with stable headings for summary extraction.

## 4. When to Diverge

Agents should fall back to the [Routing and Entry Contract](routing-contract.md) (Turn-heavy prose) only when:

- The "Cold Start" queries fail or return ambiguous state.
- The task requires deep architectural context not captured in the active plan.
- The agent is performing a repository-wide refactor or major structural change.
