# Pinned Bootstrap Source

## Goal

- Route bootstrap runner prompts through a checked-in source record and surface age-based upgrade pressure without shipping bundled executables.

## Non-Goals

- Build standalone Python executables.
- Rework unrelated planning bootstrap behaviour.
- Mirror the same hardening into `agentic-memory` in this change.

## Active Milestone

- Status: completed
- Scope: add a package-managed planning upgrade source file, use it for prompt/runner generation, and teach doctor to report and age-check the recorded source.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed plan and leave release-tag migration as inactive roadmap follow-on work.

## Blockers

- None.

## Touched Paths

- `.agentic-planning/`
- `bootstrap/`
- `skills/`
- `src/repo_planning_bootstrap/`
- `tests/`
- `README.md`
- `TODO.md`

## Invariants

- The checked-in source record should own bootstrap runner selection instead of scattered hard-coded runner specs.
- Upgrade flows should prefer the repo's checked-in source record.
- The package must remain pure-Python and avoid bundled executables.

## Validation Commands

- `uv run pytest`
- `uv run ruff check .`
- `uv run agentic-planning-bootstrap doctor --target .`
- `uv run agentic-planning-bootstrap prompt install --target .`
- `uv run agentic-planning-bootstrap prompt upgrade --target .`
- `uv run agentic-planning-bootstrap adopt --target .`

## Completion Criteria

- A checked-in source record drives the remote bootstrap source used by planning prompts.
- `doctor` reports the recorded source and warns when its age crosses the configured threshold.
- Repo docs and bundled skills point to the source-record flow instead of scattered hard-coded runner specs.

## Drift Log

- 2026-04-05: Plan created after identifying that floating `uvx`/`pipx` specs can outrun the checked-in planning bootstrap contract.
- 2026-04-05: Switched the planning package to a package-managed `.agentic-planning/UPGRADE-SOURCE.toml` targeting `@master`, taught `doctor` to report source age, and kept immutable release/tag pinning as inactive roadmap follow-on work.
