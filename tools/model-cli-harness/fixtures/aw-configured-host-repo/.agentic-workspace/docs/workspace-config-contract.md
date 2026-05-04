# Workspace Config Contract

Use `agentic-workspace config --target . --profile compact --format json` for the resolved workspace configuration before reading raw config files.

`config.toml` is repo-owned policy. `config.local.toml` is local runtime posture and must not be treated as shared repo authority.

Prefer compact output for workflow obligations, output posture, delegation posture, proof policy, and closeout settings. Use the full profile only when compact output lacks a field needed for the current decision.
