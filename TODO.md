# TODO

`TODO.md` is the single source of truth for milestone status, pending work, and short handoff context.

Use it for:

- what is next
- what is in progress
- what is blocked
- what decision is pending

Do not use it for durable technical memory. Put subsystem knowledge, runbooks, invariants, and recurring failures in `/memory`.

Keep this file execution-focused only. Collapse completed detail into short outcome notes.

## Current focus

- Keep repository housekeeping files aligned with current workspace needs.

## Active milestones

### Milestone: Deterministic Upgrade System

Status: done

- [x] Add bootstrap versioning and system docs needed for deterministic upgrades.
- [x] Refactor the installer around file roles and a shared plan engine for install, adopt, doctor, and upgrade flows.
- [x] Add doctor and upgrade commands, structured plan output, and local `AGENTS.md` patch support.
- [x] Update docs and workflow references for the new upgrade model.
- [x] Run CLI smoke tests and collapse this milestone into short outcome notes.

Progress notes:

- 2026-03-17: Reviewed the current installer, bootstrap payload, and workflow split to map where the existing logic still conflates empty bootstrap, live-repo adoption, and upgrades.
- 2026-03-17: Added `memory/system/VERSION.md`, `memory/system/UPGRADE.md`, a marker-based `AGENTS.md` workflow pointer block, and file-role-aware planning for install, adopt, doctor, and upgrade flows.
- 2026-03-17: Added `doctor`, `adopt`, `upgrade`, and `--format json`, plus deterministic upgrade rules for shared files, local entrypoints, starter notes, and append-only fragments.
- 2026-03-17: Verified with `uv run python scripts/check/check_memory_freshness.py`, `uv run agentic-memory-bootstrap doctor --target .`, `uv run agentic-memory-bootstrap upgrade --dry-run --target . --format json`, `uv run agentic-memory-bootstrap adopt --dry-run --target .`, and disposable empty-repo and older-install smoke targets under `.agent-work/`.

### Milestone: Workflow Document Split

Status: done

- [x] Add `memory/system/WORKFLOW.md` to the repo and bootstrap payload as the reusable workflow rules document.
- [x] Slim local and bootstrap `AGENTS.md` so they point to `WORKFLOW.md` instead of embedding shared workflow policy.
- [x] Update docs, installer messaging, and memory notes to reflect the new separation of responsibilities.
- [x] Exclude `memory/system/WORKFLOW.md` from the freshness audit and verify the installer/docs flow still works.

Progress notes:

- 2026-03-17: Reviewed the current bootstrap payload, repo `AGENTS.md`, memory routing docs, installer output, and audit script to identify assumptions that still treat `AGENTS.md` as the primary shared workflow document.
- 2026-03-17: Added `memory/system/WORKFLOW.md` to both the repo and the bootstrap payload, slimmed both `AGENTS.md` entrypoints, and updated routing/docs text so `AGENTS.md` now points to the shared workflow file.
- 2026-03-17: Updated the freshness audit to skip `memory/system/WORKFLOW.md` and verified with `uv run python scripts/check/check_memory_freshness.py` plus `uv run agentic-memory-bootstrap list-files --target .`.

### Milestone: Memory System Hardening

Status: done

- [x] Tighten repo and bootstrap guidance around memory hygiene, routing, cleanup bias, and working-set declaration.
- [x] Update bootstrap templates and scratch templates to standardise note metadata and working-set fields.
- [x] Improve installer safety and UX for explicit nested targets and packaged file preview.
- [x] Run freshness and CLI verification, then collapse this milestone into a short outcome note.

Progress notes:

- 2026-03-17: Reviewed current `AGENTS.md`, `memory/index.md`, bootstrap payload, installer CLI, and freshness audit to separate already-implemented checklist items from remaining gaps.
- 2026-03-17: Added memory cache/cleanup guidance, standardised template metadata including optional `Verified against`, tightened `.agent-work/current-task.md` working-set expectations, and extended the installer with nested-target warnings plus `list-files`.
- 2026-03-17: Verified with `uv run python scripts/check/check_memory_freshness.py`, `uv run agentic-memory-bootstrap list-files --target .`, and `uv run agentic-memory-bootstrap status --target src`.

### Milestone: Git Ignore Baseline

Status: done

- [x] Expand `.gitignore` beyond `.agent-work/` to cover local Python artefacts in this repo.
- [x] Verify the resulting ignore rules match the current workspace state.

Progress notes:

- 2026-03-16: Existing `.gitignore` already ignores `.agent-work/`; repo still exposes local `.venv/` and Python cache artefacts.
- 2026-03-16: `.gitignore` now also ignores `.venv/`, `__pycache__/`, `*.py[cod]`, and common Python tool caches; `git status --short` no longer shows local cache or virtualenv noise.

## Blocked / pending decisions

- None.

## Handoff notes

- No open follow-up for this task.

## Recurring maintenance

- review `/memory`
- prune stale TODO detail
