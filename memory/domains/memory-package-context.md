# Memory Package Context
## Status
Active
## Purpose
Durable context for `packages/memory/`.
## Durable context
- The package stays planning-system agnostic.
- Source of truth is package-local: `src/`, `bootstrap/`, and `tests/`.
- Primary proof stays `packages/memory/tests/` plus payload verification.
- Repeatable inspection belongs in `memory/runbooks/package-context-inspection.md`.
## Monorepo adaptation note
Root ownership now contains the installed memory system. For the owning rationale, load `memory/decisions/installed-system-consolidation-2026-04-05.md` instead of expanding this context note.
## Load when
- Editing files under `packages/memory/`.
## Review when
- The memory package source, payload, or test layout changes materially.
## Failure signals
- The note starts carrying workflow steps instead of package facts.
## Verify
- `packages/memory/README.md`
- `packages/memory/bootstrap/`
- `packages/memory/tests/`
- `memory/runbooks/package-context-inspection.md`
## Last confirmed
2026-04-08 after moving repeatable inspection procedure into a runbook
