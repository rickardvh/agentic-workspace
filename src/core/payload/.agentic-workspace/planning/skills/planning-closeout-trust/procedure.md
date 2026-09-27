# Select current need

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "Does the delivered work satisfy the requested outcome, and what still needs evidence or a saved next step?",
  "branches": [
    {
      "id": "intent",
      "description": "Compare delivered work with the original and parent outcomes",
      "next": "references/intent.md"
    },
    {
      "id": "finish",
      "description": "Check evidence, preserve useful results and record what remains open",
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
