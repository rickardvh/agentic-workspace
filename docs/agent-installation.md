# Agentic Workspace External Install Or Adopt Handoff

Use Agentic Workspace as the lifecycle front door for the repository that contains this file.
This file is only the external install/adopt handoff.
Do not treat it as the normal repo startup surface after bootstrap or adoption.

Target repository:
- the repository you are currently working in

Required steps:
- Do not assume agentic-workspace is already installed; follow the checked-in lifecycle instructions in this repository.
- For lifecycle work, use agentic-workspace rather than package-specific CLIs unless package-local debugging is required.
- After install or adopt, inspect `agentic-workspace config --target ./repo --format json` to find the canonical repo startup entrypoint.
- For normal work after bootstrap, return to that configured startup file, then continue through `TODO.md` and the active execplan only when `TODO.md` points to one.
- When the question is active planning recovery rather than bootstrap, prefer `agentic-workspace summary --format json` before broad planning prose.

Preferred install or adopt intent:
- agentic-workspace install --target ./repo --preset full
- agentic-workspace install --target ./repo --preset full --local-only

Preferred follow-up commands:
- agentic-workspace status --target ./repo
- agentic-workspace doctor --target ./repo
- agentic-workspace uninstall --target ./repo --local-only
- agentic-workspace skills --target ./repo --task "<task>" --format json
- agentic-workspace upgrade --target ./repo

Quick state check:
- agentic-workspace defaults --section startup --format json
- agentic-workspace config --target ./repo --format json
- agentic-workspace summary --format json
- If agentic-workspace.local.toml is present, use the config report to see local capability/cost posture without treating it as checked-in repo policy.
- If the current agent does not natively use `AGENTS.md`, follow the configured startup file from config; if the CLI is unavailable, fall back to `AGENTS.md` or another supported startup file already present in the repo.

Compact routing docs when present:
- tools/AGENT_QUICKSTART.md
- tools/AGENT_ROUTING.md

Rules:
- Prefer conservative review over replacing repo-owned workflow surfaces in ambiguous repos.
- Keep planning and memory ownership boundaries explicit.
- Use `agentic-workspace ownership --target ./repo --format json` before changing startup or uninstall behavior when you need the current package-owned versus repo-owned surface split.
- Workflow artifact profile: repo-owned.
- TODO.md and docs/execplans stay authoritative; no extra runtime artifact should carry durable state.
- If bootstrap writes .agentic-workspace/bootstrap-handoff.md, treat that file as the immediate next-action brief before normal work resumes.

Success means:
- the workspace lifecycle runs through agentic-workspace
- the configured startup file remains the ordinary repo startup entrypoint after bootstrap
- the installation surface stays bounded to external install/adopt handoff and aligned with the installed workspace contract
