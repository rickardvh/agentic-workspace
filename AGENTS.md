# Agent Instructions

Authority marker:

- authority: adapter
- canonical_source: `.agentic-workspace/config.toml` and the configured AW startup router
- safe_to_edit: true
- refresh_command: null

Source checkout preparation: run `cargo build --locked --workspace --bins` before
first use and after Rust or bundled contract/payload changes. Build both native
binaries together; do not substitute the former Python host if either is missing.

Repository completion requirements:

- Changes to structured startup, routing or query contracts must include current
  generated adapter surfaces and their applicable validation before completion.
- Prefer committing after the bounded proof lane passes; keep the current Planning
  milestone truthful through its owner when this work uses Planning.
- Before claiming a lane complete, distinguish validation, issue completion,
  intent satisfaction and total operating cost. Route actionable dogfood friction
  through its current owner and retain knowledge only when it prevents rediscovery.
  Required reconciliation cannot be replaced by a successful current-state query.
- For material system-direction changes, prefer current source-owner reconciliation.
  Preserve unresolved source admissions; do not advance trust revisions merely
  because HEAD changed or substitute direct edits to interpreted owner state.

<!-- agentic-workspace:workflow:start -->
Use `.agentic-workspace/skills/workspace-startup/SKILL.md` as the canonical Agentic Workspace procedure.

If host-native skill discovery is unavailable, read that skill before other package-owned AW surfaces. Repository and local instructions/config remain policy and constraints; current owner state/evidence remains source-owned. The skill explains how to use the configured Rust-backed tools when executable AW is available and how to degrade conservatively when it is not.
<!-- agentic-workspace:workflow:end -->

If you implemented or materially changed a PR, do not review or approve it yourself
and do not spawn or direct a reviewer to do so. After implementation or review
fixes, report `ready for independent review` and stop. An externally initiated
reviewer uses `tools/skills/pr-review-recheck/SKILL.md`; issue shaping and ordinary
review feedback do not constitute implementation custody.
