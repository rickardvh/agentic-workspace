# Select current procedure

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "Which part of this method does the current work need? Select only the relevant branch; no work needs no call.",
  "branches": [
    {
      "id": "select",
      "description": "Choose the smallest resource",
      "next": "references/select.md"
    },
    {
      "id": "operation",
      "description": "Propose and carry an exact resource operation",
      "next": "references/operation.md"
    },
    {
      "id": "build",
      "description": "Reserve reproducible build output",
      "next": "references/build.md"
    },
    {
      "id": "cleanup",
      "description": "Reconcile lifetime and clean up",
      "next": "references/cleanup.md"
    },
    {
      "id": "recovery",
      "description": "Recover bounded or interrupted resources",
      "next": "references/recovery.md"
    },
    {
      "id": "hygiene",
      "description": "Interpret local hygiene",
      "next": "references/hygiene.md"
    }
  ]
}
```
