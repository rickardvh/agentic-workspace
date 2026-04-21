# Context Budget Contract

This contract defines the compact planning-side context-budget discipline for active work.

Use it to keep the live working set small, preserve only the residue that must survive a context shift, and make later reload cheaper without turning planning into a second chat log.

## Core Distinction

- `live working set`: the smallest bundle that must stay mentally active to finish the current bounded step safely
- `recoverable later`: useful context that can be reloaded from checked-in surfaces when a boundary is crossed again
- `externalize before shift`: residue that must be written down before deliberately shedding or switching context

Keep the live working set small on purpose.
Do not keep broad subsystem history mentally live just because it might matter later.
If it can be cheaply recovered from checked-in state, treat it as recoverable later instead.

## Externalize Before Shift

Before deliberately shedding or switching context, externalize the minimum residue that later proof, review, or continuation would otherwise have to reconstruct:

- exact next step when it is no longer obvious from the bounded slice
- unresolved blockers or ambiguity that would change the next safe move
- proof expectations that still govern completion
- the reason a path was chosen or rejected when that decision matters later
- any scoped caution that an interrupted or delegated return should not have to rediscover

Do not turn this into broad narrative dumping.
The rule is to preserve the smallest residue that keeps later continuation honest and cheap.

## Tiny Resumability Note

The tiny resumability note is the cheapest scoped residue that helps a later return without promoting the content into broad planning or memory.

It should usually answer one small thing such as:

- what subtle risk was found
- what decision should not be reopened casually
- what can safely be forgotten now
- what to reload first if this area is revisited later

Keep it one short line inside the active execplan's `Context Budget` section rather than a second free-form note system.

## Context-Shift Triggers

The main triggers for unloading one bundle and reloading another are:

- bounded-slice proof reached or current milestone completed
- subsystem boundary crossed
- stop or escalation condition reached
- interruption, tool switch, or delegated handoff
- return from a finished, interrupted, or externally executed run

Use these triggers to decide when the live bundle should shrink or change.
Do not micromanage every tiny attention shift.

## Mixed-Agent Resume

Interruption and resume should remain cheap across planner, executor, and reviewer boundaries.

For mixed-agent work:

- keep the checked-in planning handoff authoritative
- externalize the minimum residue before a tool or session change
- prefer resumability notes plus minimal refs over broad rereads
- reload only the live bundle needed for the next bounded step

## Interaction-Cost Rule

Optimize for total costly interactions per successful tranche, not for one narrow proxy.

Prefer changes that reduce:

- broad rereads
- clarification loops
- retry and repair cycles
- avoidable review bounce
- repeated recovery work after interruptions

If a local optimization merely shifts cost into more rereads, more follow-up turns, or more review friction later, it is not a real win.
