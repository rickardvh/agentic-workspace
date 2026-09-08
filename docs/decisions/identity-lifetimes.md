# Separate identity lifetimes

Status: current reconstruction boundary. Repository-owned decision; no AW installation is needed to read or retain it.

## Decision and consequence

Decision-view revision, material currentness, logical effect identity and execution attempt identity have different lifetimes.

Bind currentness to material dependencies and replay to admitted operation semantics. Unrelated view churn must neither stale an action nor create another logical effect; recovery attempts retain the effect identity.

## Rationale and alternatives

An aggregate revision changes whenever unrelated context changes. Using it as an effect or action key creates accidental repeats and invalidates safe work. Attempts must distinguish uncertain execution from a new owner-authorized generation.

Rejected: workspace revision as universal identity, random retry IDs as semantic authority, and historical next-decision replay. Exact invocation admission is still required before effect.

## Authority and provenance

Rickard supplied the product boundary in the linked owning issues and reconstruction instructions. Codex selected and condensed this record; that editorial contribution does not turn AW or Memory into its semantic author. The repository owner admits this provenance when accepting this record. Until that admission, it is a proposed source for automated consumption.

The structured authority basis binds the current repository intent document. The linked issues preserve the specific human boundary and discussion; they are evidence references, not runtime network dependencies. AW context informed the preservation work, without supplying deciding authority.

## Scope, evidence and supersession

Exact initial applicability: `path:crates/agentic-workspace-core/src/lib.rs`, `path:crates/agentic-workspace-core/src/attempt.rs`, `path:crates/agentic-workspace-core/src/continuity.rs`. This bounded selection does not claim all future semantic applicability; broader relevance remains agent/owner judgment.

Authority/evidence: [#2987](https://github.com/rickardvh/agentic-workspace/issues/2987); [#3000](https://github.com/rickardvh/agentic-workspace/issues/3000); [System intent](../../SYSTEM_INTENT.md).

Accepted implementation evidence: [PR #3032](https://github.com/rickardvh/agentic-workspace/pull/3032); [PR #3042](https://github.com/rickardvh/agentic-workspace/pull/3042); [shared-core architecture](../architecture/shared-rust-core.md); existing #2909 shared-core and v1 conformance tests.

No prior decision identity is fabricated. The rejected mechanisms above are alternatives, not invented historical records. A later superseding decision must explicitly name this identity, material revision and affected scope; retain this rationale.

```aw-decision
{
  "id": "aw:identity-lifetimes",
  "decision": "Decision-view revision, material currentness, logical effect identity and execution attempt identity have different lifetimes.",
  "consequence": "Bind currentness to material dependencies and replay to admitted operation semantics. Unrelated view churn must neither stale an action nor create another logical effect; recovery attempts retain the effect identity.",
  "authors": [
    {
      "kind": "human",
      "id": "rickardvh"
    }
  ],
  "contributors": [
    {
      "kind": "agent",
      "id": "codex"
    }
  ],
  "authority": {
    "actor": {
      "kind": "human",
      "id": "rickardvh"
    },
    "basis": [
      {
        "owner": "repository",
        "reference": "SYSTEM_INTENT.md",
        "revision": "sha256:b256160d13a2a8d47ab276cab83bf5beee3e77ecad5ca07358b2422239068e9a"
      }
    ]
  },
  "scope": [
    "path:crates/agentic-workspace-core/src/lib.rs",
    "path:crates/agentic-workspace-core/src/attempt.rs",
    "path:crates/agentic-workspace-core/src/continuity.rs"
  ],
  "dependencies": [],
  "context": [],
  "supersedes": []
}
```
