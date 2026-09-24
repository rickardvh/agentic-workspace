# Select the current need

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "Which configuration concern needs procedure now?",
  "branches": [
    {
      "id": "selection",
      "description": "Select the affected behavior",
      "next": "references/selection.md"
    },
    {
      "id": "consequences",
      "description": "Authorize and verify a change",
      "next": "references/consequences.md"
    },
    {
      "id": "package",
      "description": "Package lifecycle and host exposure",
      "next": "references/package.md"
    },
    {
      "id": "boundaries",
      "description": "Source and unavailable-runtime boundaries",
      "next": "references/boundaries.md"
    }
  ],
  "activation": {
    "occasions": [
      "observation",
      "binding"
    ],
    "applicability": "Installation, invocation, environment or configuration information requires a current durable choice or repair.",
    "outcome": "Usable current configuration with unresolved owner readiness stated.",
    "binding_owners": [
      "configuration"
    ]
  }
}
```

Select by current meaning. Unknown, deferred and no-match answers grant no effect.
