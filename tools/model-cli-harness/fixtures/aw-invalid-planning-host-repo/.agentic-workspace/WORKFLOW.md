# Agentic Workspace Workflow

Use CLI-first orientation before implementation:

1. Run `agentic-workspace summary --target . --format json`.
2. If the task is broad, run `agentic-workspace planning --target . --format json`.
3. If the request asks for repo-visible durable state, handoff, continuation, or a plan for future agents, run `agentic-workspace planning --target . --format json` and use its `durable_state_bridge` route before creating files.
4. Use package lifecycle commands for planning mutations when available.

This file is startup/router guidance, not task state. Do not edit it to record task-specific plans, progress, decisions, or handoff notes; durable work state belongs in planning, decomposition, execplan, Memory, issue, or other repo-configured execution surfaces routed by the CLI.

Do not invent the outer structure of planning records. Do not create root `PLAN.md`, `DOC_CLEANUP_PLAN.md`, or similar freehand handoff files unless repo config explicitly routes there. When the user asks to prepare, plan, decompose, hand off, or says not to implement yet, keep writes to planning/decomposition surfaces; do not create product source, package, dependency, schema, or app scaffold files unless explicitly requested. If a lifecycle command is unavailable, copy a shipped template exactly and edit only content fields.
