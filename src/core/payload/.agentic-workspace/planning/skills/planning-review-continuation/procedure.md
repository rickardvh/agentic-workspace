# Select the current need

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "Does the finding still apply, and does it justify a source change or saved next step?",
  "branches": [
    {
      "id": "triage",
      "description": "Check the review scope, evidence and source revision",
      "next": "references/triage.md"
    },
    {
      "id": "continuation",
      "description": "Choose the source to repair or the plan that should retain unfinished work",
      "next": "references/continuation.md"
    }
  ],
  "activation": {
    "occasions": [
      "need"
    ],
    "applicability": "Review findings or a worker return require current accepted continuation rather than assumed progress.",
    "outcome": "Supported findings have an authorised next step; approval remains separate."
  }
}
```
