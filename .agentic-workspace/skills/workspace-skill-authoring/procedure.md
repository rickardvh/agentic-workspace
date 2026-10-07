# Choose the smallest useful skill change

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "authoring-need",
  "question": "What does the requested repository method need? Start plain; choose an addition only when it reduces repeated work.",
  "branches": [
    {"id": "plain", "description": "Create or improve a short ordinary skill", "next": "references/plain.md"},
    {"id": "structured", "description": "Substantial alternatives need selected resources or source-bound branch answers", "next": "references/structured.md"},
    {"id": "helper", "description": "An existing deterministic computation needs an explicit helper declaration", "next": "references/helpers.md"},
    {"id": "maintain", "description": "Qualify, merge, replace, remove or expose an existing method", "next": "references/maintain.md"}
  ]
}
```

If the required shape is unclear, keep the answer unknown or deferred and obtain
the missing task facts. A selected branch is advice, not permission or proof.
