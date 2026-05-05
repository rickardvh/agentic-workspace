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
- Down-route to a cheaper bounded executor when a strong target would be overqualified for mechanical work and proof remains clear.
- Do not silently widen the requested outcome.

## Canonical Shape

Use `agentic-workspace defaults --section delegation_posture --format json` for the machine-readable contract surface.
Use `agentic-workspace defaults --section relay --format json` when the question is how a strong planner hands the compact contract to a bounded executor, especially when routed Memory should supply durable context first.
Use `agentic-planning handoff --format json` when the question is what the active delegated worker actually needs to read, own, prove, and escalate.

```json
{
  "delegation_posture": {
    "canonical_doc": ".agentic-workspace/docs/delegation-posture-contract.md",
    "command": "agentic-workspace defaults --section delegation_posture --format json",
    "rule": "Use the effective mixed-agent posture to decide whether to keep work direct, split it into planner/implementer/validator subtasks, or escalate to a stronger planner.",
    "preferred_split": [
      "planner",
      "implementer",
      "validator"
    ],
    "config_controls": [
      ".agentic-workspace/config.local.toml runtime.supports_internal_delegation",
      ".agentic-workspace/config.local.toml runtime.strong_planner_available",
      ".agentic-workspace/config.local.toml runtime.cheap_bounded_executor_available",
      ".agentic-workspace/config.local.toml handoff.prefer_internal_delegation_when_available",
      ".agentic-workspace/config.local.toml delegation_targets.<target>.*",
      ".agentic-workspace/delegation-outcomes.json"
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

- `doc: .agentic-workspace/docs/delegation-posture-contract.md`
- `command: agentic-workspace defaults --section delegation_posture --format json`
- `rule: Use the effective mixed-agent posture to decide whether to keep work direct, split it, or escalate.`
- `preferred split: planner -> implementer -> validator`
- `config controls: .agentic-workspace/config.local.toml runtime, handoff, optional delegation-target posture fields, and local delegation outcome evidence`

## Capability Posture

When bounded work already has a checked-in execplan, let the handoff carry one compact capability posture packet:

- `execution class`: `boundary-shaping`, `reasoning-heavy`, `mixed`, or `mechanical-follow-through`
- `recommended strength`: `strong`, `medium`, or `weak`
- `preferred location`: `local`, `external`, or `either`
- `delegation friendly`: `yes`, `no`, or another short advisory cue
- `strong external reasoning`: `avoid`, `allowed`, or `preferred`
- `work shape`: `direct`, `bounded`, `lane`, or `epic`
- `proof burden`: `obvious`, `non-obvious`, or `high`
- `risk flags`: compact structural reasons that raise proof or review burden
- `inspection evidence required`: context the agent must inspect before choosing a target
- `classification authority`: the structural signal source used for routing
- `self-assessment authority`: always advisory-only
- `why`: one sentence explaining why the posture fits the slice

Keep this posture advisory. The runtime or local layer may resolve it against configured target profiles, but the checked-in plan must not hard-bind one vendor, machine, or exact target by default.

Model self-confidence is not a routing authority. It may influence handoff detail, review burden, and local confidence tuning, but it cannot override forbidden task classes, capability mismatch, high proof burden, escalation requirements, or human-control mode.

Local target profiles may optionally describe model-level fit with `model_family`, `provider`, `context_capacity`, `reasoning_profile`, `cost_class`, `latency_class`, `safe_task_classes`, `forbidden_task_classes`, `escalation_target`, `confidence_source`, `last_evaluation`, and `human_control_modes`. These fields belong in `.agentic-workspace/config.local.toml`; they are local advisory evidence, not shared repo policy.

## Capability Mismatch

Target strength is a fit signal, not a status ranking.

- If a weak target is below the recommended strength for boundary-shaping or reasoning-heavy work, it should escalate before execution.
- If a strong target is above the recommended strength for mechanical-follow-through work, it should down-route when a cheaper configured target fits and validation remains narrow.
- If no safe up-route or down-route exists, stay with the current executor and make the reason visible.

Delegation posture controls how this happens:

- `off`: do not force delegation; stay direct only if the current executor can satisfy the task.
- `manual`: prepare a compact handoff and stop.
- `suggest`: recommend the better-fit target or stronger planner, but do not execute automatically.
- `auto`: route automatically only inside local safety and target-profile limits.

Saving tokens is a valid goal only after task fit, proof expectations, and review trust remain safe.

## Capability Handoff Packets

Use capability-aware handoff packets when the runtime route is no longer simple direct execution:

- `weak_target_escalation`: an underfit target must stop and hand off to a stronger planner, human, or configured escalation target.
- `strong_target_downrouting`: a strong target should hand mechanical work to a cheaper bounded executor when proof remains clear.
- `manual_human_clarification`: the next decision depends on human intent, ownership boundary, or acceptable autonomy.
- `strong_reviewer_fallback`: cheap implementation may proceed, but review or proof interpretation needs stronger reasoning.
- `no_safe_route`: no configured target satisfies capability, proof, and human-control requirements.

Each packet must carry task shape, route reason, inspected context, allowed write scope, proof expectations, stop conditions, and the return contract. The receiver should not need chat history to understand what it owns.

## Relationship To Other Docs

- Use [`execution-flow-contract.md`](execution-flow-contract.md) for the delegated-judgment boundary between human-set outcomes and agent-local means.
- Use [`.agentic-workspace/docs/lifecycle-and-config-contract.md`](lifecycle-and-config-contract.md) for the repo-owned config and local override posture that influence delegation preference.
- Use [`.agentic-workspace/docs/capability-aware-execution.md`](.agentic-workspace/docs/capability-aware-execution.md) for the broader capability-fit decision tree.
- Use [`orchestrator-workflow-contract.md`](orchestrator-workflow-contract.md) for the delegated planner-to-worker workflow and the active handoff surface.

