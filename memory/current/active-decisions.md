# Active Decisions

## Status

Active

## Scope

- Current high-impact technical and operational decisions for `agentic-memory-bootstrap`.

## Applies to

- `bootstrap/`
- `README.md`
- `AGENTS.md`
- `memory/system/WORKFLOW.md`
- `memory/system/SKILLS.md`
- `memory/system/VERSION.md`
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
- Keep repo-local scope and guardrails in `AGENTS.md`; keep reusable operating rules in `memory/system/WORKFLOW.md`.
- Keep skills optional and specialised; the core operating model must remain usable from checked-in docs alone.

## How to recognise it

- You are making a trade-off that affects multiple subsystems.
- You need to know which current boundary or contract is intentional.

## Verify

- Check the active architecture docs, contracts, or decision records referenced in `## Applies to`.
- Confirm that older decisions have been moved out if they are no longer current.

## Verified against

- `AGENTS.md`
- `bootstrap/README.md`
- `src/repo_memory_bootstrap/cli.py`
- `src/repo_memory_bootstrap/installer.py`
- `memory/system/SKILLS.md`
- `memory/system/WORKFLOW.md`
- `memory/system/VERSION.md`
- `README.md`

## What to do

- Keep this file current and compact.
- Prefer one line per active decision unless more detail is required for safe implementation.

## Current decisions

- `bootstrap/` is the source of truth for installed payload files; packaging should mirror it rather than fork from it.
- Shared operating rules belong in `memory/system/WORKFLOW.md`; `AGENTS.md` should stay local, short, and repo-specific.
- The bootstrap product boundary is memory-only and task-system agnostic.
- `memory/current/project-state.md` is a lightweight overview file and must not become a task list.
- `memory/current/task-context.md` is the checked-in current-work compression note and must not become a backlog, detailed plan, or history log.
- Durable shared knowledge must stay in checked-in files; repeatable bounded workflows over that knowledge should be implemented as skills.
- Completed transitions and operational residue should not stay here once they stop changing implementation choices.
- `upgrade` may replace shared repo-agnostic files automatically, but must continue to treat `AGENTS.md` and customised starter notes conservatively.
- Skills are bundled product assets for specialised procedures and should stay outside the mandatory bootstrap payload.
- The base memory system must remain understandable and usable even when skills are unavailable.
- The default always-read surface should stay as close as possible to `AGENTS.md` plus `memory/index.md`, with workflow and current-context docs loaded only when needed.
- Repositories that have checked-in `memory/skills/` should tell agents to scan that directory during setup and use a matching skill before inventing a new memory procedure.
- Machine-readable memory metadata should live in `memory/manifest.toml` as an optional companion to `memory/index.md`, not as a replacement for the human-readable routing layer.
- The product should distinguish canonical checked-in docs from assistive memory explicitly, with manifest metadata and audits making that boundary enforceable instead of purely conventional.
- Bundled product skills should stay limited to bootstrap lifecycle work; shared day-to-day memory workflows should ship as checked-in skills under `memory/skills/`, with repo-specific sibling skills added there when needed.
- Temporary bootstrap lifecycle completion can live in a bootstrap-managed `memory/bootstrap/` workspace for install and populate work, which should be removed after that work is complete.
- Conservative bootstrap removal should use a real CLI uninstall path, with any remaining repo-local memory content handled as manual review rather than blind deletion.
- The old checked-in `memory/system/UPGRADE.md` runbook is obsolete; upgrade guidance now lives in the CLI-driven upgrade flow plus the permanent packaged `bootstrap-upgrade` skill.
- Prompt generation should emit one no-install runner command: prefer `uvx` when available and otherwise fall back to `pipx run`.
- `memory/system/` and the shipped core skill directories under `memory/skills/` are product-managed and upgrade-replaceable; repo-specific durable knowledge and reusable local procedures should live outside those files.

## Last confirmed

2026-04-02 during checked-in memory-skill discovery hardening
