# Collaboration Safety

Use these rules when multiple agents or contributors are working through git.

- Keep `memory/current/` and other current-state files compact.
- Archive execplans aggressively once they stop affecting future execution.
- Prefer feature-scoped execplan files over growing shared hot files.
- Do not edit generated routing docs under `tools/` by hand; update the manifest source and rerender.
- Keep root planning and memory installs authoritative for monorepo operation.
- Let local pre-commit hooks handle formatting and lint; keep full test execution in CI or explicit validation runs.
- When pre-commit rewrites files, restage them and rerun the commit instead of fighting the formatter.
- Record meaningful follow-up work in planning or memory instead of leaving it in chat-only residue.