# Select the current need

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "Which current need calls for this method?",
  "branches": [
    {
      "id": "triage",
      "description": "Receive and classify current findings",
      "next": "references/triage.md"
    },
    {
      "id": "continuation",
      "description": "Route a justified finding to its owner",
      "next": "references/continuation.md"
    }
  ]
}
```
