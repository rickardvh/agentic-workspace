---
name: memory-capture
description: Capture durable lessons into the right Memory or owner surface. Use when a task has revealed reusable knowledge that should survive the current session, including repo-shared facts for checked-in Memory and machine-local/runtime-specific lessons for local Memory.
---

# Memory Capture

This is a bootstrap-managed core skill shipped with the payload under `.agentic-workspace/memory/skills/`. Add repo-specific sibling skills under `.agentic-workspace/memory/repo/skills/` instead of customising this core skill unless the shared reusable procedure itself changed.

Use this skill to turn a solved issue or discovered rule into the smallest correct capture or routing decision.

It operates on Memory decisions. Repo-shared Memory is checked in under `.agentic-workspace/memory/repo/`; machine-local, user-local, runtime-specific, private, or low-confidence notes belong under local-only Memory such as `.agentic-workspace/local/memory/`.

## Workflow

1. Read the repo's local contract:
   - `AGENTS.md`
   - `.agentic-workspace/memory/repo/index.md`
   - `.agentic-workspace/memory/SKILLS.md` when deciding whether a repo-specific skill should be created
2. Identify the durable lesson:
   - what fact should survive this task
   - why it is likely to matter again
   - which files, commands, or surfaces it applies to
3. Decide whether it belongs in Memory at all.
   - Do not capture one-off troubleshooting steps, temporary task notes, or backlog state.
4. Choose the storage authority before choosing a file:
   - Use repo-shared Memory only for durable knowledge that should travel with the repository.
   - Use local-only Memory for machine-local, user-local, runtime-specific, private, or low-confidence knowledge.
   - Use Planning/status for active task state or continuation state.
   - Use docs/config/tests/contracts for canonical policy, enforceable behavior, or proof obligations.
   - Use review or issues for follow-up work that is not durable anti-rediscovery knowledge.
5. For repo-shared Memory, choose the primary home:
   - `.agentic-workspace/memory/repo/domains/` for subsystem knowledge
   - `.agentic-workspace/memory/repo/invariants/` for things that must remain true
   - `.agentic-workspace/memory/repo/runbooks/` for durable operating procedures
   - `.agentic-workspace/memory/repo/mistakes/recurring-failures.md` for repeated failure patterns
   - `.agentic-workspace/memory/repo/decisions/` for longer-lived rationale when a README note is no longer enough
6. For local-only Memory, use the supported command path:
   - `agentic-workspace memory create-note --slug <slug> --local --local-reason "<why local>" --summary "<lesson>" --target . --format json`
   - Do not add local-only lessons to `.agentic-workspace/memory/repo/manifest.toml`.
7. Prefer editing an existing note over creating a new one when the existing note clearly owns the lesson.
   - If the existing note is already large, broad, or a repeated merge hotspot, split the durable lesson into a focused note instead of adding to the same catch-all surface.
8. Update repo note metadata and routing in the same change:
   - `Status`
   - `Applies to`
   - `Load when`
   - `Review when`
   - `Failure signals`
   - `Verify`
   - `Last confirmed`
   - `.agentic-workspace/memory/repo/manifest.toml` when used
9. If the repo note set changed materially, update `.agentic-workspace/memory/repo/index.md`.
10. If the repeated procedure is repo-specific rather than a durable fact, create a new repo-specific checked-in skill under `.agentic-workspace/memory/repo/skills/` instead of growing this core skill.
11. Treat `.agentic-workspace/memory/WORKFLOW.md` as reference policy only when the capture touches the memory contract or policy boundary.
12. Do not capture active state into shared current-memory notes. Put durable facts in the selected memory note, active state in planning/status, and transient context in local-only scratch.
13. If the lesson is better understood as friction than durable truth, record that with manifest metadata and prefer an upstream remediation target over training contributors to depend on an ever-growing note.

## Capture test

Capture the lesson only if most of these are true:

- another contributor could hit the same confusion or failure
- the fact affects future code changes, operations, or review
- the note will save future re-orientation time
- the information can be kept concise and verifiable
- the storage authority is clear: repo-shared, local-only, or routed elsewhere

If not, leave it out of `/memory`.

## Guardrails

- Keep durable knowledge in checked-in files so the result stays visible in git.
- Keep local/runtime/user/environment-specific knowledge out of checked-in repo Memory; use local-only Memory or local scratch.
- Do not create a new note when an existing note can be tightened instead.
- Do not keep expanding one broad note when separate branches are likely to edit unrelated facts in it.
- Do not put task state, backlog items, or one-off implementation history into memory.
- Mark uncertain claims `Needs verification` instead of presenting them as settled.
- Treat legacy `project-state.md` and `task-context.md` files as migration residue, not normal capture targets.
- Do not use filenames, prompt words, or phrase markers as authority for the storage decision; use agent judgment over the evidence.

## Typical outputs

- an updated invariant, domain note, runbook, or recurring-failures note
- a new memory note when no suitable home exists
- a local-only memory note when the lesson is machine-local or runtime-specific
- a routed_elsewhere decision when docs, Planning, tests, contracts, config, review, or an issue is the better owner
- refreshed note metadata and `Last confirmed`
- an updated `.agentic-workspace/memory/repo/index.md` or `.agentic-workspace/memory/repo/manifest.toml` when routing changed
