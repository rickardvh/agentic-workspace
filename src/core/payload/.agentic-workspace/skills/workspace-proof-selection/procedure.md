# Select current procedure

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "What is missing before the selected result can support this task or completion claim?",
  "branches": [
    {
      "id": "select",
      "description": "Choose relevant evidence and verify that the test prerequisites are ready",
      "next": "references/select.md"
    },
    {
      "id": "execute",
      "description": "Run the exact check selected by Verification",
      "next": "references/execute.md"
    },
    {
      "id": "receipt",
      "description": "Use the current evidence continuation, or admit an external receipt explicitly",
      "next": "references/receipt.md"
    },
    {
      "id": "claim",
      "description": "Decide which outcome the current evidence supports",
      "next": "references/claim.md"
    },
    {
      "id": "recovery",
      "description": "A check may have run but its reply or next request is missing",
      "next": "references/recovery.md"
    },
    {
      "id": "learning",
      "description": "A returned lesson may prevent future rediscovery",
      "next": "references/learning.md"
    }
  ],
  "activation": {
    "occasions": [
      "need",
      "binding"
    ],
    "applicability": "A test, claim, review finding or missing prerequisite needs current evidence or readiness before proceeding.",
    "outcome": "Current prerequisite readiness, admitted evidence and an accurately bounded claim.",
    "binding_owners": [
      "verification"
    ]
  }
}
```
