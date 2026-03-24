# Checked-in Skills

This directory contains checked-in core memory skills installed by the bootstrap payload.

The shipped core skills are:

- `memory-hygiene`
- `memory-capture`
- `memory-upgrade`
- `memory-refresh`
- `memory-router`

Use these as shared building blocks for repo-local memory work.

When a repository needs a local memory workflow beyond these, add a new sibling skill under `memory/skills/` instead of editing the shared core skills unless the reusable shared procedure itself changed.

Keep repo-specific skills procedural and concise. Put durable repo facts in `/memory`, then have the skill operate on those files.
Only put memory-facing skills here. General non-memory skills belong elsewhere.
When both a checked-in repo skill and a runtime-local mirrored copy exist, treat the checked-in copy as authoritative.

Ownership boundary:

- the shipped core skill directories in this folder are product-managed and may be replaced on upgrade
- repo-specific memory skills should be added as new sibling directories here
- if a local workflow must survive upgrades, do not customise the shipped core skill directories in place
