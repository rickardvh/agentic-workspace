# Explicit source-owner admission

Known-provenance conformance source, authored by the Codex implementation session for #3044 on 2026-09-06. This records the agent-taken implementation choice made under the user's #3040 direction to keep source admission independent from caller-authored records. It does not assert human authorship or human confirmation of that implementation choice.

The choice prevents unreviewed working-tree actor strings from impersonating deciding authority. The trade-off is conservative re-admission after source changes. Rejected: automatically following HEAD, trusting a recognized filename, or deriving human authority from the record's own labels.

This fixture preserves that newly authored decision for the no-native-owner Memory journey. It is not copied from a repo ADR, a synthetic historical Memory migration, or an April-note disposition. The test host atomically creates the source while absent and explicitly admits the exact snapshot and owner. Only a later independent native admission permits promotion. No file is retired by this read-only slice.

Evidence: [#3044](https://github.com/rickardvh/agentic-workspace/pull/3044), [#3040](https://github.com/rickardvh/agentic-workspace/issues/3040), [System intent](../../SYSTEM_INTENT.md).

```aw-decision
{
  "id": "aw:explicit-source-admission",
  "decision": "Require an explicit source-owner snapshot admission before projecting durable decision provenance.",
  "consequence": "Do not advance decision provenance admission from HEAD or from mutable record actor strings. Require the source owner to admit the exact snapshot before reuse.",
  "authors": [
    {
      "kind": "agent",
      "id": "codex:3044-source-admission"
    }
  ],
  "contributors": [],
  "authority": {
    "actor": {
      "kind": "agent",
      "id": "codex:3044-source-admission"
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
    "path:crates/agentic-workspace-core/src/decision_source.rs"
  ],
  "dependencies": [],
  "context": [],
  "supersedes": []
}
```
