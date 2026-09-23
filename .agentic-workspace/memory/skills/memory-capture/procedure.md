# Select Memory method

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "Which current Memory need is supported by the selected evidence?",
  "branches": [
    {
      "id": "destination",
      "description": "Choose the smallest responsible home",
      "next": "references/destination.md"
    },
    {
      "id": "publication",
      "description": "Authored decision and publication",
      "next": "references/publication.md"
    },
    {
      "id": "candidate",
      "description": "Explicit candidate consequences",
      "next": "references/candidate.md"
    }
  ],
  "activation": {
    "occasions": [
      "binding"
    ],
    "applicability": "Current future-value material has an unresolved receiving-owner or retention disposition.",
    "outcome": "Current strongest-owner consequence evidence, authorised advisory Memory, or justified no-retention.",
    "binding_owners": [
      "memory"
    ]
  }
}
```
