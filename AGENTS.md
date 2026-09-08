# Agent Instructions

Authority marker:

- authority: adapter
- canonical_source: `.agentic-workspace/config.toml` and the configured AW startup router
- safe_to_edit: true
- refresh_command: null

Source checkout preparation: run `cargo build --locked --workspace --bins` before
first use and after Rust or bundled contract/payload changes. Build both native
binaries together; do not substitute the former Python host if either is missing.

<!-- agentic-workspace:workflow:start -->
Use the main Agentic Workspace operating skill: `.agentic-workspace/skills/workspace-startup/SKILL.md`.

Invocation rule:
1. Use `.agentic-workspace/config.local.toml` `[workspace].cli_invoke` when present.
2. Otherwise use `.agentic-workspace/config.toml` `[workspace].cli_invoke`.
3. Otherwise use the package default `agentic-workspace`.
4. If no CLI invocation works, read `.agentic-workspace/skills/workspace-startup/SKILL.md` before other workspace files.
This generated adapter's configured invocation is `./target/debug/agentic-workspace`. Use it directly for ordinary route commands; do not open raw config files to rediscover it.

Ordinary route:
1. Run exactly `<configured AW invocation> start --target . --task "<task>" --format json` before non-trivial answers, edits, read-only workflow, config, delegation, or action-safety decisions; the ordinary contract is the JSON `decision_packet`, so do not omit `--format json`.
2. Use `start --target . --changed <path> --task "<task>" --format json` when changed paths are known; repeat `--changed` for each path.
3. Follow `decision_packet.status`, `primary_action`, `decision_request`, blockers and `claim_boundary` before raw workspace reads or effects. Supply only the bounded answer/material in an owner-returned request, then rerun `start --input <request.json>` with the same target/task/changed context. Combine required source-read and owner requests in a JSON array.
4. Execute only the exact returned `primary_action` through `invoke --input <action.json>` with the same context and `--format json`; resolve again afterward. Never manufacture an invocation, omit a blocker or use the former Python host to bypass an unavailable native owner. Direct work stays direct when the current contract permits it.
5. When implementing an issue, satisfy the intended end state in the ordinary path; ask for clarification instead of closing with a partial path when the full outcome appears larger than the issue safely permits.

Boundaries:
- Known dedicated Agentic Workspace commands are allowed only when the request maps directly to that command and no takeover, recovery, active-planning, or ambiguous safety decision is needed first.
- Do not bake machine-local AW invocation paths into checked-in generic guidance; concrete commands come from the configured invocation or live router output.
- Treat checked-in `.agentic-workspace/skills` and module skill trees as required operating surfaces, not optional payload mirror content.
- Treat `.agentic-workspace/skills/workspace-startup/SKILL.md` as the shared startup fallback reached through this adapter.
- Use only commands exposed by the configured runtime. Former maintainer/generator tooling is not fallback product authority; unavailable owner outcomes remain explicit gaps.
- Report repo-relative paths, not local absolute paths.
<!-- agentic-workspace:workflow:end -->
