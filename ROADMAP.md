# Roadmap

Last reviewed: 2026-04-05

## Purpose

This file holds inactive long-horizon epics and planning residue that should not live in `TODO.md` or an active execplan.

Use it to:

- track not-yet-active multi-tranche work
- hold concise strategic residue between releases
- record the next candidate epics that may later be promoted into an active execplan
- reopen planning only when a new repo-actionable queue appears

Do not use it for:

- daily execution tracking
- detailed implementation logs
- active-milestone status that already lives in `TODO.md` or an execplan
- duplicate status notes that already live in memory or canonical docs
- lists of completed epics whose only purpose is historical record

## Active Handoff

- The first package pass is focused on establishing the reusable payload, installer CLI, checker, and a self-hosted reference repo shape.

## Next Candidate Queue

- Add upgrade and uninstall flows when the initial installer contract is stable and repeated dogfooding shows the safe lifecycle boundaries clearly.
- Add more repo-agnostic generated agent-surface support when multiple repositories converge on the same startup contract.
- Add optional planning skills only when a repeated planning workflow proves stable enough to ship as reusable automation.

## Reopen Conditions

- Reopen additional roadmap planning when a new repo-actionable queue, release gate, or explicit strategic decision appears.

## Promotion Rules

- Promote an epic out of `ROADMAP.md` only when it is ready for active execution and has a clear owning execplan or a genuinely small direct task.
- When an item moves into `TODO.md`, keep only the high-level future framing here and let the execplan own execution detail.
- Remove or compress entries that have been fully implemented, retired, or superseded.
- Review this file at release boundaries and prune or compress items that are no longer plausible near-term candidates.
