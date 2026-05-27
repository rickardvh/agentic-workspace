# Routine Work Context

Agentic Workspace keeps canonical owner surfaces separate, but ordinary agents
should not have to choose among every internal concept before starting,
implementing, proving, and closing work. The routine work context is an
assembled router view over existing owners.

It does not store new knowledge. It answers five routine questions:

| Category | Routine question | Existing owners fronted |
| --- | --- | --- |
| Authority | What source, policy, or owner governs this work? | `effective_authority`, `authority_hierarchy`, standing intent, workflow obligations, assurance requirements, decision pressure |
| Active work | What is live, done, blocked, delegated, or waiting? | Planning state, current/next action, execution shape, continuation state, external work reconciliation |
| Evidence / proof | What must be shown before a claim is safe? | proof selection, proof confidence, assurance evidence, workflow obligations, closeout trust, completion options |
| Durable knowledge | What applies here that future agents should not rediscover? | Memory consult, durable facts, durable intent, standing intent, system intent |
| Promotion / residue | What should move to a stronger owner, become follow-up, or be dismissed? | durable intent promotion, improvement intake, decision pressure, Memory promotion metadata, closeout residue |

## Classification

| Concept | Classification | Router category |
| --- | --- | --- |
| Memory notes and durable facts | Canonical owner surface | Durable knowledge |
| `memory_consult` | Router/projection concept | Durable knowledge |
| Planning execplans and state | Canonical owner surface | Active work |
| `external_work_reconciliation` | Router/projection concept | Active work |
| Standing intent and effective authority | Authority projection | Authority |
| Assurance requirements | Config-owned evidence gate | Authority, evidence / proof |
| Workflow obligations | Config-owned lifecycle obligation | Authority, evidence / proof |
| Decision records / ADRs | Canonical owner surface | Authority, promotion / residue |
| `decision_pressure` | Router/projection concept | Authority, promotion / residue |
| Proof selection and proof confidence | Evidence/proof concept | Evidence / proof |
| `closeout_trust` | Claim-boundary and lifecycle action surface | Evidence / proof, promotion / residue |
| Improvement intake | Lifecycle action / routing concept | Promotion / residue |

## Workflow Placement

`start` should show compact category status when the task activates authority,
durable knowledge, or promotion pressure. It should not dump owner detail.

`implement` should make the projection selectable and verbose-visible for changed
paths, especially where authority, evidence, durable knowledge, or residue could
change the next safe action.

`proof` should continue to own proof selection. The routine context should only
explain which proof expectations are activated by repo authority or claim gates.

`report` is the best inspection home for the full assembled view:
`agentic-workspace report --section routine_work_context --format json`.

`closeout_trust` and completion options remain the claim boundary. They should
consume evidence and residue signals rather than move canonical ownership into
the routine context.

## Proportionality

Small bounded work should stay quiet when no category has attention. Detail
belongs behind selectors or report sections. The projection should surface when:

- it changes the safe next action;
- it changes proof or completion claim gates;
- stale, conflicting, or mis-owned knowledge can affect current work;
- a discovered constraint needs promotion, follow-up, or explicit dismissal.

The projection should stay quiet for unmatched assurance requirements, unrelated
Memory notes, unrelated ADR candidates, and broad historical audit detail.

## Boundary

This implements the first slice of #1150, #1151, and #1152 as a router
projection. It does not collapse Memory, Planning, ADRs, assurance requirements,
workflow obligations, proof, or closeout trust into a new generic knowledge
store.
