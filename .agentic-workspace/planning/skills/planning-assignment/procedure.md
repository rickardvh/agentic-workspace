# Select the current need

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "What does current executor policy require? Follow an existing assignment; resolve required admission before implementation, or consider advisory/optional delegation when useful.",
  "branches": [
    {
      "id": "local",
      "description": "Local is currently admitted, or nonbinding policy permits direct work without a useful delegation opportunity",
      "next": "references/local.md"
    },
    {
      "id": "delegate",
      "description": "A separate bounded outcome may benefit from delegation; request assessment",
      "next": "references/assessment.md"
    },
    {
      "id": "assessment",
      "description": "Required executor admission is unresolved, or current advice needs task requirements or worker comparison",
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
    "applicability": "Required-best-fit needs current executor admission before affected implementation; advisory policy needs a useful comparison; local-preferred has a concrete delegation opportunity; or an existing Assignment needs continuation. Passive local-preferred work stays direct.",
    "outcome": "Current admitted local execution or exact non-local dispatch/return under required policy; nonbinding advice or quiet direct work under permissive policy; scoped unresolved restrictions when admission is missing.",
    "binding_owners": [
      "assignment",
      "delegation"
    ]
  }
}
```
