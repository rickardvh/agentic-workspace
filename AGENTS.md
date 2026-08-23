# Agent Instructions

Authority marker:

- authority: adapter
- canonical_source: `.agentic-workspace/config.toml` and the configured AW startup router
- safe_to_edit: true
- refresh_command: null

<!-- agentic-workspace:workflow:start -->
Use the main Agentic Workspace operating skill: `.agentic-workspace/skills/workspace-startup/SKILL.md`.

Invocation rule:
1. Use `.agentic-workspace/config.local.toml` `[workspace].cli_invoke` when present.
2. Otherwise use `.agentic-workspace/config.toml` `[workspace].cli_invoke`.
3. Otherwise use the package default `agentic-workspace`.
4. If no CLI invocation works, read `.agentic-workspace/skills/workspace-startup/SKILL.md` before other workspace files.

Ordinary route:
1. Run `<configured AW invocation> start --target . --task "<task>" --format json` before non-trivial answers, edits, read-only workflow, config, delegation, or action-safety decisions.
2. Run `<configured AW invocation> implement --target . --changed <paths> --task "<task>" --format json` when changed paths are already known.
3. Follow the authoritative `decision_packet` action, effects, claim boundary, and routed detail before opening raw `.agentic-workspace` files or running drill-down commands.
4. Treat `communication_contract` as optional selector-backed response-shape detail; ordinary work proceeds from `decision_packet` and expands only when its safety, proof, or detail routes require it.
5. When implementing an issue, satisfy the intended end state in the ordinary path; ask for clarification instead of closing with a partial path when the full outcome appears larger than the issue safely permits.

Boundaries:
- Known dedicated Agentic Workspace commands are allowed only when the request maps directly to that command and no takeover, recovery, active-planning, or ambiguous safety decision is needed first.
- Do not bake machine-local AW invocation paths into checked-in generic guidance; concrete commands come from the configured invocation or live router output.
- Treat checked-in `.agentic-workspace/skills` and module skill trees as required operating surfaces, not optional payload mirror content.
- Treat `.agentic-workspace/skills/workspace-startup/SKILL.md` as the shared startup fallback reached through this adapter.
- Treat `preflight`, `config`, `defaults`, `skills`, `modules`, `ownership`, and `report` as routed drill-down or recovery surfaces, not the ordinary startup loop.
- Report repo-relative paths, not local absolute paths.
<!-- agentic-workspace:workflow:end -->
