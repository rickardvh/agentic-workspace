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
  ],
  "activation": {
    "occasions": [
      "need"
    ],
    "applicability": "A Planning closeout claim has unresolved evidence, accepted progress or external review custody.",
    "outcome": "Truthful current Planning status with proof and independent acceptance kept separate."
  }
}
```
