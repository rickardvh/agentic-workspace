# Planning Beta-Readiness Review

## Goal

- Run one bounded review pass that decides whether Agentic Planning should still be labeled `alpha`, tightens the maturity statement to match current evidence, and routes any remaining beta-blocking gaps into real planning surfaces.

## Non-Goals

- Re-architect planning in this slice.
- Implement every maturity blocker that the review may surface.
- Change Agentic Planning to `beta` unless the current package state actually justifies that move.

## Intent Continuity

- Larger intended outcome: Make long-horizon planning direction and maturity claims reflect current product reality instead of stale historical wording.
- This slice completes the larger intended outcome: no
- Continuation surface: `ROADMAP.md`

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `ROADMAP.md`
- Activation trigger: The review confirms one or more still-real beta blockers or identifies that the maturity statement needs a bounded follow-through slice.

## Active Milestone

- Status: completed
- Scope: inspect the current planning contract, recent planning hardening work, and maturity statement; write one bounded review artifact; align `docs/maturity-model.md`; keep only still-real blockers queued.
- Ready: yes
- Blocked: no
- optional_deps: none

## Immediate Next Action

- Archive this completed review slice and leave the next planning-facing candidate queued in `ROADMAP.md`.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `docs/maturity-model.md`
- `docs/reviews/`
- `docs/execplans/`

## Invariants

- Keep the review bounded and evidence-backed.
- Do not promote speculative blockers into `ROADMAP.md`.
- If planning remains `alpha`, say why in current product terms rather than historical migration language.

## Validation Commands

- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- One review artifact records the maturity judgment and supporting evidence.
- `docs/maturity-model.md` either confirms or updates the planning label and explains it in current terms.
- `ROADMAP.md` contains only still-real follow-on candidates derived from the review.
- This execplan is archived after the planning surfaces validate cleanly.

## Drift Log

- 2026-04-09: Plan created to turn the planning maturity label from stale doctrine into an evidence-backed review and queue update.
- 2026-04-09: Review completed; planning remains `alpha` for current follow-through and recovery-contract reasons, and the next bounded candidates stay queued in `ROADMAP.md`.
