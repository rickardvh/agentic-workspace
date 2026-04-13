# Environment And Recovery Contract

This page defines the planning-side contract for environment assumptions, interruption handling, and recovery paths.

Use it when active work depends on non-obvious tooling state, bootstrap preconditions, partial-failure handling, or a restart path that would otherwise have to be rediscovered from chat or scattered docs.

This contract is intentionally compact.
It exists to reduce dead-ends and restart cost without turning planning into a full runbook system or duplicating module-local operational docs.

## Purpose

- Make environment-sensitive work restartable from checked-in planning state.
- Keep recovery guidance small enough to stay cheaper than rediscovery.
- Clarify when module-local runbooks are enough and when active planning must carry the current recovery path.

## What This Contract Should Capture

For an active planning slice, capture only the environment and recovery facts that materially affect safe continuation:

- required preconditions or tool state
- the first safe resume point after interruption
- known failure or retry boundaries
- the command or check that proves the environment is usable
- where to escalate when the active slice cannot recover locally

The goal is not exhaustive troubleshooting.
The goal is one compact answer to "what does this work need in order to resume safely right now?"

## Canonical Shape

Do not add a new dedicated recovery section to every execplan.
Use the existing planning fields deliberately:

- `Immediate Next Action`: the next safe resume step after interruption
- `Blockers`: environment failures, missing prerequisites, or recovery blockers that currently stop progress
- `Invariants`: environment assumptions and safety boundaries that must remain true
- `Validation Commands`: the narrowest command that proves the environment or touched surface is healthy enough to proceed
- `Execution Summary`: after completion, the compact note a later contributor needs instead of re-deriving the recovery story

For direct tasks, the same rule stays simple:
if safe continuation depends on more than the TODO row can carry, promote the task into an execplan instead of inventing ad hoc prose elsewhere.

## When To Promote Recovery Guidance Into Planning

Promote the work into an execplan or strengthen the active plan when any of these become true:

- interruption would leave more than one plausible safe resume path
- a failed command needs explicit retry, rollback, or cleanup guidance
- the active slice depends on non-obvious environment state that is easy to lose between sessions
- module-local docs explain the subsystem generally, but not the current task's recovery boundary
- another contributor would need to infer whether the problem is local environment drift, expected repo customization, or a real contract failure

If module-local docs already fully answer the operational question and the current task does not add a task-specific recovery wrinkle, link or rely on those docs instead of copying them into the plan.

## What This Contract Is Not

Do not use planning recovery guidance as:

- a full troubleshooting handbook
- a substitute for package or subsystem runbooks
- a broad environment inventory
- a memory note for durable technical facts
- a narrative log of every failed attempt

Durable environment knowledge still belongs in canonical docs or memory.
Planning carries only the task-local recovery facts that change what the next contributor should do now.

## Relationship To Direct Tasks

The direct-task contract remains intentionally small.

If the current work can still restart safely from `Why now`, `Next action`, and `Done when`, keep it direct.
If interruption, environment drift, or partial failure means the TODO row no longer answers "how do I continue safely?", promote the work into an execplan.

That promotion is the recovery contract.
Do not stretch TODO rows into shadow execplans.

## Relationship To Module Docs

Planning owns current execution recovery.
Module docs own durable operational guidance.

Use planning to capture:

- the recovery boundary for the active slice
- the exact precondition that matters now
- the escalation point for the current thread

Use module docs or memory to capture:

- stable runbooks
- recurring environment traps
- long-lived setup guidance
- subsystem-specific maintenance procedures

## Archive Rule

Before archiving a completed execplan, make sure the plan no longer depends on implicit recovery knowledge.

If later contributors would still need to reconstruct the safe resume point, environment assumption, or unresolved recovery blocker from chat or drift prose, the plan is not ready to archive cleanly.
