# Planning lifetime boundary

This note is the implementation boundary for #3197. It describes the current
Planning ownership split; it is not a second Planning authority or an external
tracker mirror.

## Invariant

A feature branch may persist Planning only when the feature changes durable
semantic custody. Movement in external or derived operational state must not, by
itself, require a tracked Planning rewrite.

Durable semantic custody includes information expensive to reconstruct and still
owned by the work: intended outcome, material scope/constraints/stops, accepted
semantic progress, unresolved residual intent, durable decisions/references,
proof or reconciliation obligations, and bounded integration proposals.

Volatile operational observations are re-observed or derived at use time. They do
not become checked-in feature-branch authority merely because they affect the
current next step. This includes:

- PR/review/CI/head/merge state;
- predecessor integration and open-stack/frontier bookkeeping;
- external issue lifecycle state;
- provider/host availability or quota;
- a `next_action` derived only from those observations;
- proof/history narration with no continuing semantic custody value.

A material change to intended outcome, scope, constraints, accepted semantic
progress, residual work, durable dependencies, or required proof/reconciliation
is different: it must still be admitted as a Planning semantic mutation where
Planning owns the work.

## Current transition seam

The native Planning representation still contains legacy mixed-lifetime fields.
The relevant write/reconciliation seams are:

- `native_planning_create::MATERIAL` and creation document construction;
- `native_planning_update::fields` / `update_material` and update admission;
- `planning::reconciliation`, which projects former execplan fields into the
  current Planning subject;
- `planning::semantic_subject`, which already excludes a narrower set of
  attempt/evidence bookkeeping from subject currentness.

The current source demonstrates why #3197 is not solved by editing one stale plan:
`next_action`, `relationships.external_posture`, and
`continuation.frontier` can still be carried into durable Planning material even
when they contain only moving external posture.

## Required implementation shape

Use the existing Planning owner and current-source resolution. Do not add a
repository-global tracker, event log, session authority, merge driver, or branch
rewrite service.

1. Give native Planning one deterministic distinction between durable semantic
   material and volatile/derived observations. Prefer removing volatile fields
   from durable mutation input or projecting them out at the existing owner
   boundary rather than adding another persistent state object.
2. A change solely to volatile observations must produce no tracked Planning
   postimage. Current `start`/review may still report that the observation moved
   by consulting its current owner/source.
3. Merge-dependent lifecycle truth belongs on the integrated target through the
   existing reconciliation/integration semantics, not as a repeatedly refreshed
   feature-branch assertion.
4. Preserve fresh-process continuation from repository-owned durable Planning.
   Losing volatile observations must not lose intended outcome, accepted progress,
   residual work, proof/reconcile obligations, or returned/integration-pending
   custody.
5. Keep native/Python/TypeScript/JSON projections equivalent where this boundary
   is public.

## Proof cases

The implementation is not complete until focused fixtures demonstrate both sides
of the boundary:

- **stack movement:** create upper feature work with durable Planning, advance a
  lower PR's review/CI/merge/head state, re-enter/review the upper work, and prove
  the upper tracked Planning bytes do not change solely because that external
  state moved;
- **real semantic change:** change durable intended work meaning and prove a
  Planning mutation is still required/admitted;
- **fresh consumer:** discard process/adapter-local observations and recover
  intended outcome, accepted progress, residual frontier and proof/reconcile
  obligations from repository-owned state;
- **target reconciliation:** merge-dependent lifecycle/current posture is applied
  or derived on the integrated target without an AW-only refresh commit in the
  feature branch.

The historical #3190 stale execplan is counterevidence and a fixture source, not
the desired implementation. Do not refresh its old PR/head prose and call the
regression fixed.
