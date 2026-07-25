---
name: planning-orchestrator-workflow
description: Primary procedure for an assigned orchestrator to dispatch, track, and admit bounded delegated work from canonical Planning state.
---

# Planning Orchestrator Workflow

Use this skill only when canonical Planning state assigns the current agent the
orchestrator role for a delegated run. It is the single primary procedure for
assigned orchestration; it does not select the target, redefine the assignment,
or replace the action gate.

This skill is agent-agnostic.
The worker may be:

- an internal delegated agent
- a read-only explorer for one bounded inspection question
- a local model run through CLI or API
- another vendor executor reached through CLI or API

If the canonical assignment selects the current target for direct work, do not
load this skill. Use the normal bounded execution route instead.

## Read First

1. `AGENTS.md` and the startup action gate.
2. The canonical assignment decision and delegated-run state from Planning.
3. `agentic-workspace planning handoff --target . --format json` or the
   canonical assignment export when manual transport is selected.
4. The active execplan only through the packet's authoritative references.

## Workflow

1. Consume the canonical assignment and action gate. If the gate forbids the
   current target, stop: do not reinterpret the worker slice as local work.
2. Retain orchestrator ownership of intent, decomposition, assignment target,
   work bounds, admission, integration, proof interpretation, and closeout.
3. Retrieve the assigned-run packet. Never re-rank candidates or alter target
   ownership from this skill.
4. Select only the transport permitted by that packet:
   - internal delegated-worker execution: `planning-autopilot` / `autopilot.run`
   - manual or external transport: `planning-manual-delegation`
   - returned result: `planning-returned-result`
5. Dispatch or export the assignment unchanged except for an explicitly
   authorized transport envelope.
6. Track `returned`, `failed`, `blocked`, `stale`, and `stopped` states through
   Planning operations. Route repair, override, or reassignment back to the
   canonical assignment operation; do not repair by silently implementing.
7. On return, use `planning-returned-result` for admission and integration;
   then route proof to `planning-intent-verification` and closeout to
   `planning-closeout-trust`.

## Worker Contract

The worker owns only the assigned bounded slice:

- read-only exploration for one explicit question when assigned
- bounded implementation
- narrow validation
- checked-in updates inside explicitly assigned owned surfaces
- cleanup and commit only when explicitly assigned and still bounded

Default worker stop conditions:

- the delegated task needs broad rereads outside the explicit read-first refs
- the task shape widens beyond the owned write scope
- the chosen delegation method cannot preserve the checked-in contract
- escalation boundaries are hit

## Boundaries

- Do not use this skill to turn repo config into a scheduler.
- Do not hardcode vendor-specific routing rules into checked-in planning.
- Do not let the delegated worker become the only place continuity lives.
- Do not widen requested ends just because a stronger planner is available.
- A binding non-local assignment forbids local implementation of that worker
  slice, even if local execution seems cheaper.

## Output

For each orchestrated run, record through the canonical Planning operation:

- which bounded slice was delegated
- what the handoff contract contained
- route skipped reason when direct work was chosen
- expected token savings, actual friction, proof result, and quality concern
- any decomposition adjustment learned from the delegation outcome
- what overhead remained
- what workflow improvement signal, if any, should survive in checked-in planning or review residue
