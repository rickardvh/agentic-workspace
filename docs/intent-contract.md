# Intent Contract

This page defines the compact planning-side intent contract for active work.

Use it when the question is not "what happened after completion?" but "what did the human ask for, what constraints still bind the work, and what proof or escalation boundary should survive restart?"

## Purpose

- Preserve the requested end state in checked-in form.
- Make active work cheaper to resume across sessions and agents.
- Keep the first machine-readable contract derived from the existing execplan shape instead of introducing a second plan schema.

## Front-Door Intent Surface

Use:

```bash
agentic-workspace defaults --section intent --format json
```

That selector carries the compact front-door intent split:

- `confirmed_intent`: the human-owned request before workspace normalization
- `interpreted_intent`: the workspace-normalized request carried forward by lifecycle commands

Use it when the question is what the human asked for and how the workspace normalized it.

## Cheap Clarification Surface

Use:

```bash
agentic-workspace defaults --section clarification --format json
```

That selector captures the smallest repo-context question needed to remove vague-prompt ambiguity.

Use it when the task is vague but the repo context can cheaply disambiguate it without widening the request.

## Prompt Routing Surface

Use:

```bash
agentic-workspace defaults --section prompt_routing --format json
```

That selector maps vague prompt classes to a likely proof lane and owner surface.
Each `proof_lane` should name an executable proof or validation route id, and cross-cutting cases may add `broaden_with` follow-on lanes instead of inventing combined route names.

Use it when the main missing judgment is which contract lane or owner should absorb the work.

## Relay Surface

Use:

```bash
agentic-workspace defaults --section relay --format json
```

That selector records the strong-planner / cheap-implementer relay, the delegated execution method rule, and the routed-Memory bridge.

Use it when the prompt is already being shaped into a compact contract and the question is how the handoff should proceed.

Use:

```bash
agentic-planning-bootstrap handoff --format json
```

when the question is not only the relay rule, but the active worker handoff derived from the current planning state.

## Canonical Surface

Use:

```bash
agentic-planning-bootstrap summary --format json
```

That summary now carries a top-level schema envelope:

- `kind = "planning-summary/v1"`
- `schema.schema_version = "planning-summary-schema/v1"`

The `planning_record` object is the compact machine-readable active record for current work when planning has one active TODO item and one active execplan. The `active_contract` object remains as the narrower intent view over that canonical record, and `follow_through_contract` may carry compact iterative residue when the active plan records it clearly enough.

Use the summary first when the question is active intent, constraints, proof, or escalation boundaries.
Do not start by parsing `TODO.md` or execplan prose when the compact summary already answers the question.

The canonical planning record currently carries:

- the active task id and execplan surface
- `status`
- `requested_outcome`
- `hard_constraints`
- `agent_may_decide`
- `next_action`
- `touched_scope`
- `proof_expectations`
- `tool_verification`
- `escalate_when`
- `continuation_owner`
- `completion_criteria`
- `blockers`
- `minimal_refs`

`active_contract` remains available as a compatibility projection focused on intent and escalation boundaries.
`follow_through_contract` remains available as a compatibility projection focused on iterative carry-forward across bounded slices.
`handoff_contract` remains available as a compatibility projection focused on bounded delegated-worker handoff.

## Rules

- Derive the canonical planning record and its views from the existing execplan fields rather than adding a second required authoring section.
- Treat `planning_record` as the canonical active planning state whenever it is available; `active_contract` is a projection over that state, not a peer authority.
- Keep it small enough that a weaker or later agent can recover the intended end state without broad rereading.
- Treat it as unavailable when active planning is ambiguous instead of fabricating certainty from several partial surfaces.
- Preserve explicit escalation boundaries; the contract must not silently widen requested outcome, ownership scope, or time horizon.
- When a plan declares `Required Tools`, expose that requirement directly so weaker agents can stop or escalate before attempting impossible work.
- If an agent runtime uses native planning artifacts, project any durable state back into the canonical planning record before handoff or review instead of treating runtime-local files as authoritative.
- Treat raw planning prose as a thin human maintenance view and semantic fallback, not the default inspection path for ordinary state questions.

## Relationship To Other Contracts

- Use `docs/delegated-judgment-contract.md` for the prose rule about what the human sets and what the agent may decide locally.
- Use `docs/iterative-follow-through-contract.md` for bounded-slice carry-forward and deferred-proof residue.
- Use `docs/execution-summary-contract.md` for completed-slice summaries.
- Use `docs/execplans/README.md` for the active execplan authoring rules that supply this compact contract.

## Non-Goals

- This is not a second execplan.
- This is not a narrative handoff history.
- This is not the full minimal resumable execution contract for every active task shape.
