# Execution Plans

Checked-in execution plans for multi-milestone or multi-thread work live in this directory.

Use `python scripts/check/check_planning_surfaces.py` for advisory shape and drift warnings across `TODO.md`, active execplans, and `ROADMAP.md`.
Use `agentic-planning-bootstrap summary`, `promote-to-plan`, and `archive-plan` as thin file-native helpers around the same checked-in contract.
Use `archive-plan --apply-cleanup` only when you want the helper to also remove completed TODO references and compress matching `ROADMAP.md` Active Handoff residue for the same archived thread.

This planning system is for execution. It is not intended to become a generic tracker, backlog database, or Jira replacement.

## Layout

- Keep active plans at the top level of `docs/execplans/`.
- Keep only active plans plus `README.md` and `TEMPLATE.md` at the top level.
- Move completed plans into `docs/execplans/archive/`.
- Mark the active milestone `Status` as `completed` before archiving a finished plan.
- Keep exactly one active milestone and one immediate next action by default.
- Prefer feature-scoped plan files over growing broad shared hot files.
- Skip `archive/` during normal startup unless the task explicitly needs historical plan context.
- Do not treat `TODO.md`, `ROADMAP.md`, or active execplans as long-form completion logs; once a plan is complete, archive it and remove the completed-work detail from forward-looking planning surfaces.
- Do not add sections such as `Added In This Pass`, `Completed Work`, or similar retrospective logs to `TODO.md`; completed detail belongs in archived execplans, workflow-change notes, or git history.
- Treat active plan state as branch-local and low half-life: archive, replace, or prune it rather than mutating it forever.

Use a plan here when:

- work spans more than one milestone
- work will be handed between threads or models
- implementation should not start from chat context alone
- architectural drift or validation scope needs explicit tracking
- the implementing agent needs checked-in context because its own planning tools, context window, or local scratchpad are not sufficient

Keep small direct work in `TODO.md` when one coherent pass can finish it safely.
A direct task should stay compact and normally use only `ID`, `Status`, `Surface`, `Why now`, `Next action`, and `Done when`.
Promote that task into `docs/execplans/` once it picks up milestone sequencing, blocker management, validation scope, rollback or migration handling, or enough ambiguity that the next contributor would need more than the TODO row to continue.
Direct execution is a success mode, not a planning failure.
Use `docs/capability-aware-execution.md` when deciding whether the task still fits cheap direct execution, should move to stronger planning first, is suitable for bounded autopilot, should be silently reshaped into a cheaper slice, or should stop and escalate.
Silent shaping may improve means, decomposition, and validation scope, but it must not silently widen the requested outcome, owned surface, or time horizon; broader solutions belong in an explicit promotion or escalation decision.

When memory is installed, prefer borrowing durable context from the smallest relevant memory note or canonical doc instead of restating the same subsystem explanation inside each execplan.
Repeated background prose in plans is a missing-synergy signal: tighten routing, promote the durable fact into memory or canonical docs, or decompose the work so the plan can stay local.

Do not create a plan just because a stronger agent could write one. Use a checked-in plan only when the artifact is expected to reduce rediscovery, restart cost, or handoff risk more than it costs to produce.

Capability-aware delegation is allowed but optional. If the environment supports it, a more capable agent or model may write a compact execplan and then hand implementation to a smaller or less capable agent when that is likely to save tokens without sacrificing quality. Do not assume subagents exist; the same contract must still work for one agent executing end-to-end. Prefer silent shaping and better planning over repeated prompts to switch executors manually.

Each active plan should stay compact and include:

- goal
- non-goals
- intent continuity
- active milestone
- immediate next action
- touched paths
- invariants
- validation commands
- completion criteria
- drift log

Readiness fields belong under `## Active Milestone` for active plans:

- `Ready`: one of `ready`, `blocked`, `conditional` (or `true`/`false`)
- `Blocked`: short blocker detail (`none` when not blocked)
- `optional_deps`: optional dependency hints (`none` when unused)

Intent continuity belongs under `## Intent Continuity` for active plans:

- `Larger intended outcome`: the parent user or product intent this slice serves
- `This slice completes the larger intended outcome`: `yes` or `no`
- `Continuation surface`: `none` only when the larger intended outcome is complete; otherwise the checked-in surface that now owns continuation

Use this section to keep a safe first slice from masquerading as the full requested outcome.
If a completed slice does not finish the larger intended outcome, archive should only happen after the continuation surface is explicit.

Keep the drift log decision-shaped and brief. Do not turn an active or completed execplan into a changelog when the same detail is already recoverable from archived plans and git.
Execplans own milestone sequencing, blockers, validation scope, and completion detail for planned work. `TODO.md` should only expose that the work is active and point here.
Use stable headings, explicit status markers, and compact bullets so active plans remain merge-friendly under concurrent edits.

Keep durable technical facts and stable subsystem guidance in canonical docs or checked-in memory, not inside active execplans.
When a completed plan leaves behind durable residue, promote it into memory or canonical docs instead of treating the archived plan as its long-term home.

Prefer refining the existing contract over inventing a second schema. If a proposed improvement makes plans harder to use than the work they are guiding, it is likely the wrong change.

Default to one active milestone at a time.
Prefer updating an existing active plan over creating overlapping plan files for the same feature.
Archive or collapse completed plans once they no longer affect future execution.
