# One executable semantic authority

Status: current reconstruction boundary. Repository-owned decision; no AW installation is needed to read or retain it.

## Decision and consequence

Deterministic operating semantics execute in one Rust core; Python, Node and JSON adapt the same implementation.

Put new deterministic decision semantics in the shared Rust core. Keep Python/Node adapters thin and schemas declarative; leave semantic judgment with the responsible agent or human.

## Rationale and alternatives

Parallel Python and TypeScript semantics previously made a contract change require several implementations and parity repair. One implementation lowers that recurring cost while language-neutral shapes remain useful.

Rejected: handwritten parallel runtimes, moving both into a generator, or making JSON an executable policy language. A shared core trades native packaging work for one semantic maintenance boundary.

## Authority and provenance

Rickard supplied the product boundary in the linked owning issues and reconstruction instructions. Codex selected and condensed this record; that editorial contribution does not turn AW or Memory into its semantic author. The repository owner admits this provenance when accepting this record. Until that admission, it is a proposed source for automated consumption.

The structured authority basis binds the current repository intent document. The linked issues preserve the specific human boundary and discussion; they are evidence references, not runtime network dependencies. AW context informed the preservation work, without supplying deciding authority.

## Scope, evidence and supersession

Exact initial applicability: `path:crates/agentic-workspace-core/src/lib.rs`, `path:src/agentic_workspace/decision.py`, `path:bindings/node/semantic-decision.mjs`. This bounded selection does not claim all future semantic applicability; broader relevance remains agent/owner judgment.

Authority/evidence: [#2987](https://github.com/rickardvh/agentic-workspace/issues/2987); [#3020](https://github.com/rickardvh/agentic-workspace/issues/3020); [System intent](../../SYSTEM_INTENT.md).

Accepted implementation evidence: [PR #3042](https://github.com/rickardvh/agentic-workspace/pull/3042); [shared-core architecture](../architecture/shared-rust-core.md); existing #2909 shared-core and v1 conformance tests.

No prior decision identity is fabricated. The rejected mechanisms above are alternatives, not invented historical records. A later superseding decision must explicitly name this identity, material revision and affected scope; retain this rationale.

```aw-decision
{
  "id": "aw:shared-semantic-authority",
  "decision": "Deterministic operating semantics execute in one Rust core; Python, Node and JSON adapt the same implementation.",
  "consequence": "Put new deterministic decision semantics in the shared Rust core. Keep Python/Node adapters thin and schemas declarative; leave semantic judgment with the responsible agent or human.",
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
    "path:src/agentic_workspace/decision.py",
    "path:bindings/node/semantic-decision.mjs"
  ],
  "dependencies": [],
  "context": [],
  "supersedes": []
}
```
