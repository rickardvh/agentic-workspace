# Agentic Workspace Workflow

Use CLI-first orientation before implementation:

1. Run `agentic-workspace summary --target . --format json`.
2. If the task is broad, run `agentic-workspace planning --target . --format json`.
3. If the request asks for repo-visible durable state, handoff, continuation, or a plan for future agents, run `agentic-workspace planning --target . --format json` and use its `durable_state_bridge` route before creating files.
4. If the user asks you to prepare broad work for later continuation and does not ask you to implement, create or continue canonical checked-in Planning state now, verify it with summary, then stop. A proposal-only answer is not durable handoff.
5. Use package lifecycle commands for planning mutations when available.

This file is startup/router guidance, not task state. Do not edit it to record task-specific plans, progress, decisions, or handoff notes; durable work state belongs in planning, decomposition, execplan, Memory, issue, or other repo-configured execution surfaces routed by the CLI.

Do not invent the outer structure of planning records. Do not create root `PLAN.md`, `DOC_CLEANUP_PLAN.md`, or similar freehand handoff files unless repo config explicitly routes there. When the user asks to prepare, plan, decompose, hand off, or says not to implement yet, keep writes to planning/decomposition surfaces; do not create product source, package, dependency, schema, or app scaffold files unless explicitly requested. For prep-only broad work, the finished output is Planning state plus summary verification; do not add README, HANDOFF, SLICES, package, dependency, source, public, database, schema, or app scaffold files. Do not ask for confirmation instead of leaving durable state when the user already asked you to prepare the repo. Do not route durable Planning state to `.agentic-workspace/planning/records/`; canonical records live under `execplans/` or `decompositions/`. If a lifecycle command is unavailable, copy a shipped template exactly and edit only content fields.
