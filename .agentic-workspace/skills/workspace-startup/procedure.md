# Select current procedure

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "Which procedure is needed for the current work? Select only applicable needs; after obtaining current entry context, clear work may continue directly.",
  "branches": [
    {
      "id": "ordinary",
      "description": "Clear work or responsibility boundaries",
      "next": "references/ordinary.md"
    },
    {
      "id": "evidence",
      "description": "Missing or conflicting evidence",
      "next": "references/evidence.md"
    },
    {
      "id": "owners",
      "description": "Current owner facts, requests or effects",
      "next": "references/owners.md"
    },
    {
      "id": "reconcile",
      "description": "Correction, post-action reconciliation or residue",
      "next": "references/reconcile.md"
    },
    {
      "id": "unavailable",
      "description": "Configured runtime is unavailable",
      "next": "references/unavailable.md"
    },
    {
      "id": "constraints",
      "description": "A current restriction needs interpretation",
      "next": "references/constraints.md"
    }
  ]
}
```

Known needs may follow their reference directly. An uncertain need
remains unknown; do not infer effects or requirements from a branch label.
