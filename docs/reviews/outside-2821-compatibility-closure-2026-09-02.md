# Outside-2821 compatibility closure review

Date: 2026-09-02

Issues reviewed: #2263, #2276, #2613, and #2817.

## Decision

#2263, #2276, and #2613 are implemented at the current stack head. #2817 remains an evidence-bound continuation: its product mechanics are implemented, including separate parent custody and bounded-child authority, but its required unrelated supported-host run has not occurred after the final lifecycle repairs. This review does not substitute deterministic fixtures or direct host fan-out for that run.

## Acceptance mapping

| Issue | Current implementation and evidence | Result |
| --- | --- | --- |
| #2263 reproducible runtime/contract pair | `scripts/run_agentic_workspace.py` admits active source identity before effects, reports `unsynchronized-source-runtime` on a resource-incomplete frozen/no-sync environment, returns exact `uv sync --frozen --project ...` recovery, and preserves synchronized environments without mutation. `tests/test_agentic_workspace_launcher.py::test_active_no_sync_runtime_identity_is_stable_across_two_checkouts` exercises mismatched, missing-dependency, recovered, and stable paths across fresh checkout fixtures. Installed-state projections retain expected/actual contract, package-resource, invocation, source, lock, repair, and claim-boundary evidence. | satisfied |
| #2276 provider-neutral external owners | External observations remain immutable, relationship-bound, relevance-filtered, explicitly promoted, and non-authoritative for Planning completion or AW proof. Explicit GitHub number refresh now probes the PR owner before the issue owner, preserves `pull-request`, distinguishes open/closed/merged, carries generic completion state, and confines merge time/commit to provider detail. GitHub issue and synthetic-provider behavior continue through the same admitted observation vocabulary. | satisfied |
| #2613 orthogonal source-owned controls | Scoped Markdown plus semantic task-route facts own ordinary guidance. Delegation aliases derive from one policy and target eligibility derives from canonical capability/forbidden facts. Session-path and assurance-level aliases cannot coexist with canonical owners; classifier selection, proof command role, installed capability owner, terminal assurance disposition, CLI version constraint, and payload release constraint reject contradictory sibling ownership. The repo removed its duplicate `dogfood_latest` authoring and retains `target_release = "source-current"` as the canonical payload owner. Broad posture/config objects remain diagnostic; ordinary assignment, Verification, proof, and continuation results expose bounded semantic effects. | satisfied |
| #2817 ordinary binding orchestration | Parent task custody and child execution authority are separate in the ordinary result; binding non-local winners compile to revision-bound dispatch; failed transports cannot silently become local work; host-native and process returns preserve import/admit/integrate/proof/reconcile authority. Unconfigured/local-preferred direct work now resolves to `continue-local-work` instead of paying an unavailable-assignment tax. Focused and real #2947 lifecycle evidence exists. The final same-policy unrelated substantive run with a naturally winning non-local child and retained-local sibling is still absent. | open acceptance residue |

## #2613 current audit dispositions

| Reopened audit family | Disposition |
| --- | --- |
| delegation role/mode/down-routing/transport readiness | one canonical assignment policy plus typed transports; compatibility aliases have a 1.0.0 removal target |
| session path redaction and subsystem assurance level | canonical owner plus rejected co-authoring with legacy alias |
| assurance classifier owner/source | one discriminated classifier choice; invalid owner/source combinations fail closed |
| proof command roles | one command identity may occupy exactly one role |
| CLI minimum/exact versions | mutually exclusive schema/runtime constraint choices |
| payload source-current intent | `target_release` is canonical; `dogfood_latest` is compatibility shorthand and cannot coexist |
| requirement waiver/dismissal | one terminal disposition only |
| target capability/safety/routing | capability classes and forbidden classes derive eligibility; target-local escalation is ignored compatibility metadata; best-fit selection owns the winner |
| assurance requirements/subsystems/closeout | specialist applicability records compile to the same proof/claim decision and do not create independent execution authority |
| local high-risk guidance | specialist sections share the local overlay owner and cannot create checked-in policy |
| installed runtime capability | payload install-target capability and CLI reader/runtime capability are separate owners; duplicate capability ids are rejected |

The resulting public model has fewer writable same-question dimensions. Retained authority layers remain meaningful in every legal combination: repository policy versus local capability, and broad safety ceilings versus feature permission.

## Proof and claim boundary

The focused provider-neutral refresh tests, config orthogonality tests, launcher clean-checkout fixture, schema/contract checks, generated-package parity, lint, and typecheck are the required implementation proof. Only an actual post-repair supported-host acceptance episode may satisfy #2817's `binding_automatic_assignment_organic_dogfood` evidence requirement.
