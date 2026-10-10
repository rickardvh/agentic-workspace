# Select current need

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "Would this new or continuing task benefit from decomposition or durable continuity, and do existing records already suffice?",
  "branches": [
    {
      "id": "intake",
      "description": "Reuse sufficient current records, explicitly relate an existing plan, or choose native creation for new work",
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
    "applicability": "New work needs useful decomposition or durable intent, constraints and dependencies beyond sufficient existing records; changed scope, accepted progress, interruption or handoff also has continuity value.",
    "outcome": "Sufficient existing task meaning is reused, or native Planning custody is created/selected and verified before needed meaning is lost; direct work needs no duplicate record.",
    "binding_owners": [
      "planning"
    ]
  }
}
```
