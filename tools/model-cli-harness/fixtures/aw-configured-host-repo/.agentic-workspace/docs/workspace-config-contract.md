# Workspace Config Contract

Use `agentic-workspace config --target . --format json` for the resolved workspace configuration before reading raw config files.

`config.toml` is repo-owned policy. `config.local.toml` is local runtime posture and must not be treated as shared repo authority.

Prefer the default command output for workflow obligations, output posture, delegation posture, proof policy, and closeout settings. Use `--select <field>` for exact detail or `--verbose` only for broad diagnostics.
