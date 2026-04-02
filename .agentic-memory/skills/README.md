# Checked-in Skills

This directory contains checked-in core memory skills installed by the bootstrap payload.

When a repository has checked-in memory skills, treat this directory as part of normal task setup:

- scan this file and the sibling skill directories for a name or description that matches the task
- use the matching checked-in skill before inventing an ad hoc memory procedure
- fall back to normal routed note reading when no skill fits

The shipped core skills are:

- `memory-hygiene`
- `memory-capture`
- `memory-upgrade`
- `memory-refresh`
- `memory-router`

Quick trigger guide:

- `memory-router`: choose the smallest relevant memory note set for the current work
- `memory-refresh`: refresh or tighten existing memory notes after changes
- `memory-capture`: record new durable memory when a task exposed something worth keeping
- `memory-hygiene`: prune, merge, de-duplicate, or sharpen existing memory
- `memory-upgrade`: run the packaged memory upgrade flow for the repository

Use these as shared building blocks for repo-local memory work.

These shipped shared skills are installed under `.agentic-memory/skills/`. When a repository needs a local memory workflow beyond these, add a repo-owned sibling skill under `memory/skills/` instead of editing the shared core skills unless the reusable shared procedure itself changed.

Keep repo-specific skills procedural and concise. Put durable repo facts in `/memory`, then have the skill operate on those files.
Only put memory-facing skills here. General non-memory skills belong elsewhere.
When both a checked-in repo skill and a runtime-local mirrored copy exist, treat the checked-in copy as authoritative.

Ownership boundary:

- the shipped core skill directories in this folder are product-managed and may be replaced on upgrade
- repo-specific memory skills should be added as new sibling directories here
- if a local workflow must survive upgrades, do not customise the shipped core skill directories in place
