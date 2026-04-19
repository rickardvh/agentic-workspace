# Iterative Follow-Through Contract

This page defines the compact planning residue that should survive when a bounded slice stops before the broader goal is complete.

Use it when the work is intentionally iterative:

- the current slice lays groundwork rather than finishing everything
- new implications surfaced during execution
- some proof exists now, but validation or follow-on still remains
- the next likely slice should inherit more than a single next action

This contract is intentionally narrow.
It exists to keep iterative development coherent without turning every bounded slice into a long-range roadmap.

## Purpose

- Preserve what changed about the larger line of work after this slice.
- Distinguish intentional deferral from newly discovered implications.
- Carry forward proof achieved now versus validation still needed later.
- Make the next likely slice legible without rereading the full plan.

## Canonical Shape

In execplans, use the `## Iterative Follow-Through` section with these fields:

- `What this slice enabled`
- `Intentionally deferred`
- `Discovered implications`
- `Proof achieved now`
- `Validation still needed`
- `Next likely slice`

Keep each field compact and decision-shaped.

Good examples:

- `What this slice enabled: The workspace report now exposes repo-friction hotspots with policy-source attribution.`
- `Intentionally deferred: Evidence-weight calibration across repeated hotspots and moderation signals.`
- `Discovered implications: Large-file hotspots alone are too blunt without a concept-friction companion signal.`
- `Proof achieved now: New report fields are queryable through \`agentic-workspace report --format json\`.`
- `Validation still needed: Dogfood one ordinary-work cleanup slice to confirm the evidence is actionable rather than noisy.`
- `Next likely slice: Calibrate hotspot evidence against one real cleanup pass before widening the report surface.`

## Relationship To Other Planning Fields

`Iterative Follow-Through` complements, but does not replace:

- `Intent Continuity`
- `Required Continuation`
- `Execution Summary`

Use the distinction this way:

- `Intent Continuity` says whether the broader goal is complete and which checked-in surface owns it if not.
- `Required Continuation` says whether follow-on is mandatory and what should activate it.
- `Iterative Follow-Through` says what this slice changed about that larger line of work and what the next slice should inherit.
- `Execution Summary` says what the bounded slice delivered once it stops.

## What This Contract Is Not

Do not use iterative follow-through as:

- a second roadmap
- a backlog dump
- a substitute for `Required Continuation`
- a narrative drift log
- a place to restate the whole plan

If the work becomes a different requested outcome, promote or escalate instead of stretching this section.

## Summary Projection

When an active execplan carries this section clearly enough, `agentic-workspace summary --format json` may expose it as `follow_through_contract`.

Treat that view as a projection over the active planning state, not as a second authority.
