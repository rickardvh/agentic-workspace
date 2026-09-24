# Select the current need

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "Before binding, does this bounded outcome justify local work, delegation assessment, or an unknown/defer answer? Once binding, which current owner continuation is needed?",
  "branches": [
    {
      "id": "local",
      "description": "Local capability is sufficient; no justified independent delegation benefit",
      "next": "references/local.md"
    },
    {
      "id": "delegate",
      "description": "A bounded independent outcome justifies current Assignment assessment, without granting eligibility",
      "next": "references/assessment.md"
    },
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
