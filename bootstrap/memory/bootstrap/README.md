# Temporary Bootstrap Workspace

This directory is a temporary operator workspace created by `agentic-memory-bootstrap` during install or upgrade flows.

Use the local skills under `memory/bootstrap/skills/` to finish bootstrap lifecycle work:

- `install`
- `populate`
- `upgrade`
- `cleanup`

`memory/bootstrap/` is bootstrap-managed and may be recreated by later installs or upgrades.
It is not a home for day-to-day repo procedures or durable repo knowledge.

When bootstrap work is complete, prefer `agentic-memory-bootstrap bootstrap-cleanup --target <repo>`. The `cleanup` skill is the repo-local fallback.
