# Skills Model

## Purpose

This document defines the boundary between checked-in memory, checked-in repo skills, and bundled product skills in `agentic-memory-bootstrap`.

## Layer boundary

Use three layers inside a repo:

- checked-in files = durable shared knowledge and lightweight shared context
- temporary bootstrap workspace under `memory/bootstrap/` = bootstrap-managed lifecycle workspace during install or upgrade
- checked-in repo skills under `memory/skills/` = repo-visible repeatable procedures whose primary purpose is operating on checked-in memory or maintaining the repo's memory system
- bundled product skills = bootstrap lifecycle help such as adoption, populate, and upgrade
- runtime-local mirrored skill copies = disposable caches for runtimes that copy or mirror skills locally

The bootstrap contract remains the always-on minimal file structure that keeps the system understandable even without skills. `memory/bootstrap/` is temporary operator workspace, not a durable knowledge surface.

## Keep in checked-in docs

Keep these in `AGENTS.md`, the repo's chosen task system, or `/memory`:

- repo purpose
- local constraints and guardrails
- architecture facts and invariants
- milestone or task state
- lightweight current-task context that should stay visible in checked-in memory

If something is a durable fact about the repo, store it in files.

The core operating model must remain visible and useful even when skills are unavailable.

## Checked-in core skills

The payload ships these checked-in core memory skills under `memory/skills/`:

- `memory-hygiene`
- `memory-capture`
- `memory-refresh`
- `memory-router`

Treat them as shared repo-local building blocks.

- Keep them repo-agnostic and conservative.
- Upgrade may replace them as part of the shared payload.
- Do not put repo-specific facts into these core skills.
- Do not customise these directories in place for repo-local behaviour you expect to preserve across upgrades.

## Repo-specific skills

When a repository needs a memory workflow beyond the shared core, create a new checked-in sibling skill under `memory/skills/` instead of editing the shared core skills in place.
Do not use `memory/skills/` for general coding, planning, review, deployment, or other non-memory workflows whose primary purpose is not operating on checked-in memory.

Use a repo-specific skill when the behaviour is:

- reusable across tasks or repos
- optional rather than mandatory
- triggerable from a clear request
- procedural and memory-operational
- too detailed for the core repo contract

If something is a repeatable workflow over checked-in memory files, it is a strong skill candidate.

Good repo-specific fits:

- domain-specific capture flows
- validation-specific refresh flows
- release-memory checks
- architecture-note maintenance for local subsystems

Keep repo-specific skills small, procedural, and explicitly grounded in checked-in memory.

The safe split is:

- shared product-managed skills = the shipped core directories already under `memory/skills/`
- repo-managed skills = new sibling directories a repository adds under `memory/skills/` for repo-specific memory workflows
- runtime-local caches = mirrored copies that should follow checked-in skills rather than override them

Upgrades may replace the shared product-managed skill directories, but should not touch added repo-specific sibling skills.
When both a checked-in repo skill and a runtime-local mirrored copy exist, treat the checked-in repo skill as authoritative.

## Temporary bootstrap workspace

The payload may create a temporary bootstrap workspace under `memory/bootstrap/` during install or upgrade.

- use it for bootstrap lifecycle completion only
- do not store durable repo knowledge there
- do not add repo-specific day-to-day workflows there
- remove it after bootstrap work is complete

## Bundled product skills

Bundled product skills should stay limited to bootstrap lifecycle operations:

- `bootstrap-adoption`
- `bootstrap-populate`
- `bootstrap-upgrade`
- `bootstrap-uninstall`

Do not use bundled product skills as the main place for day-to-day repo memory behaviour.

## Avoid first

Do not start with fuzzy skills that overlap heavily with built-in agent behaviour, such as:

- generic planning
- generic coding
- vague "use memory better" instructions

## Distribution stance

For now:

- keep bootstrap lifecycle skills bundled with the product under `skills/`
- ship day-to-day memory skills as checked-in repo skills under `memory/skills/`
- treat checked-in `memory/skills/` files as the source of truth for repo-local memory workflows
- treat any runtime-local mirrored copies as disposable caches
- keep the mandatory bootstrap payload understandable and useful without any skill runtime support
- during development, treat the repo's checked-in files as canonical and any packaged or mirrored copies as potentially stale until explicitly refreshed
