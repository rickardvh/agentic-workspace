# Dogfooding Feedback

## Purpose

Use this page when normal work in this repo reveals friction that might need to become product work.

This is a maintainer policy surface, not first-line doctrine. The enduring principles stay in `docs/design-principles.md`.

## What Belongs Here

Use this surface for questions like:

- should this repo symptom become a product issue or lane?
- is the friction package-local, boundary-related, install-flow related, or only monorepo-local?
- does the right fix belong in planning, memory, routing, checks, lifecycle behavior, or the repo itself?
- is the pressure strong enough to justify adding new planned work now?

## Routing Rule

When repo-local work reveals a plausible product-level deficiency:

1. classify the friction first
2. decide whether the problem is best fixed in the repo, in a shipped package, or in a checked-in contract surface
3. record the signal in the smallest durable owner that should carry it

Preferred destinations:

- active planning state or an active execplan when it changes current execution
- roadmap state when it is a deferred product direction
- memory when the durable lesson should survive the current slice
- canonical docs when the answer is a clearer stable contract rather than a new work item

Do not leave meaningful product feedback in chat-only residue.

## Classification

Classify friction into one of these buckets before routing it:

- package defect
- ownership or boundary issue
- install or upgrade flow issue
- docs or routing issue
- proof or review surface issue
- monorepo-only friction

## Admission Rule

New planning or contract work should enter the queue only when at least one of these is true:

- measured overhead reduction opportunity
- repeated practical failure class
- repeated dogfooding friction
- explicit maintainer override for strategically important work

Concept opportunity alone is not enough. The default posture should be subtraction and proof, not idea accumulation.

## Repo Improvement Vs Workspace Self-Improvement

Keep these distinct:

- workspace self-improvement: clearer reporting, routing, recovery, or contract surfaces that stay general and bounded
- repo-directed improvement: changing the repo because repeated evidence shows the repo is the real friction source

Repo-directed improvement should clear a higher bar. One-off agent discomfort, local taste, or friction the workspace can still honestly absorb is not enough.

## Dogfooding Rules

- Treat this monorepo as the proving ground for shipped agent workflows.
- Prefer fixing the shipped package or contract over adding repo-local workaround residue when the problem clearly generalizes.
- Do not normalize repo-specific hacks as product behavior.
- When a symptom does not generalize cleanly, route it into repo-owned planning, memory, or docs instead of forcing a package change.
- When the answer is plausibly yes to “should the product have found, prevented, or made this cheaper?”, record that signal durably.

## Practical Standard

The goal is not novelty. The goal is lower real operating cost:

- faster restart
- safer execution
- cheaper continuation across tools and sessions
- less rereading
- less hidden human cleanup

When several plausible improvements compete, prefer the one that removes the clearest ordinary-work efficiency tax.
