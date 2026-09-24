# Select current procedure

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "Which part of this method does the current work need? Select only the relevant branch; no work needs no call.",
  "branches": [
    {
      "id": "select",
      "description": "Establish unmet test/environment readiness before execution, then select current evidence and strategy",
      "next": "references/select.md"
    },
    {
      "id": "execute",
      "description": "Execute the selected native check",
      "next": "references/execute.md"
    },
    {
      "id": "receipt",
      "description": "Admit the exact receipt",
      "next": "references/receipt.md"
    },
    {
      "id": "claim",
      "description": "Judge the bounded claim",
      "next": "references/claim.md"
    },
    {
      "id": "recovery",
      "description": "Preserve effects through unavailable continuation",
      "next": "references/recovery.md"
    },
    {
      "id": "learning",
      "description": "Disposition of observed learning",
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
