# Bounded Post-Install Jumpstart Phase

## Goal

- Define the first bounded post-bootstrap jumpstart phase for mature repos so safe install/adopt can deliver visible value sooner without broad repo conversion.

## Non-Goals

- Make `init` more aggressive in ambiguous repos.
- Bulk-import docs into Memory or Planning.
- Build a generic repo analysis pipeline or full migration flow.
- Convert all mature-repo context in one pass.

## Intent Continuity

- Larger intended outcome: make mature-repo adoption feel useful quickly while preserving the conservative safe-install posture.
- This slice completes the larger intended outcome: no
- Continuation surface: `ROADMAP.md`

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `ROADMAP.md`
- Activation trigger: after the bounded jumpstart phase is defined, promote only the remaining discovery-reporting, Memory-seeding, Planning-seeding, and fast-payoff ranking follow-ons that still look bounded and useful.

## Delegated Judgment

- Requested outcome: promote GitHub issue `#48` into an active execplan that defines the first bounded jumpstart phase for mature repos.
- Hard constraints: stay post-bootstrap; keep `init` conservative; avoid bulk import; keep the first slice small and reviewable; preserve explicit safety boundaries.
- Agent may decide locally: the exact surfaced name, which one or two seeded surfaces matter first, how much ranking policy belongs in this slice, and the smallest validation set needed to dogfood it.
- Escalate when: the slice would require widening `init`, introducing broad repository conversion semantics, or building a generic analysis engine instead of a bounded jumpstart phase.

## Active Milestone

- ID: bounded-post-install-jumpstart-phase
- Status: active
- Scope: define the first bounded jumpstart phase for mature repos, including what counts as jumpstart relative to `init` and which one or two surfaces prove visible value first.
- Ready: ready
- Blocked: none
- optional_deps: GitHub issue `#48`

## Immediate Next Action

- Draft the first bounded jumpstart contract shape and identify the smallest visible seed surfaces.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `docs/execplans/bounded-post-install-jumpstart-phase-2026-04-14.md`
- root planning docs and any downstream contract/docs needed after the first slice is shaped

## Invariants

- `init` stays conservative in ambiguous repos.
- Jumpstart happens only after safe install/adopt.
- The first slice stays bounded and reviewable.
- The slice seeds value without pretending to convert the entire repo.

## Contract Decisions To Freeze

- Jumpstart is a post-bootstrap phase, not a more aggressive `init`.
- Jumpstart may seed only a small number of clearly high-value surfaces.
- The first slice should prefer visible value over completeness.
- Broad discovery and ranking stay separate unless they are needed to keep the slice bounded.

## Open Questions To Close

- Which minimal seeded surfaces prove early value most clearly in mature repos?
- Should the first slice define the ranking policy now or defer it to the discovery/reporting follow-on?
- What is the smallest report or artifact needed to make jumpstart auditable without becoming noisy?

## Seed Targets

- Memory seed targets: `docs/delegated-judgment-contract.md`, `docs/resumable-execution-contract.md`, `docs/capability-aware-execution.md`, `docs/execution-summary-contract.md`
- Planning seed targets: `TODO.md`, the active execplan itself, and the current jumpstart discovery report
- Ambiguous/no-action surfaces: `ROADMAP.md` and nested cache warnings from the report surface

## Fast Payoff Ranking

- Prefer the highest-confidence durable contracts first.
- Prefer anti-rediscovery value over prose completeness.
- Keep the seed set small enough to review in one pass.
- Make skipped candidates explicit in the discovery report instead of hiding them inside the seed set.

## Validation Commands

- `python scripts/check/check_planning_surfaces.py`
- `uv run pytest tests`
- `uv run agentic-workspace defaults --format json`

## Completion Criteria

- The repo has one checked-in execplan for the bounded mature-repo jumpstart phase.
- The plan clearly distinguishes post-bootstrap jumpstart from `init`.
- The first visible-value surfaces and the follow-on candidate lanes are explicit enough to guide implementation.

## Execution Summary

- Outcome delivered: none yet.
- Validation confirmed: none yet.
- Follow-on routed to: `ROADMAP.md`
- Resume from: shape the first bounded jumpstart contract and decide whether discovery/reporting needs to stay in the roadmap or enter the active plan.

## Drift Log

- 2026-04-14: Promoted from GitHub issue `#48` after the mature-repo jumpstart tranche was reprioritized ahead of the remaining follow-on items.
- 2026-04-14: Active plan created to define the first bounded post-install jumpstart phase for mature repos.
