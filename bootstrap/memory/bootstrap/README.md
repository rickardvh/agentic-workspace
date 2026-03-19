# Temporary Bootstrap Workspace

This directory is a temporary operator workspace created by `agentic-memory-bootstrap` during install or upgrade flows.

Use the local skills under `memory/bootstrap/skills/` to finish bootstrap lifecycle work:

- `install`
- `populate`
- `upgrade`
- `cleanup`

`memory/bootstrap/` is bootstrap-managed and may be recreated by later installs or upgrades.

When bootstrap work is complete, use `cleanup` to remove this temporary workspace.
