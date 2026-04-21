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
- Proof achieved now: one compact meaning-boundary rule is checked in with a realistic restart example and tied back to the routine-recovery questions.
- Validation still needed: none beyond ordinary future dogfooding on later planning-surface tightening slices.
- Next likely slice: tighten the highest-value compact planning surface or field set revealed by this boundary.

## Delegated Judgment

- Requested outcome: classify which planning meanings must be cheaply machine-recoverable, which may remain in compact prose, and which are raw execplan detail by design.
- Hard constraints: keep `planning_record` canonical for active state; avoid pushing everything into machine-readable form; avoid prose duplication that competes with canonical state; do not redefine the roadmap/TODO/execplan hierarchy.
- Agent may decide locally: which recent planning meanings provide the best examples, whether the resulting rule belongs in one canonical doc or a compact doc plus checker/test support, and the narrowest validation that proves the boundary is usable.
- Escalate when: the best-looking classification would require broad schema extraction, cross-module redesign, or a new source of authority beyond existing planning surfaces.

## Active Milestone

- ID: planning-surface-meaning-boundary
- Status: completed
- Scope: define and dogfood one compact meaning-boundary rule for planning surfaces.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None; the slice is complete and follow-on work is routed to `ROADMAP.md`.

## Blockers

- None.

## Touched Paths

- TODO.md
- .agentic-workspace/planning/execplans/planning-surface-meaning-boundary-2026-04-17.md
- docs/default-path-contract.md
- .agentic-workspace/planning/execplans/README.md
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
- rg "Use this split when deciding where a planning meaning belongs|line-by-line change log belongs in the execplan detail" docs packages/planning

## Required Tools

- uv

## Completion Criteria

- One compact meaning-boundary rule is checked in and tied to the routine-recovery question set.
- The rule makes the next high-value surface-tightening target clearer rather than broader.
- The slice leaves behind a clear follow-on target in `ROADMAP.md` or active planning without reopening general planning redesign.

## Smaller-Agent Handoff

- Use this plan as the sole execution contract; do not infer a broader redesign from the parent lane.
- Read only the minimum relevant surfaces: `AGENTS.md`, `TODO.md`, this execplan, `ROADMAP.md` lane stub, `docs/default-path-contract.md`, `.agentic-workspace/planning/execplans/README.md`, and any directly touched planning docs/tests.
- Prefer one compact meaning-boundary rule plus one realistic restart/use example over a broad taxonomy pass.
- If the best expression is a doc clarification with narrow checker/test updates, do only that.
- If the best expression would require broad schema extraction or multiple competing owners, stop and escalate rather than widening the slice.

## Execution Summary

- Outcome delivered: one compact meaning-boundary rule was checked into the default path contract and execplans README, with package bootstrap mirrors and test fixtures kept aligned.
- Validation confirmed: `uv run python scripts/check/check_planning_surfaces.py`; `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`; `uv run agentic-planning-bootstrap summary --format json`; `rg "Use this split when deciding where a planning meaning belongs|line-by-line change log belongs in the execplan detail" docs packages/planning`
- Follow-on routed to: `ROADMAP.md` / the next planning-surface tightening slice (`#164`)
- Resume from: the next highest-value compact planning surface or field set

## Drift Log

- 2026-04-17: Re-promoted the next bounded slice from `planning-surface-clarity-routine-recovery` for orchestrated smaller-agent execution.
