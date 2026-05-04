# Agentic Workspace Workflow

Use CLI-first orientation before implementation:

1. Run `agentic-workspace summary --target . --format json`.
2. If the task is broad, use the `execution_readiness` and `decomposition` sections from summary to choose between direct work, decomposition, or an execplan.
3. If the request asks for repo-visible durable state, handoff, continuation, or a plan for future agents, create or continue canonical checked-in Planning state before product files.
4. For planning mutations, prefer package lifecycle commands such as `agentic-planning-bootstrap new-plan`, `promote-to-plan`, and `archive-plan`; if a lifecycle command is unavailable, copy a shipped schema-backed template exactly and edit only content fields.
5. Verify Planning state with `agentic-workspace summary --target . --format json` before stopping or implementing.

This file is startup/router guidance, not task state. Do not edit it to record task-specific plans, progress, decisions, or handoff notes; durable work state belongs in planning, decomposition, execplan, Memory, issue, or other repo-configured execution surfaces routed by the CLI.

Do not invent the outer structure of planning records. Do not create root `PLAN.md`, `DOC_CLEANUP_PLAN.md`, or similar freehand handoff files unless repo config explicitly routes there. When the user asks to prepare, plan, decompose, hand off, or says not to implement yet, keep writes to planning/decomposition surfaces; do not create product source, package, dependency, schema, or app scaffold files unless explicitly requested. For prep-only broad work, the finished output is Planning state plus summary verification; do not add README, HANDOFF, SLICES, package, dependency, source, public, database, schema, or app scaffold files. Do not ask for confirmation instead of leaving durable state when the user already asked you to prepare the repo. Do not route durable Planning state to `.agentic-workspace/planning/records/`; canonical records live under `execplans/` or `decompositions/`.
