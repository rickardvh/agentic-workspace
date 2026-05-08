# Agentic Workspace External Install Or Adopt Handoff

Use Agentic Workspace as the lifecycle front door for the repository that contains this file.
This file is only the external install/adopt handoff.
Do not treat it as the normal repo startup surface after bootstrap or adoption.

Target repository:

- the repository you are currently working in

Required steps:

- Prefer an installed `agentic-workspace` CLI from the target repo's environment when available.
- If the CLI is unavailable, install the package into the target repo or its tool environment before running lifecycle commands.
- Treat `uvx` or `pipx run` as temporary/debug fallbacks, not the default host-repo install path.
- For lifecycle work, use agentic-workspace rather than package-specific CLIs unless package-local debugging is required.
- After install or adopt, inspect `agentic-workspace config --target ./repo --format json` to find the canonical repo startup entrypoint.
- For normal work after bootstrap, return to that configured startup file, then inspect `.agentic-workspace/planning/state.toml` and the active execplan only when the active queue points to one.
- When the question is active planning recovery rather than bootstrap, prefer `agentic-workspace summary --format json` before broad planning prose.

Preferred install or adopt intent:

- agentic-workspace defaults --section install_profiles --format json
- agentic-workspace install --target ./repo --preset memory
- agentic-workspace install --target ./repo --preset planning
- agentic-workspace install --target ./repo --preset full
- agentic-workspace install --target ./repo --preset memory --local-only

Choose the smallest preset that matches the target repo. Use `memory` for durable repo knowledge, `planning` for active work continuity, and `full` only when both are explicitly desired. Treat `full` as an example for combined Memory plus Planning, not as the default for every external handoff.

Preferred host-repo update path:

- agentic-workspace upgrade --target ./repo --dry-run --format json
- agentic-workspace upgrade --target ./repo --format json
- agentic-workspace doctor --target ./repo --format json

Additional lifecycle commands:

- agentic-workspace status --target ./repo
- agentic-workspace uninstall --target ./repo --local-only
- agentic-workspace skills --target ./repo --task "<task>" --format json

Package-specific bootstrap CLIs are fallback/debug surfaces for package-local work. For host-repo updates, use the root `agentic-workspace upgrade` path first.

Quick state check:

- agentic-workspace defaults --section startup --format json
- agentic-workspace config --target ./repo --format json
- agentic-workspace summary --format json
- If .agentic-workspace/config.local.toml is present, use the config report to see local machine/runtime posture without treating it as checked-in repo policy.
- If the current agent does not natively use `AGENTS.md`, follow the configured startup file from config; if the CLI is unavailable, fall back to `AGENTS.md` or another supported startup file already present in the repo.

Compact routing docs when present:

- tools/AGENT_QUICKSTART.md
- tools/AGENT_ROUTING.md

Rules:

- Prefer conservative review over replacing repo-owned workflow surfaces in ambiguous repos.
- Keep planning and memory ownership boundaries explicit.
- Use `agentic-workspace ownership --target ./repo --format json` before changing startup or uninstall behavior when you need the current package-owned versus repo-owned surface split.
- Workflow artifact profile: repo-owned.
- `.agentic-workspace/planning/state.toml` and `.agentic-workspace/planning/execplans/` stay authoritative; no extra runtime artifact should carry durable state.
- If bootstrap writes .agentic-workspace/bootstrap-handoff.md, treat that file as the immediate next-action brief before normal work resumes.

Success means:

- the workspace lifecycle runs through agentic-workspace
- the configured startup file remains the ordinary repo startup entrypoint after bootstrap
- the installation surface stays bounded to external install/adopt handoff and aligned with the installed workspace contract
