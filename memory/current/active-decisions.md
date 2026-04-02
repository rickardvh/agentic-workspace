# Active Decisions

## Status

Active

## Scope

- Current high-impact technical and operational decisions for `agentic-memory-bootstrap`.

## Applies to

- `bootstrap/`
- `AGENTS.md`
- `.agentic-memory/WORKFLOW.md`
- `src/repo_memory_bootstrap/cli.py`
- `src/repo_memory_bootstrap/installer.py`

## Load when

- Choosing implementation strategy across major subsystems.
- Deciding which source of truth to trust during a refactor.

## Review when

- Architecture boundaries change.
- Public interfaces or core operating modes change.

## Failure signals

- Conflicting plans reference different sources of truth.
- A change proposal depends on an unconfirmed default or stale assumption.

## Rule or lesson

- Record only live decisions that materially affect implementation choices right now.
- Move a decision into `memory/decisions/` once it no longer changes implementation choices and is only worth keeping as durable rationale.
- Preserve decisions at the level of consequence or still-relevant rejected-path boundaries, not meeting history.
- Keep repo-local scope and guardrails in `AGENTS.md`; keep reusable operating rules in `.agentic-memory/WORKFLOW.md`.
- Keep skills optional and specialised; the core operating model must remain usable from checked-in docs alone.

## Verify

- Check the files in `## Applies to`.
- Move older decisions out once they stop affecting implementation choices.

## Verified against

- `AGENTS.md`
- `src/repo_memory_bootstrap/cli.py`
- `src/repo_memory_bootstrap/installer.py`
- `.agentic-memory/WORKFLOW.md`

## What to do

- Keep this file current and compact.

## Current decisions

- `bootstrap/` is the source of truth for installed payload files; packaging should mirror it rather than fork from it.
- Shared operating rules belong in `.agentic-memory/WORKFLOW.md`; `AGENTS.md` should stay local, short, and repo-specific.
- The bootstrap product boundary is memory-only and task-system agnostic.
- `memory/current/project-state.md` is a lightweight overview file and must not become a task list.
- `memory/current/task-context.md` is the checked-in current-work compression note and must not become a backlog, detailed plan, or history log.
- Durable shared knowledge must stay in checked-in files; repeatable bounded workflows over that knowledge should be implemented as skills.
- `upgrade` may replace shared repo-agnostic files automatically, but must continue to treat `AGENTS.md` and customised starter notes conservatively.
- The default always-read surface should stay as close as possible to `AGENTS.md` plus `memory/index.md`, with workflow and current-context docs loaded only when needed.
- Shared guidance should stay in a dedicated bootstrap-managed `.agentic-memory/` surface; `AGENTS.md` should only carry the managed workflow pointer plus repo-local contract text.
- Machine-readable memory metadata should live in `memory/manifest.toml` as an optional companion to `memory/index.md`, not as a replacement for the human-readable routing layer.
- Shared day-to-day memory workflows should ship under `.agentic-memory/skills/`, while repo-specific memory procedures can live under `memory/skills/`.
- `.agentic-memory/` and the shipped core skill directories under `.agentic-memory/skills/` are product-managed and upgrade-replaceable; repo-specific durable knowledge and reusable local procedures should live outside those files.
- `upgrade` should migrate legacy `memory/system/`, `memory/bootstrap/`, and shipped `memory/skills/` installs into `.agentic-memory/` by default so the legacy layout can be retired cleanly.

## Last confirmed

2026-04-02 during managed-root migration work
