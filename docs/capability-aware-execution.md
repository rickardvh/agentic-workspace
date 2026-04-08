# Capability-Aware Execution

This document defines the planning contract for matching task shape to execution capability.

Use it when deciding whether a task should stay a cheap direct task, be promoted into a checked-in execplan, be delegated to a smaller implementer after planning, or stop for escalation.

This contract is task-shape based. It does not depend on vendor-specific model names.

## Purpose

Planning already distinguishes:

- inactive future candidates in `ROADMAP.md`
- active direct tasks in `TODO.md`
- active planned work in `docs/execplans/`

What this document adds is capability fit:

- how much execution support the task actually needs
- whether the cheap path is still safe
- whether stronger planning is warranted first
- whether delegation is likely to save cost
- when an agent should stop and escalate instead of continuing wastefully

## Task-Shape Dimensions

Judge capability fit using the smallest set of dimensions that materially affect safe execution:

- complexity: how many moving parts or transformations the task contains
- ambiguity: how much interpretation is still required before implementation can begin safely
- validation burden: how much proving work is needed to know the result is correct
- cross-surface breadth: how many ownership surfaces, packages, or contracts the task crosses
- architecture sensitivity: how easily the task could distort a stable boundary or public contract
- handoff or restart risk: how much execution state would be lost if another contributor had to continue
- acceptable autonomy: how much independent action is safe before explicit confirmation or escalation

The more of these dimensions rise at once, the less suitable the task is for cheap direct execution.

## Recommendation Categories

Use the categories below as durable recommendations, not as hard runtime enforcement.

### Cheap Direct Execution

Use this when:

- the task is local
- ambiguity is low
- validation is obvious and narrow
- the TODO row can stay self-sufficient

Recommended shape:

- keep the task in `TODO.md`
- use the cheapest safe execution path
- do not add a plan just because a stronger agent exists

### Direct Task, Medium Reasoning

Use this when:

- the task is still one coherent pass
- some interpretation is needed
- the cheap path is plausible but not trivial
- a checked-in execplan would cost more than it saves

Recommended shape:

- keep the task direct
- spend moderate reasoning on the implementation
- promote only if ambiguity, validation, or handoff burden keeps growing

### Stronger Planning First

Use this when:

- implementation should not start from chat context alone
- ambiguity, breadth, or validation burden is high enough that the task is no longer self-sufficient as a TODO row
- restart or handoff would otherwise force re-derivation

Recommended shape:

- promote into `docs/execplans/`
- write the compact execution contract first
- then implement from that checked-in plan

### Autopilot-Suitable

Use this when:

- the task is already bounded by an execplan or equivalent active milestone
- touched paths are narrow enough to keep execution compact
- validation is obvious enough to prove the slice without broader redesign

Recommended shape:

- execute one bounded milestone
- keep the active plan current
- stop once the milestone completes or blocks

### Delegation-Friendly

Use this when:

- a stronger planner can cheaply reduce ambiguity for a smaller implementer
- the handoff artifact is likely to cost less than re-deriving the task
- the execution slice after planning is narrow and mechanically clear

Recommended shape:

- let the stronger path write the compact plan, classification, or handoff
- let the cheaper path implement if the environment supports delegation
- keep delegation optional; the same task must still be explainable for a single agent operating alone

### Stop And Escalate

Use this when:

- ambiguity remains too high
- architecture sensitivity is too high
- the safe validation story is unknown
- the current execution path lacks the capabilities needed to continue safely
- proceeding would likely create churn, drift, or wasted retries

Recommended shape:

- stop rather than guessing
- escalate to a stronger planner, clearer human direction, or a tighter checked-in contract
- record the blocker or missing capability in the active plan when the task is already promoted

## Relation To Direct Tasks And Execplans

Capability fit sharpens the existing planning boundary; it does not replace it.

- Keep work direct when one coherent pass can finish it and the task remains self-sufficient in `TODO.md`.
- Promote into an execplan when safe continuation depends on more than the TODO row can carry.
- Use stronger planning first when that checked-in artifact is likely to reduce rediscovery, restart cost, or coordination risk more than it costs to write.

Do not promote work into an execplan merely because a stronger model exists.

Do not keep work direct merely because a smaller model might manage it if the current task shape no longer makes that safe.

## Delegation And Model Neutrality

This contract is intentionally neutral about specific tools, models, or vendors.

It should remain useful whether the environment offers:

- one agent only
- stronger and cheaper models
- subagents or delegate workers
- no delegation support at all

The durable question is not which named model to use.
The durable question is what task shape the current execution path can safely support.

## Practical Test

Ask these questions in order:

1. Can this finish safely as one coherent direct task?
2. If yes, is the cheapest safe path enough, or does it need medium reasoning?
3. If no, would a compact checked-in execplan reduce enough ambiguity or restart cost to justify itself?
4. If a stronger planner is available, would planning first let a cheaper implementer succeed safely?
5. If not, should execution stop and escalate instead of continuing?

That is the capability-aware execution contract for the first planning slice.
