# Current repository coherence comparison

Assessment date: 2026-09-28. Scope: current operating bindings selected by the
[procedure](repository-state-coherence.md). Verification owns the current outcome
and observation time; replace this comparison when reassessing.

## Repository findings and controls

- `SYSTEM_INTENT.md`, `AGENTS.md`, the ownership ledger, shared configuration and
  operating instructions agree on selective source access and owner-mediated
  state changes. The configured native command exists. The ledger's optional
  Planning state file is absent by design; it is not a broken mandatory binding.
- Inspected the immediate instruction files and maintainer skill entries for
  additional current obligations. The new procedure is reached directly from
  Verification; no second registry, scheduler checklist or startup scan was added.
- The manifest's generated-adapter scenario distinguishes catalogue parity from
  runtime conformance. `generate_contract_catalogues.py --check` compares rendered
  catalogues with checked-in files; the scenario separately names public/native
  adapter tests. `make test-planning` still invokes the native Planning owner
  tests. These commands support their stated, bounded evidence claims.
- The selected Plan's next action still requested parent acceptance for #3641 and
  #3665 and described merge work as pending. Current accepted decisions settle
  those questions: [#3641 acceptance](https://github.com/rickardvh/agentic-workspace/issues/3641#issuecomment-5866948770)
  and [#3665 acceptance](https://github.com/rickardvh/agentic-workspace/issues/3665#issuecomment-5866950157).
  The relevant PRs [#3689](https://github.com/rickardvh/agentic-workspace/pull/3689)
  and [#3690](https://github.com/rickardvh/agentic-workspace/pull/3690) were merged.
  This was an incorrect current instruction, not a finding based on age.
- Supplied that finding to native `start`, established the selected-owner
  relation, then applied its exact `planning.update` action. The
  [Plan](../../../../.agentic-workspace/planning/execplans/work-5ca693423a3917d42ae51da2dabc0354349cfd1abb0a2152c0350cfd7534e79f.plan.json)
  now retains the accepted answer and has no repeated acceptance action.
  Its selector, lifecycle, historical proof and creation provenance were preserved.
- #3665 explicitly leaves #3548 as future scope. The operating instruction also
  preserves unresolved decision-point source custody. Both exceptions remain;
  neither was silently resolved by convention. Archived Plans and old receipts
  were not turned into tasks or rewritten.

No unresolved mismatch was found within these bounded comparisons. This does not
assert that all repository documents or product behavior have been audited.

## Finite drift exercise

Used an AW-owned disposable fixture with this exact requirement and procedure,
the five named dependency paths, and minimal host configuration. Native CLI and
executor-neutral JSON ingress returned the same due identity, reason, declaration
and procedure activation. The semantic comparisons below were maintainer judgments
against supplied current sources, not claims of an automated semantic checker.

| Introduced current drift | Comparison and outcome |
| --- | --- |
| Guidance binds ownership to absent `old/owner.md` | Current source assigns native Planning. Reported the wrong path and owner binding to the guidance owner. |
| Guidance says catalogue parity proves installed runtime behavior | Current source limits the command to source parity. Reported the unsupported evidence claim to the guidance owner. |
| Active next action repeats parent acceptance | `accepted.md` already settles it. Reported the obsolete continuation to Planning. The real repository repair above exercises that owner. |
| New unanchored procedure repeats the command mismatch | It remained quiet before expiry. After expiry, bounded current-directory discovery found the new procedure and the same evidence mismatch. |

An archived Plan still saying “review and merge,” a historical failed receipt,
and explicitly deferred adapter support remained unchanged controls. No new Plan
or issue was created. A `failed` assessment retained the current findings;
an `unknown` assessment retained a simulated unavailable GitHub decision without
inventing its answer. Its only claim restriction was parent-lane closeout.

Verification published satisfied assessments through its exact request, decision
and action. Repeated satisfaction replaced the same single map entry and was quiet
in compact ordinary entry. Changing the operating-guidance anchor made it due
immediately with `declaration-procedure-or-dependency-changed`. A new unanchored
file alone preserved satisfaction. For finite expiry testing, a still-valid
observation just inside the seven-day boundary was published; crossing that
boundary produced `freshness-expired` through both entry surfaces. No assessment
store was edited by hand.

## Validation boundary

The existing three standing-assessment lifecycle cases pass, together with one
new repository declaration/procedure wiring case. The new test checks native
acceptance and procedure reachability; it does not duplicate publication,
recovery or retirement tests or freeze procedure prose. The finite exercise
above covers semantic examples and history controls without a new recurring
test framework. Product correctness and independent PR review retain their own
evidence requirements.
