# Select the current need

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "Which current need calls for this method?",
  "branches": [
    {
      "id": "assessment",
      "description": "Supply unresolved assessment",
      "next": "references/assessment.md"
    },
    {
      "id": "binding",
      "description": "Follow current role, target and transport",
      "next": "references/binding.md"
    },
    {
      "id": "manual",
      "description": "Carry a sealed manual packet",
      "next": "references/manual.md"
    },
    {
      "id": "return",
      "description": "Admit and integrate returned material",
      "next": "references/return.md"
    },
    {
      "id": "recovery",
      "description": "Preserve uncertain transport and continuity",
      "next": "references/recovery.md"
    }
  ],
  "activation": {
    "occasions": [
      "binding"
    ],
    "applicability": "A current binding Assignment or dispatch/handoff consequence needs exact continuation.",
    "outcome": "An admitted local continuation, exact dispatch/handoff, or truthful current owner blocker.",
    "binding_owners": [
      "assignment",
      "delegation"
    ]
  }
}
```
