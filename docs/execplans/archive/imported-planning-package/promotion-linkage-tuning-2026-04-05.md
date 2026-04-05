# Promotion Linkage Tuning

## Goal

- Refine the promotion-linkage checks so they still catch drift but stop flagging legitimate active work that already has clear repo-local justification.

## Non-Goals

- Remove cross-surface linkage checks entirely.
- Relax the checker into allowing vague or ungrounded active work.
- Broaden this into a general checker redesign.

## Active Milestone

- Status: completed
- Scope: inspected the current promotion-linkage heuristic, tuned it against the self-hosted false-positive case, and proved the new behavior with focused tests.
- Ready: false
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed execplan now that the tuned heuristic has passed focused verification.

## Blockers

- None.

## Touched Paths

- `scripts/check/`
- `bootstrap/scripts/check/`
- `tests/`
- `README.md`
- `docs/execplans/README.md`

## Invariants

- Active work should still show a visible promotion signal somewhere in the checked-in planning surfaces.
- The checker should prefer advisory precision over broad noisy heuristics.
- Repo-local reasoning in `Why now`, the plan title, or roadmap candidate wording should all be allowed to satisfy linkage when they clearly describe the same thread.
- The planning contract remains schema-light and file-native.

## Validation Commands

- `uv run pytest`
- `uv run ruff check .`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-planning-bootstrap doctor --target .`

## Completion Criteria

- The self-hosted false-positive case no longer trips promotion-linkage drift.
- Cross-surface linkage checks still catch obviously ungrounded active work.
- Tests cover the tuned heuristic and any new accepted evidence for linkage.

## Drift Log

- 2026-04-05: Plan created after repeated self-hosted use surfaced promotion-linkage false positives on legitimate active work.
- 2026-04-05: Accepted clearer causal evidence in `Why now` as sufficient linkage, not just explicit signal/trigger vocabulary.
- 2026-04-05: Added both an acceptance test for the self-hosted causal-reason case and a guardrail test for vague activation.
