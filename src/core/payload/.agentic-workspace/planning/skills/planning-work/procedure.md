# Select current need

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "Which part of this method is needed for current work?",
  "branches": [
    {
      "id": "intake",
      "description": "Relate the current request to existing work",
      "next": "references/intake.md"
    },
    {
      "id": "structure",
      "description": "Bound the outcome and its dependencies",
      "next": "references/structure.md"
    },
    {
      "id": "continuity",
      "description": "Create or tighten accepted custody",
      "next": "references/continuity.md"
    }
  ],
  "activation": {
    "occasions": [
      "need",
      "binding"
    ],
    "applicability": "Changed scope, accepted progress, interruption or handoff has continuity value beyond this turn.",
    "outcome": "Current bounded Planning custody, or justified direct work without retained planning.",
    "binding_owners": [
      "planning"
    ]
  }
}
```
