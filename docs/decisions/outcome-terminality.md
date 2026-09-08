# Terminality belongs to the selected outcome

Status: current reconstruction boundary. Repository-owned decision; no AW installation is needed to read or retain it.

## Decision and consequence

Owner-local quiescence does not establish task terminality; closure concerns the selected outcome and its required obligations.

Do not terminalize a task from settled owners or block its completion on optional advice. Require the selected outcome owner and current required obligations to establish closure.

## Rationale and alternatives

Memory can have advice, Planning can have no active item, and Verification can hold evidence while the requested task remains unperformed. Conversely, unrelated optional work must not keep a completed selected outcome open.

Rejected: AND-ing owner terminal booleans or treating every contributed consequence as a task obligation. Independent ready actions are choices where their relations prove safety, not an automatic task conflict.

## Authority and provenance

Rickard supplied the product boundary in the linked owning issues and reconstruction instructions. Codex selected and condensed this record; that editorial contribution does not turn AW or Memory into its semantic author. The repository owner admits this provenance when accepting this record. Until that admission, it is a proposed source for automated consumption.

The structured authority basis binds the current repository intent document. The linked issues preserve the specific human boundary and discussion; they are evidence references, not runtime network dependencies. AW context informed the preservation work, without supplying deciding authority.

## Scope, evidence and supersession

Exact initial applicability: `path:crates/agentic-workspace-core/src/lib.rs`, `path:tests/test_v1_contract.py`. This bounded selection does not claim all future semantic applicability; broader relevance remains agent/owner judgment.

Authority/evidence: [#2989](https://github.com/rickardvh/agentic-workspace/issues/2989); [#2606](https://github.com/rickardvh/agentic-workspace/issues/2606); [System intent](../../SYSTEM_INTENT.md).

Accepted implementation evidence: [PR #3032](https://github.com/rickardvh/agentic-workspace/pull/3032); [shared-core architecture](../architecture/shared-rust-core.md); existing #2909 shared-core and v1 conformance tests.

No prior decision identity is fabricated. The rejected mechanisms above are alternatives, not invented historical records. A later superseding decision must explicitly name this identity, material revision and affected scope; retain this rationale.

```aw-decision
{
  "id": "aw:outcome-terminality",
  "decision": "Owner-local quiescence does not establish task terminality; closure concerns the selected outcome and its required obligations.",
  "consequence": "Do not terminalize a task from settled owners or block its completion on optional advice. Require the selected outcome owner and current required obligations to establish closure.",
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
    "path:tests/test_v1_contract.py"
  ],
  "dependencies": [],
  "context": [],
  "supersedes": []
}
```
