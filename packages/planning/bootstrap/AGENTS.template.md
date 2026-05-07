# Agent Instructions

<!-- agentic-workspace:workflow:start -->
Read `.agentic-workspace/WORKFLOW.md` for shared workflow rules.
<!-- agentic-workspace:workflow:end -->

Keep this file thin. Treat it as the repo-owned startup adapter over the structured workspace surfaces under `.agentic-workspace/`.

## Startup

- Use the effective CLI invocation from `agentic-workspace start --format json` / `.agentic-workspace/config.local.toml` `[workspace].cli_invoke` when present; do not substitute bare `agentic-workspace` when local config names a repo-local invocation.
- Use `<effective-cli> implement --profile tiny --changed <paths> --format json` first when changed paths are already known.
- Use `<effective-cli> start --profile tiny --task "<task>" --format json` for ordinary compact startup context.
- Use `<effective-cli> preflight --format json` when you need bundled takeover or recovery context.
- Use `<effective-cli> defaults --section startup --format json` when startup order or first-contact routing is the question.
- Use `<effective-cli> config --target . --profile tiny --format json` when the configured entrypoint, posture, or workflow obligations matter; use `--profile compact` only when the tiny answer is insufficient.
- Use `<effective-cli> summary --format json` when only active planning or ownership state is the question.
- Open module, planning, memory, or deeper routing files only when the compact answers point there.
- Read package-local `AGENTS.md` only for the package being edited.

## Repo Rules

- Do not bulk-read all planning surfaces.
- Keep package boundaries explicit.
- Preserve package boundaries, package-local versioning, and module CLI entry points for maintainer/debugging work.
- Keep repo-custom workflow obligations in `.agentic-workspace/config.toml`; let `AGENTS.md` stay a compact router.
