# Agentic Workspace Workflow

Use CLI-first orientation before implementation:

1. Run `agentic-workspace summary --target . --format json`.
2. If the task is broad, run `agentic-workspace planning --target . --format json`.
3. Use package lifecycle commands for planning mutations when available.

Do not invent the outer structure of planning records. If a lifecycle command is unavailable, copy a shipped template exactly and edit only content fields.

