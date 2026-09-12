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
Use `.agentic-workspace/skills/workspace-startup/SKILL.md` as the canonical Agentic Workspace procedure.

If host-native skill discovery is unavailable, read that skill before other package-owned AW surfaces. Repository and local instructions/config remain policy and constraints; current owner state/evidence remains source-owned. The skill explains how to use the configured Rust-backed tools when executable AW is available and how to degrade conservatively when it is not.
<!-- agentic-workspace:workflow:end -->
