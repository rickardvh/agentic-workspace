# Orchestrator Workflow Contract

This contract defines the post-assignment planner-to-worker workflow for a
runtime that the compact current decision identifies as the assigned
orchestrator.

## Activation Boundary

Use this contract only with a binding non-local assignment and allowed action
whose identities and revisions are current. Structured assignment role and
target relation activate the procedure; free-form task wording does not.

- A selected current target stays on the ordinary direct-work path and does not
  load the orchestrator procedure.
- An absent or unresolved assignment returns to the canonical assignment owner.
  `planning-assurance-delegation` may supply named pre-decision evidence, but it
  cannot choose or dispatch a target.
- A binding non-local assignment routes to
  `planning-orchestrator-workflow`. The orchestrator cannot retain the worker
  slice locally because of availability, convenience, cost, or predicted speed.

## Ownership

Canonical assignment and action-gate operations own selected target,
implementation permission, and revision. The orchestrator consumes those
decisions while retaining custody of intent, decomposition, assignment bounds,
admission, integration, proof interpretation, and closeout.

Detailed phases stay with narrower owners:

- manual transport: `planning-manual-delegation` and `assignment.export` /
  `assignment.import`
- returned, failed, blocked, cancelled, stale, or stopped work:
  `planning-returned-result`
- admission and recovery: the exact current `assignment.admit`,
  `assignment.reject`, `assignment.repair`, `assignment.reassign`, or
  `assignment.override` action
- integration: `assignment.integrate` through normal repository ownership
- validation: AW-owned proof
- semantic satisfaction: `planning-intent-verification`
- closeout mechanics and residue: `planning-closeout-trust`
- broad lifecycle sequencing: `planning-high-assurance-lifecycle`

## Workflow

1. Read the compact current decision; verify assignment and action identities
   and revisions instead of reconstructing them from raw Planning state.
2. Preserve the assigned slice, selected target, work bounds, proof
   requirements, stop conditions, and return contract exactly. Do not rerank or
   reclassify the target after binding.
3. Execute only the admitted transport or dispatch action:
   - a typed host internal/automatic dispatch action may invoke the worker;
   - admitted manual transport follows `planning-manual-delegation`;
   - an admitted external adapter preserves the same assignment identity,
     revision, bounds, and return contract.
4. Track the run through canonical assignment lifecycle state. Transport
   success is not worker success, admission, integration, proof, or closeout.
5. Route the return through `planning-returned-result` and execute only the
   exact admission, recovery, override, or integration action named by the
   current decision.
6. Run AW-owned proof after integration; reconcile intent and closeout through
   their narrower owners. Worker or adapter claims cannot authorize either.
7. Record durable residue and the assignment outcome in the continuing checked-
   in owner.

## Worker Contract

The worker receives only the canonical assignment packet and explicit transport
metadata. It owns its assigned exploration, implementation, or validation
slice, and must stop when scope, proof, authority, or escalation boundaries are
hit. It cannot widen scope, change target, admit or integrate its own return, or
claim parent intent and closeout.

## Failure Boundary

If a binding non-local assignment cannot be dispatched or completed, stop at
the current lifecycle action. Use structured reject, repair, reassign, override,
or human escalation; never implement the worker slice locally as fallback.

## Output

Record assignment/action identities and revisions, selected target and
transport, bounded return, lifecycle action, AW proof result, intent/closeout
status, and routed residue.
