# Roadmap

Last reviewed: [LAST_REVIEWED_DATE]

## Purpose

This file holds inactive long-horizon candidate lanes and planning residue that should not live in `TODO.md` or an active execplan.

Use it to:

- track not-yet-active grouped work
- hold concise strategic residue between releases
- record the next candidate lanes that may later be promoted into an active execplan
- reopen planning only when a new repo-actionable queue appears

Do not use it for:

- daily execution tracking
- detailed implementation logs
- active-milestone status that already lives in `TODO.md` or an execplan
- duplicate status notes that already live in memory or canonical docs
- lists of completed lanes whose only purpose is historical record

## Active Handoff

- Keep this section short. Summarise only the active strategic handoff that still matters for future promotion decisions.

## Candidate Lanes

- Lane: Candidate placeholder
  ID: candidate-placeholder
  Priority: first
  Issues: none
  Outcome: preserve one grouped deferred line of work without activating it yet.
  Why later: wait until a concrete report, blocker, or product decision creates a bounded active tranche.
  Promotion signal: promote when that bounded active tranche is clear enough to own in `TODO.md` or one execplan.
  Suggested first slice: define one short active tranche rather than widening directly into the full lane.

## Reopen Conditions

- Reopen additional roadmap planning when a new repo-actionable queue, release gate, or explicit strategic decision appears.

## Promotion Rules

- Promote a lane out of `ROADMAP.md` only when it is ready for active execution and has a clear owning execplan or a genuinely small direct task.
- When an item moves into `TODO.md`, keep only the high-level future framing here and let the execplan own execution detail.
- Remove or compress entries that have been fully implemented, retired, or superseded.
- Review this file at release boundaries and prune or compress items that are no longer plausible near-term candidates.
