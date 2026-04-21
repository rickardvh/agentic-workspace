# Collaboration Safety

Use these rules when multiple agents or contributors are working through git.

Use `docs/maintainer-commands.md` for command lookup and `docs/workflow-contract-changes.md` for compact workflow history; this page is only for concurrent-edit and merge-safety rules.

- Keep `memory/current/` compact and weak-authority. If a fact should survive the current thread, move it into a durable primary home.
- Archive execplans aggressively once they stop affecting future execution.
- Prefer feature-scoped execplan files over growing shared hot files.
- Edit canonical docs directly; edit module-managed `.agentic-workspace/` planning or memory surfaces only through their owning package or managed source.
- Do not edit generated routing docs under `tools/` by hand; update the manifest source and rerender.
- Keep the package-managed memory install authoritative for monorepo operation, and keep planning state authoritative in `.agentic-workspace/planning/state.toml` through the planning package.
- Let local pre-commit hooks handle formatting and lint, and let master-bound commits run tests in the hook as well; keep broader test execution in CI or explicit validation runs.
- When pre-commit rewrites files, restage them and rerun the commit instead of fighting the formatter.
- Record meaningful follow-up work in planning or memory instead of leaving it in chat-only residue.

## Quick Boundary Checks

- Active-now sequencing or next step: planning.
- Durable invariant, rationale, or runbook: memory or canonical docs.
- Shared module workflow support under `.agentic-workspace/`: package-managed surface.
- Rendered `tools/` guidance: generated output, not source.
