# Agent Instructions

Local bootstrap contract for agents working in this repository.

## Precedence

Resolve instruction conflicts in this order:

1. Explicit user request.
2. Active feature plan in `docs/execplans/`, when the task belongs to that plan.
3. `AGENTS.md`.
4. Checked-in workflow or memory policy docs, when present.
5. Routed memory and invariants, when present and relevant.
6. Repo docs explicitly referenced by the active route or plan.

Prefer checked-in knowledge over durable chat memory when both exist.

## Startup Procedure

1. Read `AGENTS.md`.
2. Read `TODO.md`.
3. Read `docs/execplans/README.md`.
4. Read the active feature plan in `docs/execplans/` when the task belongs to one.
5. Read `ROADMAP.md` only when promoting work, reprioritising, or reviewing candidate epics.
6. Read `docs/upstream-task-intake.md` when triaging external issues or tasks into checked-in planning.
7. Read `docs/capability-aware-execution.md` when task capability fit, delegation, silent shaping, or escalation is unclear.
8. Read `docs/environment-recovery-contract.md` when interruption handling, environment assumptions, or recovery shape is unclear.
9. Prefer `.agentic-workspace/planning/agent-manifest.json` and `tools/AGENT_QUICKSTART.md` before freeform exploration.
10. Read only the repo docs relevant to the touched subsystem.
11. Read `memory/index.md` and `\.agentic-workspace/memory/WORKFLOW.md` only when memory is installed and the task is not already well-routed by the plan or manifest, or when changing workflow, planning, or memory itself.

Do not bulk-read all planning surfaces for ordinary execution work. Start from `TODO.md`, then read at most one relevant active execplan.
When the question is active planning recovery rather than startup order, prefer `agentic-planning-bootstrap summary --format json` and `agentic-workspace defaults --section startup --format json` before reopening broader planning prose.

Direct execution is valid when one coherent pass can finish the work and the `TODO.md` item can stay compact with `ID`, `Status`, `Surface`, `Why now`, `Next action`, and `Done when`.
Promote that task into `docs/execplans/` once it needs milestone sequencing, blocker handling, non-obvious validation scope, rollback or migration detail, or enough ambiguity that restart would require more than the TODO row.
Use `docs/capability-aware-execution.md` when deciding whether the cheapest safe path, stronger planning, silent shaping, delegation, or escalation is appropriate.
Use `docs/environment-recovery-contract.md` when deciding whether task-local recovery belongs in the active plan or should remain in module-local docs.
Do not treat that contract as a standing instruction to switch models or override tools that already perform automatic capability selection well.
When a bounded slice completes only part of a larger intended outcome, the execplan must record both `Intent Continuity` and `Required Continuation` before archive so the next owner and activation trigger live in checked-in planning, not only in prose or chat.
When the slice is expected to stop intentionally before that broader outcome is complete, keep `Iterative Follow-Through` current as the compact residue for what was enabled, deferred, newly discovered, and still awaiting proof.

Do not start coding from chat context alone when the same knowledge should live in checked-in files.

## Sources Of Truth

- Active queue and lightweight direct tasks: `TODO.md`
- Active feature execution contracts: `docs/execplans/`
- Long-horizon planning: `ROADMAP.md`
- Upstream task intake contract: `docs/upstream-task-intake.md`
- Capability-fit execution contract: `docs/capability-aware-execution.md`
- Environment and recovery contract: `docs/environment-recovery-contract.md`
- Durable routed knowledge, when installed: `memory/index.md`
- Shared memory workflow policy, when installed: `\.agentic-workspace/memory/WORKFLOW.md`
- Machine-readable routing and command bundles: `.agentic-workspace/planning/agent-manifest.json`
- Agent quickstart and rendered hot paths: `tools/AGENT_QUICKSTART.md`

## Repo Rules

- This is `<PROJECT_NAME>`.
- Repository purpose: `<PROJECT_PURPOSE>`.
- Key repo docs: `<KEY_REPO_DOCS>`.
- Key subsystems: `<KEY_SUBSYSTEMS>`.
- Do not broaden migrations, refactors, or schema changes beyond the active task unless a required adjacent fix is necessary for correctness.
- Prefer updating an existing plan over creating overlapping plan files for the same feature.
- Memory complements planning; it does not own active queue state, milestone sequencing, or backlog status.
- Keep durable implementation facts in canonical docs or memory, not in planning surfaces.

## Tooling And Validation

- Primary build command: `<PRIMARY_BUILD_COMMAND>`.
- Primary test command: `<PRIMARY_TEST_COMMAND>`.
- Other key commands: `<OTHER_KEY_COMMANDS>`.
- Run the narrowest validation that proves the change; escalate to broader checks only when the change crosses subsystem boundaries or the user explicitly asks for it.

## Completion Contract

1. Update `TODO.md`.
2. Update the active plan in `docs/execplans/` when working from one.
3. If a task leaves meaningful follow-up work, record it in the appropriate planning surface before closing the task.
4. Remove completed task detail from `TODO.md` once it no longer changes the next contributor's queue decision.
5. If the completed slice came from `TODO.md` or `ROADMAP.md`, remove or archive the matched planning residue in the same pass rather than leaving stale completed queue state behind.
6. If the larger intended outcome is still unfinished, record the required next owner and activation trigger explicitly before archive.
