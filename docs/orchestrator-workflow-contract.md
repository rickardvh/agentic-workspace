# Orchestrator Workflow Contract

This page defines the compact planner-to-worker workflow for delegated execution.

Use it when a stronger planner should shape a bounded slice once and a smaller or separate executor should implement it without broad rereads.

## Purpose

- Keep delegated execution agent-agnostic.
- Reuse the existing local mixed-agent posture instead of inventing a scheduler.
- Derive worker handoff from checked-in planning state instead of handwritten prompts.
- Keep durable continuity in planning surfaces even when execution happens in another runtime.

## Surfaces

Use:

```bash
agentic-workspace config --target ./repo --format json
agentic-workspace note-delegation-outcome --target ./repo --delegation-target <target> --task-class <class> --outcome <success|mixed|failed>
agentic-workspace defaults --section relay --format json
agentic-planning-bootstrap handoff --format json
```

Use the config surface first to inspect whether the local environment reports:

- internal delegation support
- strong planner availability
- cheap bounded executor availability
- preference for internal delegation when available
- any configured local delegation target profiles with coarse strength, confidence, task-fit, and execution-method hints
- any local delegation outcome evidence and derived tuning suggestions for those targets

Those settings live in `agentic-workspace.local.toml`.
They are local capability and cost posture only.
They must not rewrite repo-owned planning semantics.
If delegation target profiles are present, use them only as advisory input for handoff detail, review burden, and whether a target is even plausible for the current bounded slice.
If local outcome evidence is present, use it only to tune those advisory hints over time; it must not become hidden scheduler policy.

Use the relay selector for the stable planner/implementer rule and the planning handoff command for the active delegated slice contract.

## Rule

- Let a stronger planner shape the compact contract once when that is cheaper than repeated re-derivation.
- Keep the handoff agent-agnostic: internal delegation, local CLI/API execution, or another vendor executor may all use the same checked-in contract.
- Prefer internal delegation only when the local posture says it is available and desirable.
- If local delegation target profiles exist, use them to reduce blind guessing about target capability, but keep the checked-in worker handoff canonical.
- Otherwise use the same handoff contract with any external CLI/API path that can preserve the checked-in boundaries.
- Stay direct when delegation would cost more than it saves.

## Worker Handoff Shape

`agentic-planning-bootstrap handoff --format json` is the compact delegated-worker surface.

It should give the worker:

- active task and parent lane
- requested outcome
- hard constraints
- agent-local latitude
- immediate next action
- completion criteria
- explicit read-first refs
- owned write scope
- proof expectations
- tool verification
- continuation owner
- default worker and orchestrator boundaries

The worker should be able to continue from that contract without broad startup rereads.

## Default Boundary

By default the worker may own:

- bounded implementation inside the assigned write scope
- the narrow validation named in the handoff
- checked-in updates inside owned surfaces when explicitly assigned
- cleanup and commit only when explicitly assigned and still bounded

By default the worker must not own:

- roadmap routing
- issue closure
- lane reshaping
- repo-wide policy changes

The orchestrator retains those concerns unless the delegated slice says otherwise explicitly.

## External Delegation

External delegation is valid.

The workflow does not require the worker to be another subagent inside the same tool.
If the executor is another local model, remote vendor, or CLI/API runner, the same handoff contract should still apply.

The workflow contract should therefore describe:

- what must remain true
- what the worker may change
- what must stop and escalate

It should not prescribe a specific executor brand, API, or model name.

## Relationship To Other Docs

- Use `docs/capability-aware-execution.md` for the task-shape decision about whether delegation is worthwhile at all.
- Use `docs/delegation-posture-contract.md` for the mixed-agent posture and config controls that influence delegation preference.
- Use `docs/intent-contract.md` for the underlying active planning record and projections that feed the delegated handoff.
- Use `docs/execplans/README.md` for the authoring rules behind the planning state the handoff derives from.
