---
name: planning-orchestrator-workflow
description: Execute the assigned-orchestrator procedure from a binding canonical assignment and action gate without reselecting the target.
---

# Planning Orchestrator Workflow

Use this skill only when the current decision identifies this runtime as the
assigned orchestrator and carries a binding non-local assignment plus its
allowed action. Assignment role, target relation, identity, and revision are
structured inputs; task wording does not activate this procedure.

When the canonical assignment selects the current target, continue through the
ordinary direct-work owner and do not load this skill. When assignment is absent
or unresolved, return to the canonical assignment owner; use
`planning-assurance-delegation` only if that owner requests unresolved
assurance input.

## Primary Ownership

This is the sole primary post-assignment orchestrator procedure. It preserves
orchestrator custody of intent, decomposition, assignment bounds, admission,
integration, proof interpretation, and closeout. Canonical assignment and
action-gate operations own target choice and implementation permission; this
skill consumes their result and never recomputes it.

## Procedure

1. Read the compact current decision and verify that the assignment and allowed
   action identities and revisions are current. Re-resolve stale or missing
   identity instead of reconstructing it from Planning prose.
2. Preserve the assigned slice, target, proof requirements, stop conditions,
   and return contract exactly. Do not rerank targets, repeat capability or cost
   comparison, or reinterpret a binding non-local assignment as local work.
3. Execute only the transport or dispatch route admitted by the current action:
   - use the host's typed internal/automatic dispatch action when present;
   - route admitted manual transport to `planning-manual-delegation` and the
     canonical `assignment.export` / `assignment.import` operations;
   - use an admitted external adapter only with the same assignment identity,
     revision, work bounds, and return contract.
4. Track returned, failed, blocked, cancelled, stale, or stopped work through
   the canonical delegated-run lifecycle. Transport success is not worker
   success, admission, integration, proof, or closeout.
5. Route every return to `planning-returned-result`. Use the exact current
   `assignment.admit`, `assignment.reject`, `assignment.repair`,
   `assignment.reassign`, `assignment.override`, or `assignment.integrate`
   action rather than hand-editing lifecycle state.
6. After admitted integration, run AW-owned proof, route semantic satisfaction
   to `planning-intent-verification`, and route closeout mechanics to
   `planning-closeout-trust`. Worker claims cannot authorize those transitions.
7. Reconcile durable residue and the assignment outcome into the checked-in
   owner before review, handoff, or session end.

## Binding Boundary

- A binding non-local assignment forbids local implementation of the worker
  slice. If dispatch cannot proceed, stop at the current action and use its
  repair, reassign, override, or human-escalation route.
- Only an authorized structured assignment transition can change the selected
  target. Availability, convenience, token cost, or expected speed cannot.
- The orchestrator may delegate bounded transport or execution, but not its
  custody of intent, decomposition, admission, integration, proof
  interpretation, or closeout.
- Do not make vendor-specific routing policy or duplicate assignment/run state
  in skill prose.

## Output

Record the assignment and action identities/revisions, dispatched target and
transport, bounded worker return, lifecycle action taken, AW proof result, and
any residue routed to the continuing owner.
