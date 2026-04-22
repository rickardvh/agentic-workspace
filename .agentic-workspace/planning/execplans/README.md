# Execution Plans

Checked-in execution plans for multi-milestone or multi-thread work live in this directory.

Use `agentic-workspace summary --format json` first when the question is active planning state.
Use raw `TODO.md` and execplan prose after that only when the compact summary is insufficient or when you are maintaining the human-readable plan directly.
Use raw `.agentic-workspace/planning/state.toml` when you need direct maintenance access to canonical machine-readable planning state.
Use `.agentic-workspace/docs/candidate-lanes-contract.md` for the native `roadmap` lane shape in `.agentic-workspace/planning/state.toml` when grouped deferred work needs more structure than a flat candidate bullet.
Use `docs/planning-routing-contract.md` when deciding whether newly discovered work belongs in `roadmap`, `todo.active_items`, `.agentic-workspace/planning/execplans/`, or `.agentic-workspace/planning/reviews/`.
Use `python scripts/check/check_planning_surfaces.py` for advisory shape and drift warnings across `todo.active_items`, active execplans, and `roadmap`.
Use `promote-to-plan` and `archive-plan` as thin file-native helpers around the same checked-in contract.
Use `docs/environment-recovery-contract.md` for task-local recovery and environment assumptions.
Use `.agentic-workspace/docs/system-intent-contract.md` for the durable larger-intent and honest-reinterpretation rule.
Use `docs/intent-contract.md` and `docs/resumable-execution-contract.md` for the compact planning summary contracts.
Use `docs/execution-summary-contract.md` for the compact outcome shape that completed slices should leave behind before archive.
Use `archive-plan --apply-cleanup` only when you want the helper to also remove completed active-item references and compress matching roadmap residue for the same archived thread.

This planning system is for execution. It is not intended to become a generic tracker, backlog database, or Jira replacement.

## Layout

- Keep active plans at the top level of `.agentic-workspace/planning/execplans/`.
- Keep only active plans plus `README.md` and `TEMPLATE.md` at the top level.
- Move completed plans into `.agentic-workspace/planning/execplans/archive/`.
- Mark the active milestone `Status` as `completed` before archiving a finished plan.
- Before archive, fill `## Proof Report`, `## Intent Satisfaction`, and `## Closure Check` so the lane-level closure evidence is explicit.
- Keep exactly one active milestone and one immediate next action by default.
- Prefer feature-scoped plan files over growing broad shared hot files.
- Skip `archive/` during normal startup unless the task explicitly needs historical plan context.
- Do not treat `todo.active_items`, `roadmap`, or active execplans as long-form completion logs; once a plan is complete, archive it and remove the completed-work detail from forward-looking planning surfaces.
- When a completed slice came from `todo.active_items` or `roadmap`, remove or archive the matched queue residue in the same pass rather than leaving stale completed candidates behind.
- Do not confuse slice completion with lane completion; a slice can ship while the larger intent remains open, and archive should wait until the lane-level proof is explicit.
- Do not add sections such as `Added In This Pass`, `Completed Work`, or similar retrospective logs to `todo.active_items`; completed detail belongs in archived execplans, workflow-change notes, or git history.
- Treat active plan state as branch-local and low half-life: archive, replace, or prune it rather than mutating it forever.

Use a plan here when:

- work spans more than one milestone
- work will be handed between threads or models
- implementation should not start from chat context alone
- architectural drift or validation scope needs explicit tracking
- the implementing agent needs checked-in context because its own planning tools, context window, or local scratchpad are not sufficient

Keep small direct work in `todo.active_items` when one coherent pass can finish it safely.
A direct task should stay compact and normally use only `ID`, `Status`, `Surface`, `Why now`, `Next action`, and `Done when`.
`todo.active_items` may also carry the smallest near-term same-thread queue that should follow the active chunk soon; keep that queue concrete and short enough that it stays activation, not backlog.
Promote that task into `.agentic-workspace/planning/execplans/` once it picks up milestone sequencing, blocker management, validation scope, rollback or migration handling, or enough ambiguity that the next contributor would need more than the TODO row to continue.
Direct execution is a success mode, not a planning failure.
Use `.agentic-workspace/docs/capability-aware-execution.md` when deciding whether the task still fits cheap direct execution, should move to stronger planning first, is suitable for bounded autopilot, should be silently reshaped into a cheaper slice, or should stop and escalate.
Use `docs/environment-recovery-contract.md` when interruption handling, environment drift, or retry state means the plan must carry a compact recovery path.
Use `.agentic-workspace/docs/context-budget-contract.md` when deciding what must stay live now, what can be recovered later, what must be externalized before a context shift, and what cheap resumability note should survive a pause or handoff.
Silent shaping may improve means, decomposition, and validation scope, but it must not silently widen the requested outcome, owned surface, or time horizon; broader solutions belong in an explicit promotion or escalation decision.

For ordinary inspection, keep the hierarchy explicit:

1. `agentic-workspace summary --format json`
2. one relevant selector or view inside that payload
3. raw `.agentic-workspace/planning/state.toml` or execplan prose only when the compact state is insufficient

When planning has one active TODO item and one active execplan, the compact hierarchy question should be answerable from the summary/report surfaces alone: active chunk, parent lane, next likely chunk, continuation owner, and proof state.

When memory is installed, prefer borrowing durable context from the smallest relevant memory note or canonical doc instead of restating the same subsystem explanation inside each execplan.
Repeated background prose in plans is a missing-synergy signal: tighten routing, promote the durable fact into memory or canonical docs, or decompose the work so the plan can stay local.

Do not create a plan just because a stronger agent could write one. Use a checked-in plan only when the artifact is expected to reduce rediscovery, restart cost, or handoff risk more than it costs to produce.

Capability-aware delegation is allowed but optional. If the environment supports it, a more capable agent or model may write a compact execplan and then hand implementation to a smaller or less capable agent when that is likely to save tokens without sacrificing quality. Do not assume subagents exist; the same contract must still work for one agent executing end-to-end. Prefer silent shaping and better planning over repeated prompts to switch executors manually.

Native runtime artifacts such as `implementation_plan.md`, `task.md`, or `walkthrough.md` may exist when an agent UI provides them, but they must not become a second durable source of truth. Before review, handoff, or session end, mirror any durable execution state back into `.agentic-workspace/planning/state.toml` and the active execplan so the next agent can continue from repo-owned surfaces alone.

Each active plan should stay compact and include:

- goal
- non-goals
- intent continuity
- required continuation
- intent interpretation when the slice is meaningfully shaped from a literal request into a bounded concrete "what"
- execution bounds and stop conditions when the slice may benefit from bounded delegated execution
- context budget
- delegated judgment
- active milestone
- immediate next action
- touched paths
- invariants
- contract decisions to freeze when the slice is product-shaping
- open questions to close when unresolved contract decisions still block implementation
- validation commands
- required tools when the task depends on a capability that may be absent in some runtimes
- completion criteria
- execution run residue when delegated work is attempted
- finished-run review when delegated work returns for planner/reviewer inspection
- execution summary
- closure check
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

Required follow-on routing belongs under `## Required Continuation` for active plans:

- `Required follow-on for the larger intended outcome`: `yes` or `no`
- `Owner surface`: `none` only when no required continuation remains
- `Activation trigger`: `none` only when no required continuation remains

Use this section to distinguish required continuation from optional nice-to-have follow-up.
If a completed slice leaves the larger intended outcome unfinished, record the required next owner and activation trigger here before archiving.
Do not rely on drift-log prose, completion-note prose, or chat residue to carry mandatory follow-through.

Iterative carry-forward belongs under `## Iterative Follow-Through` when a bounded slice is expected to stop before the broader goal is complete:

- `What this slice enabled`
- `Intentionally deferred`
- `Discovered implications`
- `Proof achieved now`
- `Validation still needed`
- `Next likely slice`

Use this section to preserve the minimal residue a later contributor should not have to reconstruct after the slice stops intentionally.
Keep it distinct from `Required Continuation`: required continuation answers who owns mandatory follow-on and when it activates; iterative follow-through answers what this slice changed about that larger line of work.
Keep it distinct from `Execution Summary`: follow-through carries forward deferred work and discovered implications, while execution summary records the bounded slice outcome once the slice stops.

Context budget belongs under `## Context Budget` for active plans:

- `Live working set`
- `Recoverable later`
- `Externalize before shift`
- `Tiny resumability note`
- `Context-shift triggers`

Use this section to keep the smallest necessary live bundle explicit without turning ordinary work into bookkeeping.
The section should stay smaller than the surrounding execplan.
It exists so an agent can deliberately shed context after externalizing the residue that later proof, review, or continuation would otherwise have to reconstruct.

Delegated judgment belongs under `## Delegated Judgment` for active plans that should preserve broad direction across sessions:

- `Requested outcome`
- `Hard constraints`
- `Agent may decide locally`
- `Escalate when`

Keep this section compact.
It exists to preserve the intended end state, the allowed local latitude, and the escalation boundary when a safe first slice might otherwise drift into a substitute for the larger request.
Use `none` only when the slice is so local that delegated-judgment framing would add no value beyond the surrounding plan.
`agentic-workspace summary --format json` exposes a typed `planning-summary/v1` payload. Inside that payload, `planning_record` is the canonical active planning record when planning has one active TODO item and one active execplan. `active_contract` is the narrower intent projection over that record.
Treat `planning_record` as canonical active state when it is available; raw `.agentic-workspace/planning/state.toml` and execplan prose remain the thin human maintenance layer and semantic fallback.

Intent interpretation belongs under `## Intent Interpretation` when the slice should preserve how it moved from the literal request to the bounded intended outcome:

- `Literal request`
- `Inferred intended outcome`
- `Chosen concrete what`
- `Interpretation distance`
- `Review guidance`

Keep this section compact and review-oriented. It should make the interpretive move inspectable enough to catch overreach or drift without turning the plan into a reasoning trace.

Execution bounds belong under `## Execution Bounds` when a bounded executor should have explicit local rails:

- `Allowed paths`
- `Max changed files`
- `Required validation commands`
- `Ask-before-refactor threshold`
- `Stop before touching`

Keep these bounds close to the active plan so the worker does not have to reconstruct them from chat.

Stop conditions belong under `## Stop Conditions` when a bounded executor should know when to stop cheaply:

- `Stop when`
- `Escalate when boundary reached`
- `Escalate on scope drift`
- `Escalate on proof failure`

These conditions should make "stop and escalate" cheaper than silent drift.

Closure checks belong under `## Closure Check` for completed or nearly-complete plans:

- `Slice status`
- `Larger-intent status`
- `Closure decision`
- `Why this decision is honest`
- `Evidence carried forward`
- `Reopen trigger`

Use this section to distinguish bounded slice success from larger-intent closure.
`archive-and-close` is only honest when the larger intent is actually satisfied.
`archive-but-keep-lane-open` is the honest path when the slice is complete but required continuation remains elsewhere.
Do not force later contributors to infer this decision from drift prose, issue bodies, or chat residue.

## Meaning Boundary

Use one compact rule when deciding where a planning meaning belongs:

- machine-readable state keeps the restart-critical meanings that must be recovered cheaply and unambiguously, including active work, next action, follow-on owner, proof state, and escalation boundaries
- compact prose keeps stable route guidance and framing when a queryable field would not reduce recovery cost enough to justify a second owner
- raw execplan detail keeps slice-specific narrative, implementation notes, drift-log residue, and other maintenance detail that should not be the default recovery path

Example: "What should I do next?" belongs in `resumable_contract`; the route that gets you there belongs in compact prose; the line-by-line change log belongs in raw execplan detail.

Current-state restart belongs in the compact `resumable_contract` projection:

- `current_next_action`
- `active_milestone`
- `completion_criteria`
- `proof_expectations`
- `escalate_when`
- `blockers`
- `minimal_refs`

That object should stay smaller than the full execplan and answer "how do I continue safely right now?" without broad rereading.
Use it before opening raw plan prose when the task is ordinary restart or handoff, not deep semantic maintenance.

Context-budget and cheap-resume answers belong in the compact `context_budget_contract` projection:

- `live_working_set`
- `recoverable_later`
- `externalize_before_shift`
- `tiny_resumability_note`
- `context_shift_triggers`

That object should stay compact enough to reduce rereads and mixed-agent restart cost rather than creating a second planning narrative.
Use it when the question is what can be dropped now, what must be written down first, or what should trigger reloading a different bundle later.

Delegated-work inspection answers belong in three compact projections over the same active plan state:

- `intent_interpretation_contract`
- `execution_run_contract`
- `finished_run_review_contract`

Use them when the question is how the slice interpreted the request, what happened in one bounded delegated run, or how returned work should be judged for scope/proof/intent fit.
Keep those projections thin and derived; they are not a second planning authority.

For larger-picture restart and queue questions, `hierarchy_contract` may also be present as a thin projection over the same active planning state. Use it for parent-lane, next-chunk, continuation-owner, and proof-state answers; do not treat it as a second planning authority.
When queued TODO items exist, the same hierarchy view may also expose the near-term queue so the next same-thread chunk does not survive only in prose or chat.

Tool verification belongs in the compact planning contract when the task needs a capability that may not be present:

- `required_tools`
- advisory rule: stop or escalate when a required tool is unavailable instead of attempting an impossible substitute

Keep the first slice advisory.
The goal is to save tokens by preventing doomed attempts, not to turn execplans into a full runtime capability detector.

Execution summaries belong under `## Execution Summary` for completed or nearly-complete plans:

- `Outcome delivered`
- `Validation confirmed`
- `Follow-on routed to`
- `Resume from`

Keep this section compact and decision-shaped.
It exists so later contributors do not have to reconstruct what the slice achieved, how it was proved, and where follow-through now lives.
Do not turn it into a second drift log, a notebook, or a memory note.
If the slice ended with intentionally deferred work or newly discovered implications, leave those in `Iterative Follow-Through` instead of stretching `Execution Summary` into a backlog.

Closure discipline should stay cheap and explicit:

- when a slice renames, moves, retires, or refactors a named surface, include a stale-reference sweep in `Validation Commands`
- prefer a narrow search or checker over broad rereads
- if required follow-on remains, route it into checked-in planning instead of leaving it implicit in chat or drift prose

Keep the drift log decision-shaped and brief. Do not turn an active or completed execplan into a changelog when the same detail is already recoverable from archived plans and git.
Execplans own milestone sequencing, blockers, validation scope, and completion detail for planned work. `todo.active_items` should only expose that the work is active and point here.
Environment-sensitive work should express recovery in the existing plan fields rather than inventing ad hoc restart sections or long troubleshooting prose.
Use stable headings, explicit status markers, and compact bullets so active plans remain merge-friendly under concurrent edits.

Keep durable technical facts and stable subsystem guidance in canonical docs or checked-in memory, not inside active execplans.
When a completed plan leaves behind durable residue, promote it into memory or canonical docs instead of treating the archived plan as its long-term home.

Prefer refining the existing contract over inventing a second schema. If a proposed improvement makes plans harder to use than the work they are guiding, it is likely the wrong change.

Default to one active milestone at a time.
Prefer updating an existing active plan over creating overlapping plan files for the same feature.
Archive or collapse completed plans once they no longer affect future execution.
