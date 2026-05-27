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

The projection also carries a `knowledge_authority_review` when existing
repo-owned metadata creates active pressure. That review composes Memory
manifest metadata, Memory promotion-pressure samples, workflow-obligation
matches, proof expectations, and closeout residue without becoming a new owner.

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

## Knowledge Authority Review

`knowledge_authority_review` is the concrete #1150 loop:

```text
scattered signal
  -> existing owner found
  -> authority / freshness / supersession / promotion metadata interpreted
  -> proof and closeout effects surfaced
  -> existing owner action suggested
```

For Memory, the review reads existing manifest fields such as `authority`,
`canonicality`, `canonical_home`, `routes_from`, `stale_when`, `evidence`,
`memory_role`, `promotion_target`, and `promotion_trigger`. A changed path that
matches `stale_when` becomes freshness pressure. A note marked
`candidate_for_promotion`, `improvement_signal`, or carrying a promotion target
becomes owner-shaped promotion pressure. Deprecated or canonical-elsewhere notes
become supersession pressure.

For workflow obligations, the review uses the existing
`workflow_obligations.match_evidence.match_count` shape, with fallback for
compact projections that already expose `match_count`.

The review suggests existing owner actions only, such as Memory freshness review,
Memory promotion reporting, or workflow-obligation inspection. It does not create
a generic knowledge queue.

## Workflow Placement

`start` should show compact category status when the task activates authority,
durable knowledge, or promotion pressure. It should not dump owner detail.

`implement` should make the projection selectable and verbose-visible for changed
paths, especially where authority, evidence, durable knowledge, or residue could
change the next safe action.

`proof` should continue to own proof selection. The routine context should only
explain which proof expectations are activated by repo authority or claim gates.
When a changed path activates a workflow obligation, proof can show the authority
and evidence/proof categories so the obligation is not missed before validation.

`report` is the best inspection home for the full assembled view:
`agentic-workspace report --section routine_work_context --format json`.

`closeout_trust` and completion options remain the claim boundary. They should
consume evidence and residue signals rather than move canonical ownership into
the routine context. Closeout surfaces compact knowledge-authority pressure so
Memory promotion or dismissal does not disappear behind "knowledge preserved
somewhere" when the stronger owner is docs, config, assurance, ADR, checks, or
explicit dismissal.

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

This closes #1150, #1151, and #1152 by providing the routine router model, the
owner-surface map, and the knowledge-to-action composition needed for scattered
authority, freshness, and promotion pressure. It does not collapse Memory,
Planning, ADRs, assurance requirements, workflow obligations, proof, or closeout
trust into a new generic knowledge store.

Still requiring agent or human judgment:

- whether a Memory promotion candidate should actually become docs, config,
  assurance, ADR, checks, or be dismissed;
- whether a stale note is wrong or merely needs re-confirmation;
- whether external authority evidence has an accepted repo interpretation;
- whether proof execution and closeout evidence are sufficient for a completion
  claim.
