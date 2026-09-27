# Select current procedure

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "What temporary resource does this task need, or what must be preserved before cleanup?",
  "branches": [
    {
      "id": "select",
      "description": "Decide whether temporary files or a separate checkout are necessary",
      "next": "references/select.md"
    },
    {
      "id": "operation",
      "description": "Create or change a resource through its returned request",
      "next": "references/operation.md"
    },
    {
      "id": "build",
      "description": "Reserve disposable tool output before creating an isolated checkout",
      "next": "references/build.md"
    },
    {
      "id": "cleanup",
      "description": "The task ended; preserve needed files and remove its temporary resource",
      "next": "references/cleanup.md"
    },
    {
      "id": "recovery",
      "description": "A resource operation was interrupted or its result is uncertain",
      "next": "references/recovery.md"
    },
    {
      "id": "hygiene",
      "description": "Inspect local files whose owner or lifetime is unclear",
      "next": "references/hygiene.md"
    }
  ],
  "activation": {
    "occasions": [
      "need",
      "binding"
    ],
    "applicability": "Current work actually needs scratch, isolation, resource recovery or terminal cleanup.",
    "outcome": "The smallest authorised resource is acquired or cleaned up through its current owner.",
    "binding_owners": [
      "workspace-resources"
    ]
  }
}
```
