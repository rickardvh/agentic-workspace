# Checked-in Skills

This directory contains checked-in core memory skills installed by the bootstrap payload.

The shipped core skills are:

- `memory-hygiene`
- `memory-capture`
- `memory-refresh`
- `memory-router`

Use these as shared building blocks for repo-local memory work.

When a repository needs a local memory workflow beyond these, add a new sibling skill under `memory/skills/` instead of editing the shared core skills unless the reusable shared procedure itself changed.

Keep repo-specific skills procedural and concise. Put durable repo facts in `/memory`, then have the skill operate on those files.
