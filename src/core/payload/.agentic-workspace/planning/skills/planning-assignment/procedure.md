# Select the current need

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "Has a worker already been selected? Follow that assignment; otherwise decide whether local work or delegation is useful.",
  "branches": [
    {
      "id": "local",
      "description": "Current capability is sufficient and delegation adds no justified benefit",
      "next": "references/local.md"
    },
    {
      "id": "delegate",
      "description": "A separate bounded outcome may benefit from delegation; request assessment",
      "next": "references/assessment.md"
    },
    {
      "id": "assessment",
      "description": "The result asks for missing task requirements or worker comparison",
      "next": "references/assessment.md"
    },
    {
      "id": "binding",
      "description": "A worker is selected; follow the assigned role, scope and permitted transport",
      "next": "references/binding.md"
    },
    {
      "id": "manual",
      "description": "The owner permits manual delivery of its exported assignment packet",
      "next": "references/manual.md"
    },
    {
      "id": "return",
      "description": "A worker returned a result; check it before integrating",
      "next": "references/return.md"
    },
    {
      "id": "recovery",
      "description": "Dispatch, return delivery or integration has an uncertain result",
      "next": "references/recovery.md"
    }
  ],
  "activation": {
    "occasions": [
      "need",
      "binding"
    ],
    "applicability": "A concrete pre-binding local/delegate choice needs judgment, or current binding Assignment/dispatch/handoff needs exact continuation. Unrelated ordinary local work does not need this method.",
    "outcome": "A quiet local or unknown/defer choice, current Assignment assessment for a delegate proposal, or exact binding continuation with truthful owner gaps.",
    "binding_owners": [
      "assignment",
      "delegation"
    ]
  }
}
```
