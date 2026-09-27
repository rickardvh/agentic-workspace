# Select the current need

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "Which requested behaviour or reported setup gap needs attention?",
  "branches": [
    {
      "id": "selection",
      "description": "Identify the setting responsible for the requested behaviour",
      "next": "references/selection.md"
    },
    {
      "id": "consequences",
      "description": "Check authorisation, apply the setting and verify its consumer",
      "next": "references/consequences.md"
    },
    {
      "id": "package",
      "description": "Refresh package files, expose skills to the host, or assess updated setup",
      "next": "references/package.md"
    },
    {
      "id": "boundaries",
      "description": "Build the source runtime or handle unavailable setup tooling",
      "next": "references/boundaries.md"
    }
  ],
  "activation": {
    "occasions": [
      "observation",
      "binding"
    ],
    "applicability": "Installation, invocation, environment or configuration information requires a current durable choice or repair.",
    "outcome": "The requested configuration works, or its remaining prerequisite is identified.",
    "binding_owners": [
      "configuration"
    ]
  }
}
```

Select by current meaning. Unknown, deferred and no-match answers grant no effect.
