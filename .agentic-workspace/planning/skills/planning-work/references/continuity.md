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
existing owner, first establish the current task relation, then use its update
request below. Preserve all unchanged fields and relationships. Submit the filled
request through `start`, invoke only the returned admitted action, and inspect the
effect outcome. Creation returns an exact `selection_request` and
`selection_context`; use them to select this owner without rebuilding the context.

Map useful meaning to the existing fields, without another resume schema:

- `intent` and `scope`: intended outcome, constraints and negative requirements.
- `continuation`: accepted progress and conclusions with concise rationale/source
  pointers, unresolved uncertainty and the current remaining frontier.
- `blockers` and `next_action`: remaining impediments, next useful action and its
  prerequisite. Record authorisation as a source to revalidate, never permission
  that transfers to a fresh agent.
- `references` and `proof`: exact supporting and recovery references. Proof reuse
  depends on its owner's current dependencies; uncertain effects require recovery.

Classify volatile PR/head/review/CI observations through existing material lifetime
fields. Moving observations alone must not produce tracked semantic updates.
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

On fresh entry, use the supplied issue/owner pointer or current selected-owner
reference, establish its relation to today's task, and recover only that owner's
intent, continuation, blockers, next action and proof references. Follow the exact
Planning detail route or read that named record; do not scan all plans/history.
An incumbent identity alone does not establish assignment. The exact continuation
request is `owner:request:planning:planning/continuation/v1`; answer the current
relation/posture questions separately when work is independent.

Reobserve material volatile state such as remote head/review changes, relevant
source/scope changes and required prerequisites. Unrelated changes do not require
reconstruction. Do not inherit source availability from surviving carriage after
context loss. Retained state recovers what was actually written, with explicit
unknowns; it cannot recover an unrecorded finding from abrupt context loss.

If the owner is disabled or unavailable, state the exact retention gap. A readable
record is useful evidence without executable AW but grants no mutation custody.
Use an already authorised ordinary repository destination when sufficient; never
hand-edit managed state or claim persistence from a chat promise. At completion,
use current closeout and resource-retention paths; preserve referenced evidence
and unfinished work while retiring disposable transport.

Continue while the user's authorized objective has safe remaining work; a completed
milestone alone does not end the session. Stop for completion, a real blocker or
user direction, without widening scope. This is ordinary agent continuation, not
a scheduler, launcher or final-response admission service. Keep validation, issue
completion and intent satisfaction distinct.
