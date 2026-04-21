# Doctrine Refresh Discipline

## Goal

- Define an explicit maintenance contract for long-horizon doctrine so `docs/agent-os-capabilities.md`, `docs/ecosystem-roadmap.md`, and `docs/maturity-model.md` stay synchronized instead of drifting into overlapping shadow backlogs.

## Non-Goals

- Rewriting the product doctrine in `docs/design-principles.md`.
- Promoting new roadmap candidates beyond this slice.
- Expanding the long-horizon docs into broader strategy essays.

## Active Milestone

- Status: completed
- Scope: doctrine role boundaries, refresh triggers, and consistency rules across the long-horizon docs plus the roadmap queue entry.
- Ready: ready
- Blocked: false
- optional_deps: None.

## Immediate Next Action

- Archive this completed doctrine-refresh slice and remove its active TODO entry.

## Blockers

- None.

## Touched Paths

- [ROADMAP.md](ROADMAP.md)
- [docs/agent-os-capabilities.md](docs/agent-os-capabilities.md)
- [docs/ecosystem-roadmap.md](docs/ecosystem-roadmap.md)
- [docs/maturity-model.md](docs/maturity-model.md)

## Invariants

- Keep `ROADMAP.md` as a bounded queue rather than a doctrine home.
- Keep the capability map, ecosystem stance, and maturity framing distinct.
- Prefer explicit refresh rules over adding more long-horizon narrative.

## Validation Commands

- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- Each long-horizon doctrine page states its role, refresh triggers, and anti-drift rule clearly.
- The docs describe when to update doctrine directly versus when to route concrete next work back into `ROADMAP.md`.
- `ROADMAP.md` no longer lists doctrine refresh discipline as an open candidate.

## Intent Continuity

- Larger intended outcome: Keep the long-horizon doctrine surfaces synchronized and explicitly bounded so future roadmap promotions do not have to rediscover which page owns what.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Execution Summary

- Outcome delivered: Added explicit role boundaries and refresh triggers to the long-horizon doctrine pages and removed the doctrine-refresh candidate from `ROADMAP.md`.
- Validation confirmed: `uv run python scripts/check/check_planning_surfaces.py`
- Follow-on routed to: none
- Resume from: No further action in this slice; promote the next roadmap candidate when long-horizon work is reopened.

## Drift Log

- 2026-04-13: Initial plan created from the roadmap doctrine-refresh candidate.
