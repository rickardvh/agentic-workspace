# Select current procedure

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "What evidence or test-design decision does this task need?",
  "branches": [
    {
      "id": "select",
      "description": "Choose validation, permanent coverage and recurring cadence before authoring tests",
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
    "applicability": "Validation or test design is being considered, or a claim, review finding or missing prerequisite needs current evidence.",
    "outcome": "Proportionate validation, retention and cadence choices, ready prerequisites and an accurately bounded claim.",
    "binding_owners": [
      "verification"
    ]
  }
}
```
