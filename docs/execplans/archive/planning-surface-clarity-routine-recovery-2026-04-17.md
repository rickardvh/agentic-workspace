# Planning Surface Clarity Routine Recovery

## Goal

- Define a bounded first slice of the `planning-surface-clarity-routine-recovery` lane that a smaller agent can execute safely: audit repeated routine-recovery ambiguity, define the minimum routine-recovery question set, and tighten one high-value compact planning surface only if the answer is clear from the audit.

## Non-Goals

- Redesign Planning from scratch.
- Reopen the recently closed hierarchy/routing lane.
- Add a second planning authority, new planning artifact, or broad new process.
- Expand into standing-intent, optimization-bias, Memory, or declarative-contract work in the same slice.

## Intent Continuity

- Larger intended outcome: make planning surfaces cheaper for agents to distinguish, recover from, and trust without broad prose rereads.
- This slice completes the larger intended outcome: no
- Continuation surface: ROADMAP.md
- Parent lane: planning-surface-clarity-routine-recovery

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: ROADMAP.md
- Activation trigger: when the routine-recovery question set and first ambiguity audit are stable enough to justify one targeted surface refinement or one follow-on review-derived candidate.

## Iterative Follow-Through

- What this slice enabled: the front-door route now answers routine planning recovery from one compact question set instead of scattering the answer across multiple projections.
- Intentionally deferred: any broader schema redesign, multi-surface cleanup, or standing-guidance integration work.
- Discovered implications: if routine-recovery questions still grow beyond this bundle, the next cheapest move is still a compact field-set clarification rather than more prose.
- Proof achieved now: `docs/default-path-contract.md` names the minimum recovery questions and the checker enforces that compact route contract.
- Validation still needed: a live dogfood pass should confirm the recovery path stays obvious in ordinary restart work.
- Next likely slice: implement the highest-value follow-on refinement from `ROADMAP.md` if the compact recovery path still feels split.

## Delegated Judgment

- Requested outcome: prepare a handoff-safe first slice for a smaller agent to audit routine planning recovery, define the minimum operational question set, and land one narrow clarification if it is mechanically obvious.
- Hard constraints: keep `planning_record` canonical; prefer clarifying existing surfaces over inventing new ones; keep the result compact enough that a cheaper agent can execute it without broad rereads or product-shape debate; do not silently widen into hierarchy redesign, standing-intent enforcement, or backlog semantics.
- Agent may decide locally: exact wording of the question set, which recent planning surfaces provide the best ordinary-work evidence, whether the audit should live in a review artifact or directly in the execplan summary, and whether the first clarification belongs in summary/report output, selector docs, or one contract doc.
- Escalate when: the best-looking fix would require changing canonical planning ownership, adding a new planning artifact, redefining the roadmap/TODO/execplan hierarchy, or touching more than one compact surface family at once.

## Active Milestone

- ID: planning-surface-clarity-routine-recovery
- Status: completed
- Scope: shape a smaller-agent-ready first slice around routine-recovery questions, evidence, and one bounded clarification target.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None; the slice is complete and follow-on work is routed to `ROADMAP.md`.

## Blockers

- None.

## Touched Paths

- TODO.md
- docs/default-path-contract.md
- docs/execplans/planning-surface-clarity-routine-recovery-2026-04-17.md
- packages/planning/tests/
- .agentic-workspace/planning/scripts/check/check_planning_surfaces.py
- packages/planning/bootstrap/.agentic-workspace/planning/scripts/check/check_planning_surfaces.py

## Invariants

- `planning_record` remains the canonical compact active planning state.
- New clarity work must reduce ordinary rereading rather than add more planning vocabulary.
- The smaller-agent handoff must stay bounded enough that implementation can proceed without high-level product reinterpretation.

## Contract Decisions To Freeze

- The first slice should answer a small routine-recovery question set before it tries to redesign planning surfaces.
- The smaller agent should only implement one compact clarification target if the audit makes that target obvious.
- If the audit reveals broader ambiguity than one cheap slice can safely resolve, route that residue back to `ROADMAP.md` instead of widening the tranche.

## Open Questions To Close

- Which routine-recovery questions are truly minimum and repeated in ordinary work?
- Which compact surface should own each answer first?
- Is the first clarification best expressed as a summary/report field tweak, a selector/doc clarification, or a narrow reporting rule?

## Validation Commands

- uv run pytest packages/planning/tests/test_installer.py -q
- uv run python scripts/check/check_planning_surfaces.py
- uv run agentic-planning-bootstrap summary --format json
- uv run agentic-planning-bootstrap report --format json

## Required Tools

- uv

## Completion Criteria

- The minimum routine-recovery question set is checked in and small enough to guide future planning-surface cleanup.
- The first slice leaves behind one explicit smaller-agent-safe recommendation or one landed narrow clarification target.
- The resulting artifact makes it cheaper to answer routine planning recovery questions from compact surfaces than from raw planning prose.

## Smaller-Agent Handoff

- Use this plan as the sole execution contract; do not infer a broader redesign from the parent lane.
- Read only the minimum relevant surfaces: `AGENTS.md`, `TODO.md`, this execplan, `ROADMAP.md` lane stub, `agentic-planning-bootstrap summary --format json`, `agentic-planning-bootstrap report --format json`, and the directly touched planning docs/tests.
- Prefer proving ambiguity with one or two ordinary-work examples rather than a broad theory pass.
- If one compact clarification target is clearly dominant, implement only that target and its narrow tests/docs in this slice.
- If no single target is clearly dominant, stop after the audit and routine-recovery question set, then route the follow-on candidate back into `ROADMAP.md`.

## Execution Summary

- Outcome delivered: Added a compact routine-planning-recovery question set to the default-path contract and enforced it in the planning-surface checker.
- Validation confirmed: `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`; `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-planning-bootstrap summary --format json`; `uv run agentic-planning-bootstrap report --format json`
- Follow-on routed to: `ROADMAP.md`
- Resume from: the `planning-surface-clarity-routine-recovery` roadmap lane

## Drift Log

- 2026-04-17: Promoted the top-priority planning-surface-clarity lane into an active first slice and shaped it explicitly for smaller-agent handoff.
- 2026-04-17: Tightened the default-path contract so routine planning recovery has one compact question set and one guarded front-door route.
