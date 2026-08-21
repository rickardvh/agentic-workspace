# Assurance Authority Contract

Agentic Workspace can consume repository assurance policy from either native workspace configuration or a repository-owned classifier. Both routes produce the same bounded application identity and neither grants mutation, waiver, proof, or completion authority.

`agentic_workspace.assurance_authority` owns four small contracts:

1. `build_assurance_application` binds a requirement id to its classification owner, source revision, relevant applicability input, and optional current-work identity. It deliberately stays separate from the proof subject.
2. `admit_repository_assurance_decision` admits only complete decisions from the configured owner and current source/input revisions. Missing, malformed, incompatible, stale, ambiguous, conflicting, and authority-widening outputs fail closed with a constructible refresh action.
3. `evaluate_assurance_disposition` keeps waivers and dismissals active only inside their optional application, source, work, proof-subject, expiry, and review bounds. Legacy reason-and-owner records remain compatible unless strict closeout is enabled; strict mode reactivates them for migration. Any inactive disposition re-exposes the original requirement and claim block.
4. `admit_external_evidence` treats provider output as a candidate until a repository-owned evidence authority admits the proof route and class together with a separate host-authenticated producer custody record. Producer identity, issuer, result contract, result, and evidence reference come from that resolved record, never from candidate-authored fields.

Evidence authorities live in `.agentic-workspace/verification/manifest.toml` under `[evidence_authorities.<id>]`. They are queryable through the Verification report. The host integration must resolve producer custody through its authenticated API, signature, or receipt boundary and pass an `agentic-workspace/resolved-evidence-producer/v1` record separately from the candidate. The producer, issuer, and transport are distinct identities: delivery through an API, CI bridge, or connector never authorizes the sender. External evidence remains a bounded reference, not an embedded log or durable ledger.

```toml
[evidence_authorities.acme_unit]
producer_id = "ci/acme"
issuer_id = "github-actions"
proof_route = "authoritative_validation"
evidence_class = "test-result"
result_contract = "pytest/v1"
allowed_results = ["passed", "failed"]
```

The ordinary operating decision accepts an optional repository assurance decision. An invalid requested decision becomes a typed blocker; an admitted decision contributes repository-policy obligations and its source/input revisions. If no classifier is configured, direct work remains quiet and existing config-native assurance behavior is unchanged.
