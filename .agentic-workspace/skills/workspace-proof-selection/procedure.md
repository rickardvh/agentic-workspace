# Select current procedure

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "Which part of this method does the current work need? Select only the relevant branch; no work needs no call.",
  "branches": [
    {
      "id": "select",
      "description": "Select current evidence and strategy",
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
  ]
}
```
