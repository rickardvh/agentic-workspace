# Agent Instructions

This file is the local bootstrap contract for agents working in this repository.

Keep it short and repo-specific. Shared workflow rules live in `memory/system/WORKFLOW.md`.

## Before doing work

1. Read `TODO.md`.
2. Read `memory/index.md`.
3. Read `memory/system/WORKFLOW.md`.
4. Load only the memory files relevant to the task.
5. Read any repository docs referenced by those files.

Use built-in agent planning and memory for task execution.  
Do not rely on transient chat context when the same knowledge should exist in checked-in files.

`memory/index.md` is the routing layer for task-relevant durable knowledge.  
`memory/system/WORKFLOW.md` defines the shared planning, memory, freshness, and handoff rules.

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

## Optional working notes

Local working notes (for example under `.agent-work/`) may be used when helpful, but are not required.

Do not treat local working notes as durable memory. Persist reusable knowledge in `/memory`.
