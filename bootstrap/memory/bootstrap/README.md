# Temporary Bootstrap Workspace

This directory is a temporary operator workspace created by `agentic-memory-bootstrap` during install and populate flows.

Use the local skills under `.agentic-memory/bootstrap/skills/` to finish install and populate bootstrap lifecycle work:

- `install`
- `populate`
- `cleanup`

`.agentic-memory/bootstrap/` is bootstrap-managed and may be recreated by later installs or upgrades.
It is not a home for day-to-day repo procedures or durable repo knowledge.

Upgrade work is now handled by the permanent packaged `bootstrap-upgrade` skill instead of this temporary workspace.
When bootstrap work is complete, prefer `agentic-memory-bootstrap bootstrap-cleanup --target <repo>`. The `cleanup` skill is the repo-local fallback for install and populate cleanup.
