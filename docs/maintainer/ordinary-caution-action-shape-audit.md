# Ordinary Caution Action-Shape Audit

## Purpose

This audit records the ordinary caution classes reviewed after #1755 so warning and gate work stays tied to concrete action effects instead of broad caution prose.

## Disposition

| Caution class | Ordinary surface | Disposition | Action effect |
| --- | --- | --- | --- |
| Objective drift | `implement` context | action-shaped and allowed in ordinary output | `objective_drift.action_effect` names allowed work, blocked completion claim, claim boundary, and selector. |
| External issue intent | `start` / `implement` issue-reference intent | action-shaped and allowed in ordinary output when task text names issue refs | `issue_reference_intent.action_effect` allows read/review or bounded slice work, blocks issue-scope and task-complete claims until refresh, and names the refresh command. |
| Knowledge gates | task posture packet | already action-shaped; retain in ordinary output only when matched gates affect design, edits, proof, or claims | Gate records name `force`, `next_allowed_action`, `forbidden_actions`, `required_actions`, `record_resolution_to`, and closeout boundaries. |
| Generated surface trust | `implement` generated-surface trust selector and compact context | action-shaped and selector-backed | `generated_surface_trust.action_effect` blocks generated-freshness and task-complete claims until refresh/validation, while allowing implementation to continue through the canonical source. |
| Required proof | proof obligations | action-shaped and allowed in ordinary output when proof is selected | `required_proof.action_effect` allows implementation, blocks task-complete claims, and points to `proof.proof_obligations.required_proof`. |

## Follow-up Boundary

This audit does not claim every warning class is finished. Future slices should prefer one caution family at a time and preserve the same minimum contract: force, allowed action, blocked claim/action, claim boundary, and resolution selector or command.
