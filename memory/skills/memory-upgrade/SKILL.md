---
name: memory-upgrade
description: Upgrade the checked-in agentic-memory scaffold for this repository. Use when the user asks to upgrade memory or upgrade agentic-memory and the agent should run the packaged upgrade flow with the recorded source, without broad repo exploration.
---

# Memory Upgrade

This is a checked-in core skill shipped with the payload. Keep it minimal and stable.

Use this skill as the repo-local entrypoint for "upgrade memory".

It should trigger the packaged upgrade flow, not recreate that flow in prose.

## Contract

- run the packaged `agentic-memory-bootstrap upgrade` command for the current repo
- let the tool resolve the installation source from `memory/system/UPGRADE-SOURCE.toml`
- report manual-review items only when the tool leaves repo-owned files untouched
- do not treat upgrade as a general memory-maintenance pass

## Guardrails

- Do not rewrite repo-owned notes such as `memory/current/project-state.md` or `memory/current/task-context.md` unless the user explicitly asks for that follow-up.
- Do not broaden the task into package-manager investigation when the repo already has an installed memory scaffold.
- Preserve repo-local customisation in `AGENTS.md` and other repo-owned files.

## Typical outputs

- the shared bootstrap-managed memory scaffold upgraded to the latest version from the recorded source
- a short list of any conservative manual-review items
- verification output from the packaged checks
