# Select the current need

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "Which owner destination needs correction or retention procedure?",
  "branches": [
    {
      "id": "destination",
      "description": "Choose and verify the responsible change",
      "next": "references/destination.md"
    },
    {
      "id": "instructions",
      "description": "Publish scoped instructions",
      "next": "references/instructions.md"
    },
    {
      "id": "other",
      "description": "Advisory knowledge, decisions or method repair",
      "next": "references/other.md"
    },
    {
      "id": "opportunity",
      "description": "Judge a selected repository opportunity",
      "next": "references/opportunity.md"
    }
  ]
}
```

Select by current meaning. Unknown, deferred and no-match answers grant no effect.
