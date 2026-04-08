# Capability-Aware Execution

This document defines the planning contract for matching task shape to execution capability.

Use it when deciding whether a task should stay a cheap direct task, be promoted into a checked-in execplan, be delegated to a smaller implementer after planning, or stop for escalation.

This contract is task-shape based. It does not depend on vendor-specific model names.

## Operating Stance

This contract is advisory and tool-agnostic.

Use it to shape work, not to fight assistants that already perform automatic capability selection well.

The normal goal is quiet execution:

- proceed directly when the current path is already safe
- promote, split, or tighten the task when that would reduce ambiguity
- delegate only when a compact handoff is likely to cost less than re-derivation
- escalate only when continuing would likely waste effort or distort a stable boundary

Do not turn this contract into a noisy layer of repeated prompts to switch models, raise reasoning effort, or hunt for a stronger executor by name.
If the surrounding tool already chooses execution capability automatically, keep this contract focused on checked-in task shape, planning, validation, and escalation discipline.

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
- let the environment auto-select execution capability when it already does that well
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
- prefer silent shaping of the task over interrupting the user with executor-selection advice
- promote only if ambiguity, validation, or handoff burden keeps growing

### Stronger Planning First

Use this when:

- implementation should not start from chat context alone
- ambiguity, breadth, or validation burden is high enough that the task is no longer self-sufficient as a TODO row
- restart or handoff would otherwise force re-derivation

Recommended shape:

- promote into `docs/execplans/`
- write the compact execution contract first
- use the plan to reduce ambiguity, validation breadth, or restart cost before asking for more execution capability
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
- do not assume the user should have to choose the delegating or implementing executor explicitly

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

## Silent Shaping And Non-Interference

Prefer changing the work shape over interrupting execution with capability advice.

Examples of silent shaping:

- split a broad task into a bounded direct slice plus follow-up
- promote the work into an execplan before implementation starts
- narrow touched paths and validation scope
- make handoff state explicit enough that a cheaper implementer can continue safely

Only surface explicit escalation when the current path is no longer safe or the missing capability cannot be reduced by better task shaping.

When the assistant or tool already performs automatic capability selection:

- do not override it with vendor-specific instructions
- do not duplicate its routing logic in repo policy
- do use this contract to decide whether the work should stay direct, be planned first, be delegated, or stop

Capability-aware execution should make tool-local routing easier, not noisier.

## Relation To Direct Tasks And Execplans

Capability fit sharpens the existing planning boundary; it does not replace it.

- Keep work direct when one coherent pass can finish it and the task remains self-sufficient in `TODO.md`.
- Promote into an execplan when safe continuation depends on more than the TODO row can carry.
- Use stronger planning first when that checked-in artifact is likely to reduce rediscovery, restart cost, or coordination risk more than it costs to write.

Do not promote work into an execplan merely because a stronger model exists.

Do not keep work direct merely because a smaller model might manage it if the current task shape no longer makes that safe.

When stronger capability keeps seeming necessary, prefer asking whether the task should be decomposed, bounded, or routed differently before treating stronger execution as the default answer.

## Delegation And Model Neutrality

This contract is intentionally neutral about specific tools, models, or vendors.

It should remain useful whether the environment offers:

- one agent only
- stronger and cheaper models
- subagents or delegate workers
- no delegation support at all

The durable question is not which named model to use.
The durable question is what task shape the current execution path can safely support.

## Complexity-Reduction Feedback

Repeated stronger-capability needs are not only routing outcomes.
They are also product signals.

When the same subsystem or workflow repeatedly needs stronger planning, stronger reasoning, or repeated escalation, treat that as evidence that the repo could become cheaper to execute over time.

Common complexity-reduction targets include:

- decomposition that keeps direct tasks smaller and more local
- clearer validation lanes
- tighter canonical docs
- cleaner ownership boundaries
- better runbooks, skills, or scripts for mechanical steps
- improved planning templates or promotion rules

Route the signal to the narrowest durable surface that fits:

- active execplan when the refinement belongs to work already in progress
- `TODO.md` only when the immediate active task can absorb the improvement directly
- `docs/reviews/` when the right remediation still needs bounded analysis
- `ROADMAP.md` when the improvement is plausible future work but not active now
- memory or canonical docs only when the signal has stabilized into durable guidance rather than future-work tracking

The long-term goal is not only to pick the right capability for today's task.
It is to make more future tasks safe for cheaper execution paths.

## Practical Test

Ask these questions in order:

1. Can this finish safely as one coherent direct task?
2. If yes, is the cheapest safe path enough, or does it need medium reasoning?
3. If no, would a compact checked-in execplan reduce enough ambiguity or restart cost to justify itself?
4. If a stronger planner is available, would planning first let a cheaper implementer succeed safely?
5. If stronger capability still seems necessary, can better decomposition, validation, or checked-in guidance make the work cheaper first?
6. If not, should execution stop and escalate instead of continuing?

That is the capability-aware execution contract for the first planning slice.
