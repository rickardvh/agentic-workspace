# Agent Instructions for .agentic-workspace

Authority marker:

- authority: workspace-managed-local-adapter
- canonical_source: `.agentic-workspace/config.toml` and `uv run python scripts/run_agentic_workspace.py start --target . --format json`
- safe_to_edit: false
- refresh_command: `uv run python scripts/run_agentic_workspace.py init --target . --format json` or `uv run python scripts/run_agentic_workspace.py upgrade --target . --format json`

This directory contains Agentic Workspace managed workflow, planning, memory, ownership, and state surfaces.

Before editing inside `.agentic-workspace/`:

- Use `uv run python scripts/run_agentic_workspace.py start --target . --task "<task>" --format json` for routing.
- Use `uv run python scripts/run_agentic_workspace.py summary --target . --format json`, `uv run python scripts/run_agentic_workspace.py implement --changed <paths> --task "<task>" --format json`, and `uv run python scripts/run_agentic_workspace.py proof --changed <paths> --format json` before opening broad raw state.
- Use `uv run python scripts/run_agentic_workspace.py planning ...` and `uv run python scripts/run_agentic_workspace.py memory ...` commands for structured Planning and Memory mutations when a command exists.
- Do not hand-edit structured state such as Planning execplans, Planning state, Memory indexes, ownership ledgers, or config when a package CLI command exists.
- Raw structured edits are only fallback or repair work; after any fallback edit, run `uv run python scripts/run_agentic_workspace.py summary --target . --format json` and `uv run python scripts/run_agentic_workspace.py doctor --target . --modules planning,memory --format json` as applicable.
- If a needed managed-state mutation has no command, route or file an improvement issue for a command-owned path instead of making manual edits routine.
