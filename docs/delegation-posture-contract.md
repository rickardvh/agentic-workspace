# Delegation Posture Contract

This page defines the bounded mixed-agent posture for task-by-task routing between direct execution, planner/implementer/validator splitting, and stronger-planner escalation.

Use it when you want the repo to make delegation preference queryable without turning config into a scheduler.

## Purpose

- Make delegation posture explicit and inspectable across sessions.
- Keep task-shape routing separate from delegated judgment about requested outcomes.
- Let config influence posture while keeping runtime orchestration tool-owned.

## Rule

- Prefer direct execution when the task is cheap and self-sufficient.
- Prefer a planner/implementer/validator split when a compact handoff or bounded execplan reduces cost or risk.
- Escalate to a stronger planner when the current path is no longer safe or the task shape would otherwise force re-derivation.
- Do not silently widen the requested outcome.

## Canonical Shape

Use `agentic-workspace defaults --section delegation_posture --format json` for the machine-readable contract surface.
Use `agentic-workspace defaults --section relay --format json` when the question is how a strong planner hands the compact contract to a cheap implementer, especially when routed Memory should supply durable context first.

```json
{
  "delegation_posture": {
    "canonical_doc": "docs/delegation-posture-contract.md",
    "command": "agentic-workspace defaults --section delegation_posture --format json",
    "rule": "Use the effective mixed-agent posture to decide whether to keep work direct, split it into planner/implementer/validator subtasks, or escalate to a stronger planner.",
    "preferred_split": [
      "planner",
      "implementer",
      "validator"
    ],
    "config_controls": [
      "agentic-workspace.local.toml runtime.supports_internal_delegation",
      "agentic-workspace.local.toml runtime.strong_planner_available",
      "agentic-workspace.local.toml runtime.cheap_bounded_executor_available",
      "agentic-workspace.local.toml handoff.prefer_internal_delegation_when_available"
    ],
    "secondary": [
      "Do not treat config as a scheduler.",
      "Do not delegate when the task stays cheap and direct.",
      "Do not silently rewrite ends."
    ]
  }
}
```

## Concise Text Output

The text form should stay short and stable:

- `doc: docs/delegation-posture-contract.md`
- `command: agentic-workspace defaults --section delegation_posture --format json`
- `rule: Use the effective mixed-agent posture to decide whether to keep work direct, split it, or escalate.`
- `preferred split: planner -> implementer -> validator`
- `config controls: agentic-workspace.local.toml runtime and handoff posture fields`

## Relationship To Other Docs

- Use [`docs/delegated-judgment-contract.md`](docs/delegated-judgment-contract.md) for the boundary between human-set outcomes and agent-local means.
- Use [`docs/workspace-config-contract.md`](docs/workspace-config-contract.md) for the repo-owned config and local override posture that influence delegation preference.
- Use [`docs/capability-aware-execution.md`](docs/capability-aware-execution.md) for the broader capability-fit decision tree.
