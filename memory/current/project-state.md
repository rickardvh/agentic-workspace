# Project State

## Status

Active

## Scope

- Lightweight current overview for `agentic-memory-bootstrap`.

## Applies to

- `AGENTS.md`
- `README.md`
- `memory/index.md`
- `memory/system/SKILLS.md`
- `memory/system/WORKFLOW.md`
- `memory/system/VERSION.md`
- `memory/system/UPGRADE.md`
- `bootstrap/README.md`

## Load when

- Starting work and needing a short current overview.
- Returning to the repository after a break.

## Review when

- The product boundary changes.
- The current focus, recent meaningful progress, or blockers change materially.
- Main orientation docs move or change role.

## Current focus

- Keep the always-read surface small: `AGENTS.md` plus `memory/index.md` by default, with other docs loaded on demand.

## Recent meaningful progress

- Removed task-management guidance from the core payload and installer.
- Repositioned `memory/current/project-state.md` as the overview note rather than a planning surface.
- Shipped the first bundled product skill set for memory and bootstrap workflows.
- Removed repo-local Beads and task-tracking expectations from this source repository.
- Promoted `memory/current/task-context.md` as the checked-in current-work compression note.
- Added agent-facing memory ergonomics to the CLI for current-memory inspection, routing, sync suggestions, and payload verification.
- Clarified that the base system must remain understandable and maintainable even when skills are unavailable.
- Clarified that `skills/` should be limited to bundled bootstrap-lifecycle skills.
- Added checked-in core memory skills under `memory/skills/` so repo-local memory operations ship in the payload rather than only in the bundled product skill catalogue.
- Added `bootstrap-populate` as the conservative post-adoption skill for filling new current-memory files from repo evidence.
- Shifted the product model toward bundled auto-discoverable skills, with manual installation only as fallback guidance.
- Trimmed `AGENTS.md`, `memory/system/WORKFLOW.md`, and `memory/index.md` toward a lower-token, skill-first operating surface.
- Hardened bootstrap adoption so fresh current-memory seed notes are audit-clean immediately.
- Added `agentic-memory-bootstrap prompt populate` and made the post-adoption populate handoff explicit in the CLI and skill docs.
- Tightened AGENTS patch guidance and optional `check-memory` append messaging.
- Trimmed the always-read contract further so installed agents start from `AGENTS.md` plus `memory/index.md`, with workflow policy loaded only on demand.
- Tightened the local contract to prefer targeted CLI checks over broad file re-reading when they answer the question faster.
- Clarified that package version bumps are required for Git-based tool installs to receive updates via `uv tool upgrade`.
- Added first-class `memory/manifest.toml` support so routing and freshness checks can use typed note metadata and file-trigger hints.
- Switched the recommended bootstrap entry path from installed-product-first prompts to `uvx` no-install execution, with bundled skills treated as optional when already visible in the runtime.
- Added a temporary `memory/bootstrap/` workspace with local install, populate, upgrade, and cleanup skills so prompt-driven lifecycle work can hand off to repo-local skills and then remove the workspace.
- Hardened the freshness audit so temporary `memory/bootstrap/` files are ignored and the recurring-failures starter note is audit-clean on install.

## Blockers

- None currently noted.

## High-level notes

- Optional local scratch conventions are outside the core bootstrap contract.
- `memory/current/project-state.md` is the overview note; `memory/current/task-context.md` is the current-work compression note.
- Skills are the execution layer for repeatable memory workflows, not the storage layer for durable repo knowledge.
- The bundled skill catalogue is now intended for bootstrap lifecycle work, while `memory/skills/` carries the shared day-to-day memory-operation skills.
- `memory/system/WORKFLOW.md` is now a compact policy shim rather than a workflow handbook.
- `memory/manifest.toml` is the emerging machine-readable companion to `memory/index.md` for typed note metadata, routing hints, and freshness triggers.

## Failure signals

- The overview becomes a task list instead of a short current-state note.
- Shared workflow guidance drifts back into `AGENTS.md` instead of `memory/system/WORKFLOW.md`.

## Verify

- Read `memory/index.md` and confirm the routing still matches the memory structure.
- Confirm `README.md`, `AGENTS.md`, and the relevant `memory/system/` docs still exist and remain the correct orientation set.

## Verified against

- `AGENTS.md`
- `README.md`
- `memory/index.md`
- `memory/system/SKILLS.md`
- `memory/system/WORKFLOW.md`
- `memory/system/VERSION.md`
- `memory/system/UPGRADE.md`
- `bootstrap/README.md`

## Last confirmed

2026-03-19 during bootstrap audit hardening
