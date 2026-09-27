# Select current procedure

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "What is preventing the next authorised step? Choose only the help needed; clear work may continue directly.",
  "branches": [
    {
      "id": "ordinary",
      "description": "The next action needs current AW information or a configured command",
      "next": "references/ordinary.md"
    },
    {
      "id": "evidence",
      "description": "Required evidence is missing, unavailable or conflicts with another source",
      "next": "references/evidence.md"
    },
    {
      "id": "owners",
      "description": "AW returned a request to answer or an operation to invoke",
      "next": "references/owners.md"
    },
    {
      "id": "reconcile",
      "description": "A finding or correction may need a source change or saved lesson",
      "next": "references/reconcile.md"
    },
    {
      "id": "unavailable",
      "description": "The configured AW runtime cannot be used",
      "next": "references/unavailable.md"
    },
    {
      "id": "constraints",
      "description": "A result blocks an action or claim; determine what remains allowed",
      "next": "references/constraints.md"
    }
  ]
}
```

Known needs may follow their reference directly. An uncertain need
remains unknown; do not infer effects or requirements from a branch label.
