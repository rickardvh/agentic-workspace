# Planning Surface Meaning Boundary

## Goal

- Define the minimum meaning boundary between machine-readable planning state, compact prose surfaces, and raw execplan detail so later planning-surface compression work can remove ambiguity without creating a second source of truth.

## Non-Goals

- Broad redesign of planning schemas or hierarchy.
- Multi-surface cleanup in the same slice.
- New planning artifacts, backlog shapes, or reporting systems.
- Optimizing for human narrative richness over operational clarity.

## Intent Continuity

- Larger intended outcome: make planning surfaces cheaper for agents to distinguish, recover from, and trust without broad prose rereads.
- This slice completes the larger intended outcome: no
- Continuation surface: ROADMAP.md
- Parent lane: planning-surface-clarity-routine-recovery

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: ROADMAP.md
- Activation trigger: when the meaning boundary is stable enough to tighten one high-value planning surface or field set without reopening ownership ambiguity.

## Iterative Follow-Through

- What this slice enabled: later planning-surface refinements can target one compact owner with less ambiguity about whether a meaning belongs in state, prose, or raw plan detail.
- Intentionally deferred: the actual follow-on surface compression win.
- Discovered implications: the routine-recovery question set is a useful test, but not every question needs a machine-readable answer if compact prose remains cheaper and authoritative enough.
- Proof achieved now: pending until the meaning boundary is checked in and tied back to the routine-recovery questions plus one realistic restart/use example.
- Validation still needed: planning-surface checks and one dogfood pass showing the boundary makes the next tightening target easier to choose.
- Next likely slice: tighten the highest-value compact planning surface or field set revealed by this boundary.

## Delegated Judgment

- Requested outcome: classify which planning meanings must be cheaply machine-recoverable, which may remain in compact prose, and which are raw execplan detail by design.
- Hard constraints: keep `planning_record` canonical for active state; avoid pushing everything into machine-readable form; avoid prose duplication that competes with canonical state; do not redefine the roadmap/TODO/execplan hierarchy.
- Agent may decide locally: which recent planning meanings provide the best examples, whether the resulting rule belongs in one canonical doc or a compact doc plus checker/test support, and the narrowest validation that proves the boundary is usable.
- Escalate when: the best-looking classification would require broad schema extraction, cross-module redesign, or a new source of authority beyond existing planning surfaces.

## Active Milestone

- ID: planning-surface-meaning-boundary
- Status: in-progress
- Scope: define and dogfood one compact meaning-boundary rule for planning surfaces.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Classify the routine-recovery meanings from the previous slice into machine-readable state, compact prose, and raw execplan detail, then record the rule in one canonical planning doc.

## Blockers

- None.

## Touched Paths

- TODO.md
- docs/execplans/planning-surface-meaning-boundary-2026-04-17.md
- docs/default-path-contract.md
- docs/execplans/README.md
- packages/planning/bootstrap/docs/
- packages/planning/tests/

## Invariants

- Machine-readable planning state stays compact and canonical.
- Compact prose remains authoritative only for meanings that do not need state-level recovery.
- Raw execplan detail remains fallback and maintenance detail, not the normal routine-recovery path.

## Contract Decisions To Freeze

- Not every planning meaning needs to become a queryable field.
- Meanings that materially affect routine restart, active ownership, and required continuation should prefer compact state when it is cheaper and stable.
- Meanings that only matter for deeper interpretation or maintenance may remain in compact prose or raw plan detail when that is the cheaper truthful owner.

## Open Questions To Close

- Which meanings from the routine-recovery question set must stay machine-readable?
- Which meanings are better left in compact prose even if they are routine?
- Which meanings are intentionally raw execplan detail rather than missing structure?

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py
- uv run agentic-planning-bootstrap summary --format json
- uv run agentic-planning-bootstrap report --format json

## Required Tools

- uv

## Completion Criteria

- One compact meaning-boundary rule is checked in and tied to the routine-recovery question set.
- The rule makes the next high-value surface-tightening target clearer rather than broader.
- The slice leaves behind a clear follow-on target in `ROADMAP.md` or active planning without reopening general planning redesign.

## Execution Summary

- Outcome delivered: pending
- Validation confirmed: pending
- Follow-on routed to: pending
- Resume from: current milestone

## Drift Log

- 2026-04-17: Promoted the next bounded slice from `planning-surface-clarity-routine-recovery` after the routine recovery path itself was clarified and archived.
