# Import Map

Track history-preserving import provenance for both source repositories.

## Sources

- Memory source repository: `c:/Users/ricka/Documents/src/agentic-memory`
- Planning source repository: `c:/Users/ricka/Documents/src/agentic-planning`

## Target

- Monorepo host: `c:/Users/ricka/Documents/src/agentic-workspace`

## Import Records

### Memory package

- Source repo: `c:/Users/ricka/Documents/src/agentic-memory` (`main`)
- Source anchor commit: `a03a982fbd5b7e3676e7bdd9a4c4aacf295492cf`
- Import method: `git subtree add --prefix=packages/memory src-memory main`
- Target path: `packages/memory/`
- Imported by: GitHub Copilot (GPT-5.3-Codex)
- Imported at: 2026-04-05
- Monorepo import commit: `4430ebe`

### Planning package

- Source repo: `c:/Users/ricka/Documents/src/agentic-planning` (`master`)
- Source anchor commit: `2d4e2aafb21e3343da00fd21a6c3a7ba40a00be6`
- Import method: `git subtree add --prefix=packages/planning src-planning master`
- Target path: `packages/planning/`
- Imported by: GitHub Copilot (GPT-5.3-Codex)
- Imported at: 2026-04-05
- Monorepo import commit: `c265938`

## Notes

- Fill this file in the same change as each package import.
- Keep this map concise and auditable.
- Source remotes configured in monorepo during import: `src-memory`, `src-planning`.
