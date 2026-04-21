---
name: memory-upgrade
description: Upgrade the checked-in agentic-memory scaffold for this repository. Use when the user asks to upgrade memory or upgrade agentic-memory and the agent should run the packaged upgrade flow with the recorded source, without broad repo exploration.
---

# Memory Upgrade

This is a checked-in core skill shipped with the payload. Keep it minimal and stable.

Use this skill as the repo-local entrypoint for "upgrade memory".

When invoked, run the packaged upgrade flow for the current repo and stop there unless the tool reports specific manual-review items.

## Workflow

1. Run the packaged upgrade flow for the current repository:
   - prefer `agentic-memory-bootstrap upgrade --target <repo>` when the CLI is already installed and on `PATH`
   - otherwise, use the recorded source with a runner such as `uvx --from <recorded-source> agentic-memory-bootstrap upgrade --target <repo>`
   - if `uvx` is unavailable, fall back to `pipx run --spec <recorded-source> agentic-memory-bootstrap upgrade --target <repo>`
2. Let the tool resolve the installation source from `.agentic-workspace/memory/UPGRADE-SOURCE.toml`.
3. Report manual-review items only when the tool leaves repo-owned files untouched.
4. Verify with the packaged checks that are relevant to the repo.

## Guardrails

- Do not rewrite repo-owned notes such as `.agentic-workspace/memory/repo/current/project-state.md` or `.agentic-workspace/memory/repo/current/task-context.md` unless the user explicitly asks for that follow-up.
- Do not broaden the task into package-manager investigation when the repo already has an installed memory scaffold.
- Do not stop only because the global CLI is unavailable; prefer a runner command from the recorded source before considering any local-checkout-specific fallback.
- Preserve repo-local customisation in `AGENTS.md` and other repo-owned files.
- Do not turn upgrade into a general memory refresh or note-maintenance task.

## Typical outputs

- the shared bootstrap-managed memory scaffold upgraded to the latest version from the recorded source
- a short list of any conservative manual-review items
- verification output from the packaged checks
