# Execution Summary Contract

This page defines the compact planning-side summary shape for completed bounded work.

Use it when a direct slice or execplan finishes and later contributors should not have to reconstruct what was delivered, how it was validated, and where follow-through now lives.

This contract is intentionally small.
It exists to reduce restart and handoff cost, not to turn planning into a second memory system or a narrative changelog.

## Purpose

- Leave one durable checked-in outcome summary for a completed bounded slice.
- Keep continuation cheaper than re-reading the full archived plan or recovering the outcome from chat.
- Make it obvious whether follow-on was routed cleanly or whether the slice truly finished the larger intended outcome.

## What An Execution Summary Should Capture

For a completed planning slice, record:

- what outcome was delivered
- how validation was confirmed
- where required follow-on now lives
- how a later contributor should treat the slice when resuming related work

When the slice renamed, moved, retired, or refactored a named surface, `Validation confirmed` should make the stale-reference sweep explicit instead of implying that closure was complete.

The point is not exhaustive history.
The point is one compact answer to "what happened here, and what should the next session know?"

## Canonical Shape

In execplans, use the `## Execution Summary` section with these fields:

- `Outcome delivered`
- `Validation confirmed`
- `Follow-on routed to`
- `Resume from`

Keep each field brief and decision-shaped.

Good examples:

- `Outcome delivered: Added archive cleanup guards for compact TODO rows.`
- `Validation confirmed: make check; uv run pytest packages/planning/tests/test_installer.py`
- `Follow-on routed to: ROADMAP.md candidate \`Handoff and execution summary contract\``
- `Resume from: No further action in this plan; start from the queued follow-on candidate if the broader outcome is reopened.`

## What This Contract Is Not

Do not use the execution summary as:

- a second drift log
- a retrospective notebook
- a memory note
- a backlog dump
- a place to restate the entire plan

If a fact is durable technical knowledge, route it to memory or canonical docs instead.
If a task remains active, keep the live execution contract in the plan itself rather than faking closure through the summary.
If the slice stopped with meaningful deferred work or discovered implications, preserve that in `Iterative Follow-Through` instead of overloading `Execution Summary`.

## Relationship To Intent Continuity

Execution summaries complement, but do not replace:

- `Intent Continuity`
- `Required Continuation`
- `Iterative Follow-Through`

Those sections answer whether the larger intended outcome is complete and what checked-in surface owns follow-through.
`Iterative Follow-Through` carries the deferred work, discovered implications, and proof/validation carry-forward that the next bounded slice should inherit.

The execution summary answers:

- what this bounded slice actually achieved
- what validation was performed
- how a later contributor should treat the result without rereading the whole plan

## Archive Rule

Before archiving a completed execplan, the plan should carry an explicit execution summary.

Archive should fail closed when a completed plan still leaves outcome, validation, or continuation state implicit enough that a later contributor would need to reconstruct it from drift prose or chat.
