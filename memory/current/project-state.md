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
- Keep planner-agnostic interoperability explicit so memory owns durable repo knowledge and planning/status surfaces own active execution state.
- Tighten note ownership, routing sharpness, and current-context discipline so memory helps agents read less, not more.
- Keep bootstrap-managed shared guidance inside product-managed memory files and the workflow pointer block instead of expanding repo-specific `AGENTS.md` prose.

## Recent meaningful progress

- Re-tightened the product boundary so shared skill-discovery guidance now lives in product-managed memory files rather than in upgrade-sensitive `AGENTS.md` prose outside the workflow pointer block.
- Added planner-agnostic interoperability guidance across the shared workflow docs, package READMEs, and routing docs.
- Tightened capture-threshold and anti-pattern guidance around deletion, consolidation, one-home ownership, and keeping user-specific memory out of repo memory.
- Strengthened current-context and active-decision guidance so continuation notes stay temporary and decisions preserve consequence rather than meeting history.
- Tightened stale-note messaging so oversized or old current-state notes explicitly point at semantic drift and planning/status spillover.
- Added a first-class "memory as improvement pressure" model so the package can suggest docs, tests, skills, scripts, or refactor review when memory is compensating for repo friction.
- Added optional manifest hints and soft `doctor`/`sync-memory`/`promotion-report` suggestions for improvement candidates without making the package intrusive in adopting repos.
- Hardened the upgrade skill so it no longer assumes a globally installed `agentic-memory-bootstrap` executable and can fall back to the packaged module entrypoint from a local checkout.
- Realigned the upgrade skill and generated prompt with the recorded-source runner model so fallback prefers `uvx` or `pipx run` from the resolved source instead of assuming a local checkout.
- Fixed package-level hygiene issues: the module version now follows installed package metadata, the CLI exposes `--version`, git change detection times out with a warning, and the repo now has basic CI plus CLI smoke coverage.

## Blockers

- None currently noted.

## High-level notes

- Optional local scratch conventions are outside the core bootstrap contract.
- `memory/current/project-state.md` is the overview note; `memory/current/task-context.md` is optional continuation compression only.
- Current-state notes should stay short: current focus, recent meaningful progress, blockers, and a few high-value notes only.
- Durable facts should have one primary home, with short cross-references instead of duplicated summaries.
- Routing is the primary integration point between planning and memory: planning identifies touched surfaces and memory returns the smallest durable note set.
- Memory should either preserve irreducible durable truth or help the agent suggest upstream repo improvements that make the note smaller.

## Failure signals

- The overview becomes a task list instead of a short current-state note.
- The note starts to read like a ledger, backlog, tranche history, or changelog.
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
- `bootstrap/README.md`

## Last confirmed

2026-04-02 during ownership-boundary hardening for bootstrap-managed files
