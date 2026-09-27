# Select current need

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "Does this task continue a saved plan, need smaller steps, or need progress saved for later?",
  "branches": [
    {
      "id": "intake",
      "description": "Decide whether the current task belongs to the selected plan",
      "next": "references/intake.md"
    },
    {
      "id": "structure",
      "description": "Divide the outcome into complete steps with explicit dependencies",
      "next": "references/structure.md"
    },
    {
      "id": "continuity",
      "description": "Save agreed progress and remaining work, or resume a saved record",
      "next": "references/continuity.md"
    }
  ],
  "activation": {
    "occasions": [
      "need",
      "observation",
      "binding"
    ],
    "applicability": "Changed scope, accepted progress, interruption or handoff has continuity value beyond this turn.",
    "outcome": "The needed task record is saved and verified, or no plan is needed.",
    "binding_owners": [
      "planning"
    ]
  }
}
```
