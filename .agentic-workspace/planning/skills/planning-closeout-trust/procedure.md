# Select current need

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "Which part of this method is needed for current work?",
  "branches": [
    {
      "id": "intent",
      "description": "Compare the requested outcome",
      "next": "references/intent.md"
    },
    {
      "id": "finish",
      "description": "Reconcile proof, residue and continuation",
      "next": "references/finish.md"
    }
  ]
}
```
