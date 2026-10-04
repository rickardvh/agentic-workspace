# Preserve and resume useful task meaning

At a meaningful boundary, retain only changes whose loss would cause material
rediscovery or unsafe continuation: accepted progress/conclusions, changed scope
or constraints, a pause/handoff, or completed work with unfinished follow-through.
Group related changes in one owner update; skip unchanged material. No per-turn,
token-count or elapsed-time checkpoint is required.

First reuse an accepted owner for this work. If ordinary repository records
already preserve enough meaning, retain their exact pointers instead of copying
them or creating a duplicate plan. Simple completed work needs no record. When
material unfinished execution has no adequate owner, obtain the exact creation
request through the public reference:

```agentic-owner-reference
{"kind":"request","owner":"planning","id":"planning/create/v1"}
```

Resolve an owner reference with ordinary `start --target . --task "<actual task>"`
and `--reference owner:request:planning:planning/create/v1`. Fill only its requested
`arguments.material` using the returned schema/current Planning detail. For an
existing owner, first explicitly select or resume it for this task, then use its update
request below. Supply only the semantic material that changed. Submit the filled
request through `start`, invoke only the returned admitted action, and inspect the
effect outcome and current continuation. Native creation establishes the current
owner for this task through the existing selection admission. Verify that current
Planning names the created owner; a successful write alone is not selection or
task completion. Genuine ambiguity or unavailable admission remains an explicit
selection gap with a bounded next request.

If selection was interrupted, use current reentry and the exact owner path to
reobserve the current creation/selection recovery; never
replay the creation effect or find an owner with an all-plan glob. Preserve a
precise selection gap when the current owner cannot admit the next operation.

Map useful meaning to the existing fields, without another resume schema:

- `intent` and `scope`: intended outcome, constraints and negative requirements.
- `continuation`: accepted progress and conclusions with concise rationale/source
  pointers, unresolved uncertainty and the remaining work.
- `blockers` and `next_action`: remaining impediments, next useful action and its
  prerequisite. Record authorisation as a source to revalidate, never permission
  that transfers to a fresh agent.
- `references` and `proof`: exact supporting and recovery references. Proof reuse
  depends on its owner's current dependencies; uncertain effects require recovery.

Classify volatile PR/head/review/CI observations through existing material lifetime
fields. Moving observations alone must not produce tracked semantic updates.
Prefer leaving these observations with their current source. If `proof.observed`
contains only a captured check result or status, classify it with
`material_lifetimes.proof_observed: observation`. First separate real obligations
into `proof.remaining` and accepted results needed for continuation into durable
`continuation` fields. Unclassified or mixed meaning stays retained;
classification requires judgment, not matching words such as "passed".
Replace current continuation rather than append transcript history, source bodies,
raw logs or carriage. A retained conclusion needs its rationale, not every step.

Tighten unresolved requirements before claiming readiness. Keep milestones, proof,
risks, invariants and continuation truthful. A scaffold, successful write or quiet
owner does not establish implementation or completion authority. Invoke only the
exact admitted action, then inspect effect outcome and fresh continuation. Preserve
source, policy, Assignment and Verification restrictions and uncertain effects.

```agentic-owner-reference
{"kind":"request","owner":"planning","id":"planning/update/v1"}
```

Use `planning_context.next_step` with current reentry and the changed `material`
fields. Object members merge into current supported material; arrays and scalar
values replace the named value, and `null` removes a named member. The complete
record must still satisfy all required fields. Omitted members, lifecycle, phase, relationships
and other supported fields remain under Planning's custody. Planning constructs
and validates the complete postimage and rechecks current sources before effects.
Include lifecycle or phase only when the task actually changes them. Detailed
schemas remain available for exceptional contract questions.

On fresh entry, use the supplied issue/owner pointer and explicitly select it for
today's task, then recover only that owner's
intent, continuation, blockers, next action and proof references. Follow the exact
Planning detail route or read that named record; do not scan all plans/history.
The exact selection request is `owner:request:planning:planning/select-owner/v1`.
Fill `arguments.owner_ref` to select a named plan, or leave arguments empty only
when explicitly resuming the local remembered hint. Planning revalidates its
real source and custody. Several unfinished plans may coexist; unrelated work
does not need to reject or release any of them. An exact retained current-work
binding still restores the bound owner's continuity requirements.
Use the returned current reentry for the next step. It preserves any still-current
explicit relation answer. A missing update request is a reason to resolve the
current relation or its reported gap, not to reconstruct a record or repeatedly
fetch schemas. Exact committed creation custody also restores this task's owner
on fresh entry; unrelated tasks remain direct.

Reobserve material volatile state such as remote head/review changes, relevant
source/scope changes and required prerequisites. Unrelated changes do not require
reconstruction. Do not inherit source availability from surviving carriage after
context loss. Retained state recovers what was actually written, with explicit
unknowns; it cannot recover an unrecorded finding from abrupt context loss.

If the owner is disabled or unavailable, state the exact retention gap. A readable
record is useful evidence without executable AW but grants no mutation custody.
Use an already authorised ordinary repository destination when sufficient; never
hand-edit managed state or claim persistence from a chat promise. At completion,
update the owner only if changed durable meaning must survive or a currently
relied-upon instruction would cause unsafe continuation. Name that consequence;
old phase, head, check or completed-step snapshots alone need no refresh. A
complete leaf can leave its containing lane live, and a lower PR need not mirror
later work. Reobserve relevant facts before acting; snapshots grant no current
proof, permission or task authority. Preserve referenced evidence and unfinished
work while retiring disposable transport through current retention paths.

Continue while the user's authorized objective has safe remaining work; a completed
milestone alone does not end the session. Stop for completion, a real blocker or
user direction, without widening scope. This is ordinary agent continuation, not
a scheduler, launcher or final-response admission service. Keep validation, issue
completion and intent satisfaction distinct.
