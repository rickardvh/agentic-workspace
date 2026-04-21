# Bootstrap Intent And Handoff Tranche

## Goal

- Ship the next bounded front-door bootstrap contract so the workspace CLI classifies repo state more explicitly, chooses conservative defaults with less user input, and provides one canonical external-agent handoff plus next-action surface.

## Non-Goals

- Rewriting package-local lifecycle implementations.
- Turning the handoff surface into a second broad README.
- Expanding bootstrap into a hidden aggressive auto-installer for ambiguous repos.

## Active Milestone

- Status: completed
- Scope: root workspace bootstrap classification/reporting, default-path docs, package-facing bootstrap guidance, and regression coverage for the new contract.
- Ready: ready
- Blocked: false
- optional_deps: None.

## Immediate Next Action

- Archive this completed tranche and remove its active TODO entry.

## Blockers

- None.

## Touched Paths

- [src/agentic_workspace/cli.py](src/agentic_workspace/cli.py)
- [tests/test_workspace_cli.py](tests/test_workspace_cli.py)
- [README.md](README.md)
- [docs/default-path-contract.md](docs/default-path-contract.md)
- [docs/init-lifecycle.md](docs/init-lifecycle.md)
- [packages/planning/README.md](packages/planning/README.md)

## Invariants

- Keep the workspace layer as the public lifecycle entrypoint while preserving package-local lifecycle ownership.
- Prefer conservative inference and explicit review over aggressive guessing in ambiguous repos.
- Keep one obvious external-agent handoff surface and avoid duplicating source-of-truth startup guidance.

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py`
- `uv run ruff check src/agentic_workspace tests/test_workspace_cli.py`
- `make maintainer-surfaces`
- `uv run agentic-planning-bootstrap upgrade --target .`
- `uv run agentic-memory-bootstrap upgrade --target .`

## Completion Criteria

- Workspace init/prompt output uses explicit repo-state and user-intent framing rather than only internal lifecycle mode names.
- Automatic conservative policy selection is visible in reports and tests, with safe fallback to handoff/review for ambiguous repos.
- A canonical checked-in external-agent handoff output path exists and the docs route users to it as the default front door.
- Package/root docs describe the same contract without making package-local paths look equally primary.
- Completed: all criteria satisfied on 2026-04-09.

## Drift Log

- 2026-04-09: Initial plan created for the open bootstrap intent/handoff issue cluster (#19-#23).
- 2026-04-09: Completed the tranche with workspace CLI, docs, `llms.txt`, and regression coverage updates.
