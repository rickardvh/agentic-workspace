# Execution Plans

Checked-in execution plans for multi-milestone or multi-thread work live in this directory.

Use `python scripts/check/check_planning_surfaces.py` for advisory shape and drift warnings across `TODO.md`, active execplans, and `ROADMAP.md`.
Use `agentic-planning-bootstrap summary`, `promote-to-plan`, and `archive-plan` as thin file-native helpers around the same checked-in contract.

This planning system is for execution. It is not intended to become a generic tracker, backlog database, or Jira replacement.

## Layout

- Keep active plans at the top level of `docs/execplans/`.
- Keep only active plans plus `README.md` and `TEMPLATE.md` at the top level.
- Move completed plans into `docs/execplans/archive/`.
- Mark the active milestone `Status` as `completed` before archiving a finished plan.
- Keep exactly one active milestone and one immediate next action by default.
- Skip `archive/` during normal startup unless the task explicitly needs historical plan context.
- Do not treat `TODO.md`, `ROADMAP.md`, or active execplans as long-form completion logs; once a plan is complete, archive it and remove the completed-work detail from forward-looking planning surfaces.

Use a plan here when:

- work spans more than one milestone
- work will be handed between threads or models
- implementation should not start from chat context alone
- architectural drift or validation scope needs explicit tracking

Each active plan should stay compact and include:

- goal
- non-goals
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

Keep the drift log decision-shaped and brief. Do not turn an active or completed execplan into a changelog when the same detail is already recoverable from archived plans and git.
Execplans own milestone sequencing, blockers, validation scope, and completion detail for planned work. `TODO.md` should only expose that the work is active and point here.

Keep durable technical facts and stable subsystem guidance in canonical docs or checked-in memory, not inside active execplans.

Prefer refining the existing contract over inventing a second schema. If a proposed improvement makes plans harder to use than the work they are guiding, it is likely the wrong change.

Default to one active milestone at a time.
Prefer updating an existing active plan over creating overlapping plan files for the same feature.
Archive or collapse completed plans once they no longer affect future execution.
