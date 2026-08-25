<!-- GENERATED FILE: do not edit manually. -->

# Agent Quickstart

> GENERATED STATIC ROUTING ADAPTER. Do not edit manually. Rerender with `python scripts/render_agent_docs.py`.

Generated, non-authoritative helper. It points to compact query surfaces and owns no workflow truth.

## Route

- Read `AGENTS.md` first.
- If changed paths are already known, run `uv run agentic-workspace implement --changed <paths> --format json` first.
- Otherwise, run `uv run agentic-workspace start --task "<task>" --format json` for compact startup context.
- Run `uv run agentic-workspace summary --format json` only when active planning or roadmap state matters.
- Run `uv run agentic-workspace preflight --format json` only when you need bundled takeover or recovery context.
- Run `uv run agentic-workspace report --target . --format json` when you need health, warnings, or section hints.
- For nontrivial GitHub issue work, follow `tools/skills/github-issue-shaping/SKILL.md`, then `tools/skills/github-issue-creation/SKILL.md` only when creation is required.
- For independent external PR review by an agent that did not implement the patch, follow `tools/skills/pr-review-recheck/SKILL.md`; implementation agents addressing feedback must not load it.

## Constraints

- This file is a generated static adapter, not a doctrine or state owner.
- Do not bulk-read all planning surfaces; follow compact query results to the one needed file.
- Keep changing operational truth in structured/queryable surfaces, not in this helper.
