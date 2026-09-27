# Select the current need

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "What should change because of this correction or finding?",
  "branches": [
    {
      "id": "destination",
      "description": "Choose the source that controls the affected behaviour",
      "next": "references/destination.md"
    },
    {
      "id": "instructions",
      "description": "Publish a rule for this repository or this machine",
      "next": "references/instructions.md"
    },
    {
      "id": "other",
      "description": "Save advisory knowledge or a decision, or repair a reusable method",
      "next": "references/other.md"
    },
    {
      "id": "opportunity",
      "description": "Check whether policy permits acting on a useful improvement",
      "next": "references/opportunity.md"
    }
  ],
  "activation": {
    "occasions": [
      "observation",
      "binding"
    ],
    "applicability": "A material finding from source/test work, repeated friction, positive optimisation opportunity, correction, acquired conclusion, environment fact or source inconsistency can change current or future work.",
    "outcome": "The controlling source is corrected and checked, or the finding is saved as advice or deliberately not retained.",
    "binding_owners": [
      "instructions",
      "system-intent"
    ]
  }
}
```

Select by current meaning. Unknown, deferred and no-match answers grant no effect.
