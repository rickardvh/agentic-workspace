# Environment And Recovery Contract

This page records the compact default path for environment and recovery work in this repo.

Use it when normal work is blocked by repo-state ambiguity, interrupted bootstrap, lifecycle warnings, or a local environment that no longer matches the checked-in contract.

## Purpose

- Keep recovery ordered and cheap.
- Prefer one canonical path over scattered troubleshooting prose.
- Make the normal remediation route queryable through workspace defaults as well as readable in docs.

## Ordered Recovery Path

1. Inspect the current workspace state:
   - `agentic-workspace status --target ./repo`
   - `agentic-workspace doctor --target ./repo`
2. Reconfirm the default operating contract:
   - `agentic-workspace defaults --format json`
   - `agentic-workspace config --target ./repo --format json`
3. If the issue is package-contract freshness rather than repo-owned customization, refresh the shipped contract:
   - `uv run agentic-planning-bootstrap upgrade --target .`
   - `uv run agentic-memory-bootstrap upgrade --target .`
4. Re-run the narrowest proving lane for the touched surface:
   - workspace CLI changes -> `uv run pytest tests/test_workspace_cli.py`
   - planning package changes -> `uv run pytest packages/planning/tests/test_installer.py`
   - memory package changes -> `uv run pytest packages/memory/tests/test_installer.py`
   - cross-boundary maintainer work -> `make maintainer-surfaces`
5. If bootstrap or adopt work still requires judgment, follow the checked-in handoff:
   - `llms.txt` for the external-agent entry surface
   - `.agentic-workspace/bootstrap-handoff.md` when bootstrap says review is still needed

## What This Contract Covers

Use this contract for:

- interrupted install, adopt, or upgrade work
- repo-state ambiguity after lifecycle commands
- warnings about missing shared workspace files or managed surfaces
- uncertainty about the correct next proving lane
- restart after a broken or partial maintenance pass

Do not stretch it into:

- package-specific domain troubleshooting
- broad incident response
- a replacement for package READMEs or maintainer check docs

## Recovery Rules

- Prefer `agentic-workspace` as the public recovery entrypoint.
- Treat `status` and `doctor` as the first inspection lane, not direct file spelunking.
- Use `defaults` and `config` when the question is “what is the normal contract here?” rather than “what failed?”
- Distinguish package drift from repo-local warnings:
  - package drift means the shipped payload is stale relative to checked-in package source
  - repo-local warnings may still be expected customization, nested-repo noise, or optional-surface absence
- Re-run only the narrowest validation that can prove the recovery worked.
- If recovery still needs human judgment, route through the checked-in handoff surfaces instead of chat-only interpretation.

## Relationship To Other Docs

- [`docs/default-path-contract.md`](docs/default-path-contract.md) says which route is primary.
- [`docs/init-lifecycle.md`](docs/init-lifecycle.md) explains the init/adopt state machine and handoff signals.
- [`docs/delegated-judgment-contract.md`](docs/delegated-judgment-contract.md) explains what the agent may decide locally during recovery and when it must escalate.

This doc owns the ordered recovery path itself.
