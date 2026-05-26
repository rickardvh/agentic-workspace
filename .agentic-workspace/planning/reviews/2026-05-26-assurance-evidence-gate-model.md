# Assurance Evidence Gate Model Investigation

## Intent

GitHub #1131 asks for a design investigation under parent lane #1130. The answer is: reuse the existing assurance/proof/Planning/Memory/closeout machinery, add only a small repo-declared requirement fact model, and make evidence status a projection before adding any new store.

## Inventory

- Config already owns assurance posture: `assurance.default_level`, `agent_may_escalate`, `agent_may_deescalate`, `strict_closeout`, `proof_profiles`, `test_data_policy`, `decision_record_target`, `invariant_registry`, and `risk_registry`.
- Config also owns `workflow_obligations` with `summary`, `stage`, `force`, `scope_tags`, `commands`, and `review_hint`.
- Planning execplans already carry `adaptive_assurance`, `traceability_refs`, `control_gates`, `risk_registry_refs`, `invariant_refs`, `test_data_policy`, `proof_report`, `intent_proof`, `durable_residue`, and closeout fields.
- Proof already reads active Planning assurance and configured proof profiles, reports missing proof profiles, review aids, blocked commands, and proof confidence.
- `closeout_trust` already reconciles proof, intent, acceptance, package evidence, durable residue, strict closeout, and completion options.
- Memory is the anti-rediscovery layer and should not become the canonical store for active evidence.

## Minimal V1 Requirement Shape

Requirements should live under `assurance.requirements.<id>` unless implementation finds a schema blocker.

Stable fields:

- `level`: `low`, `medium`, `high`, or `critical`.
- `applies_to_paths`: path globs.
- `applies_to_task_markers`: repo-owned terms.
- `authority_refs`: docs, runbooks, registries, policies, or decision records to consult.
- `required_evidence`: free-form repo vocabulary, not AW domain semantics.
- `proof_profile`: existing `assurance.proof_profiles.<id>`.
- `workflow_obligation_refs`: existing or synthesized workflow obligations.
- `review_owner`: repo-local owner label.
- `force`: `informational`, `recommended`, `required-before-closeout`, or `blocking`.
- `blocking_claims`: completion option ids such as `claim-work-complete` and `close-parent-lane`.

The implementation should require at least one matching signal and should validate known enum fields, but leave evidence labels free-form.

## Evidence Status

Start with a projection, not a new evidence store:

```json
{
  "requirement_id": "privacy_data",
  "state": "matched|satisfied|missing-evidence|review-required|waived",
  "level": "high",
  "applies_because": ["changed path matched db/migrations/**"],
  "authority_refs": ["docs/compliance/privacy.md"],
  "required_evidence": ["authority_consulted", "risk_assessment"],
  "evidence_present": [],
  "missing_evidence": ["authority_consulted", "risk_assessment"],
  "proof_profile": "privacy",
  "workflow_obligation_refs": ["privacy_review"],
  "review_owner": "privacy-review",
  "blocking_claims": ["claim-work-complete", "close-parent-lane"],
  "next_action": {}
}
```

Evidence should be read from existing Planning/proof/closeout fields first. Add a command-owned writer only if direct-work evidence cannot be represented cleanly.

## Surface Integration

- `start`: report task-marker requirements and authority refs only when the task activates a requirement.
- `implement`: match changed paths plus task markers; expose detail behind selector/verbose and keep tiny output quiet unless a required action changes the next step.
- `proof`: include requirement-linked proof profile commands, review aids, disallowed commands, and residual missing evidence.
- `report --section closeout_trust`: summarize evidence status and add blockers to existing completion options.
- `report --section workflow_obligations`: let requirements reference or synthesize obligations rather than duplicate commands/reviews.
- `planning`: carry requirement refs, evidence status, proof profile, review owner, and claim boundary in existing execplan fields.
- `memory`: capture only durable lessons or unresolved assurance residue that future agents would rediscover.

## Completion Behavior

Missing high/critical required evidence should block `claim-work-complete` and `close-parent-lane` by default. `claim-slice-complete` can remain allowed only when the slice explicitly excludes that evidence or routes the continuation honestly. `request-review`, `route-residue`, and `stop-with-status` must remain available.

## Proportionality

A requirement should activate only from explicit evidence: path glob match, task marker match, active Planning requirement ref, proof profile ref, or risk/invariant ref. Configuring high-assurance requirements must not make unrelated small edits noisy.

## Follow-Up Issues

1. Minimal `assurance.requirements.<id>` fact model in config/schema/defaults/config output.
2. Requirement matching/projection into `start`, `implement`, and `report`.
3. Evidence status and `closeout_trust` completion-option gates.
4. Requirement-linked proof profile integration.
5. High-assurance and non-code dogfood fixtures after the first implementation slices exist.

## Non-Goals

- Domain compliance interpretation.
- A parallel `[compliance]` tree.
- A new evidence store by default.
- A new top-level command by default.
- Blocking all work in repos with assurance config.

## Validation

- `uv run agentic-workspace summary --target . --format json`
- `uv run agentic-workspace doctor --target . --modules planning --format json`
- `uv run python scripts/check/check_planning_surfaces.py`
