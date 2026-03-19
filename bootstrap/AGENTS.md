# Agent Instructions

This file is the local bootstrap contract for agents working in this repository.

Keep it short and repo-specific.

<!-- agentic-memory:workflow:start -->
Read `memory/system/WORKFLOW.md` for shared workflow rules.
<!-- agentic-memory:workflow:end -->

## Before doing work

1. Read `memory/index.md`.
2. Consult the repository's chosen task system or the user's request for what to work on next.
3. Load only the memory files routed by `memory/index.md` that are relevant to the task.
4. Read `memory/system/WORKFLOW.md` only when the shared policy boundary is unclear.
5. Read any repository docs referenced by those files.

Use built-in agent planning and memory for task execution.  
Do not rely on transient chat context when the same knowledge should exist in checked-in files.

`memory/index.md` is the routing layer for task-relevant durable knowledge.  
`memory/system/WORKFLOW.md` is a compact policy shim for the shared operating model.
`memory/system/SKILLS.md` defines how checked-in `memory/skills/` and bundled bootstrap skills should coexist.

Keep durable repo knowledge in checked-in files. Prefer skills for repeatable procedures that operate on that knowledge.
Treat `memory/system/` and the shipped core skills under `memory/skills/` as bootstrap-managed files that may be replaced on upgrade. Put repo-specific durable knowledge in other `/memory` notes and repo-specific procedures in added sibling skills under `memory/skills/`.

## Repo scope

Replace the placeholders below with repository-specific details.

- Project purpose: `<PROJECT_PURPOSE>`
- Key repository docs: `<KEY_REPO_DOCS>`
- Key commands: `<PRIMARY_BUILD_COMMAND>`, `<PRIMARY_TEST_COMMAND>`, `<OTHER_KEY_COMMANDS>`
- Key subsystems: `<KEY_SUBSYSTEMS>`

This section should remain short and high-level.

## Workspace guardrails

- Work from the repository root.
- Do not edit sibling repositories unless explicitly requested.
- Prefer the existing project tooling, layout, and conventions.
- Avoid introducing new tooling or structure unless it clearly improves maintainability.

## Task-system boundary

- This bootstrap does not install or define a task system.
- Use the repository's chosen task system or explicit user request to decide what to work on.
- Use built-in agent planning to execute the current task.

## Optional working notes

Local working notes may be used when helpful, but are not required.

Do not treat local working notes as durable memory. Persist reusable knowledge in `/memory`.
