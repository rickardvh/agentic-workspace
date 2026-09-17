---
name: memory-reporting
description: Resolve current Memory owner questions and distinguish source-maintenance diagnostics from native operating authority.
---

# Memory Reporting

Follow `.agentic-workspace/skills/workspace-startup/SKILL.md` with the actual Memory
question. Use the configured native invocation for `start --target . --task
"<memory question>" --format json`, then pass exact owner-returned requests to
`invoke`. Report the observed owner answer, its evidence and any unresolved
freshness or admission boundary. Open only the owner-selected detail; a current
query does not authorize cleanup, promotion or a completion claim.

## Source-maintenance diagnostics

When maintaining the Memory package in this source checkout, its separate
maintenance CLI supports `uv run agentic-memory doctor --target . --format json`
and `uv run agentic-memory report --target . --format json`. The package
`check-memory` Make target runs these diagnostics against the repository.
These are maintenance observations, not native AW commands or owner mutations.
Use the returned diagnostic scope and findings when reporting results; do not
infer whole-workspace health, trust freshness or intent satisfaction from exit zero.
