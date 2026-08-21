# Assurance Authority Contract

Agentic Workspace can consume repository assurance policy from either native workspace configuration or a repository-owned classifier. Both routes produce the same bounded application identity and neither grants mutation, waiver, proof, or completion authority.

`agentic_workspace.assurance_authority` owns four small contracts:

1. `build_assurance_application` binds a requirement id to its classification owner, source revision, relevant applicability input, and optional current-work identity. It deliberately stays separate from the proof subject.
2. `admit_repository_assurance_decision` admits only complete decisions from the configured owner and current source/input revisions. Missing, malformed, incompatible, stale, ambiguous, conflicting, and authority-widening outputs fail closed with a constructible refresh action.
3. `evaluate_assurance_disposition` keeps waivers and dismissals active only inside their optional application, source, work, proof-subject, expiry, and review bounds. Legacy reason-and-owner records remain compatible unless strict closeout is enabled; strict mode reactivates them for migration. Any inactive disposition re-exposes the original requirement and claim block.
4. `admit_external_evidence` is the internal normalization step. Public callers use `external-evidence.submit` and `external-evidence.query`; those operations accept an opaque signed host-result reference, derive producer custody inside AW, query repository evidence authority, and revalidate dependency-scoped source inputs before invoking normalization. Producer identity, issuer, result contract, result, and evidence reference never come from candidate-authored fields.

Evidence authorities live in `.agentic-workspace/verification/manifest.toml` under `[evidence_authorities.<id>]`. They are queryable through the Verification report, and the submission operation loads them directly rather than accepting a caller policy list. A host integration places a provider result in its protected inbox and gives the external consumer only an `external-evidence-host-result:<id>` reference. AW verifies the package-pinned issuer key, validity window, audience, replay identity, producer/result facts, proof route/class, and proof-subject digest. Repository-local keys, caller resolvers, `authenticated=true`, and submitted resolved-producer dictionaries cannot create custody. The producer, issuer, and transport remain distinct identities.

The generated Python and TypeScript clients expose both operations through the normal external-operation profile. Submission and query are stateless and deterministic: neither creates a second evidence ledger, and an ordinary proof owner may consume the compact admitted result. Query re-verifies the signed host result, current Verification declaration, and current source inputs, so a previously admitted result becomes stale when a dependency changes while unrelated repository edits remain quiet.

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
