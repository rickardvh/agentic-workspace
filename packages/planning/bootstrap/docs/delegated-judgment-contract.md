# Delegated Judgment Contract

This page defines the front-door contract for bounded delegated judgment in Agentic Workspace.

Use it when the human wants to provide direction and constraints while trusting the agent to handle bounded local decisions.

This contract does not authorize open-ended initiative.
It exists to make delegated judgment explicit, portable, and auditable.

## Purpose

- Clarify what the human should set.
- Clarify what the agent may decide locally.
- Clarify what requires explicit promotion, escalation, or confirmation.

The intended outcome is simple:

- humans can step back to direction and constraints
- agents can proceed without constant supervision
- the repo still fails safe when scope, ownership, or confidence changes

## What The Human Sets

The human should normally provide:

- requested outcome
- priorities
- hard constraints
- any explicit approvals or prohibitions

Examples:

- "Implement the smallest safe slice of this capability."
- "Keep changes inside planning and workspace docs."
- "Do not widen this into a plugin system."
- "Stop and ask if the cleaner fix requires changing ownership boundaries."

The more clearly those are expressed, the more safely the agent can own local execution.

## What The Agent May Decide Locally

The agent may improve means locally when doing so stays inside the requested outcome and constraints.

Allowed local judgment includes:

- decomposition into smaller bounded slices
- choosing the narrowest touched-path set
- tightening validation
- selecting the relevant skill or registry-backed workflow
- preferring a checked-in plan when direct execution is no longer safe
- capturing durable residue in the correct checked-in surface

This is bounded initiative.
It is not permission to replace the requested outcome with a broader or more ambitious one.

## What Requires Promotion Or Escalation

The agent must not silently widen:

- requested outcome
- owned surface
- time horizon

Promotion or escalation is required when:

- the better-looking solution changes what success means
- the requested path is blocked and cannot complete safely as stated
- the requested path would violate a stable contract or ownership boundary
- validation would be meaningless without the added work
- confidence drops below the point where silent continuation is defensible

The safe pattern is:

- improve means locally
- escalate changed ends explicitly

Short rule:

- Improve means locally.
- Do not silently rewrite ends locally.

## Scope-Expansion Rule

When a better answer requires broader scope, present it as a choice rather than smuggling it into execution.

The agent should say, in effect:

- "I can complete the requested slice safely."
- "There is a broader fix that may be better because ..."
- "That broader fix expands scope because ..."
- "Promote it if you want that larger outcome."

This keeps delegated judgment useful without turning it into uncontrolled drift.

## Relationship To Planning

Planning is the current home of this contract.

- direct tasks stay direct when the request remains self-sufficient
- execplans appear when the checked-in execution contract reduces ambiguity or restart cost
- escalation appears when safe continuation is no longer justified

Delegated judgment does not replace planning.
It defines how much local decision-making is safe before planning, promotion, or escalation should take over.

## Relationship To Machine-Readable Defaults

`agentic-workspace defaults --format json` should expose the same front-door contract in structured form.

The structured surface should answer:

- what the human sets
- what the agent may decide locally
- what forces promotion or escalation

That keeps the contract queryable for agents that should not have to rely on richer prose first.
