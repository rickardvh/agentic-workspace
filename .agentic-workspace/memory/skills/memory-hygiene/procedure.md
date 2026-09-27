# Select Memory method

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "What needs attention in the selected Memory material?",
  "branches": [
    {
      "id": "disposition",
      "description": "Decide whether to keep advice, stop selecting it, or confirm another source accepted it",
      "next": "references/disposition.md"
    },
    {
      "id": "repair",
      "description": "The note conflicts with a source or needs a change beyond disposition metadata",
      "next": "references/repair.md"
    },
    {
      "id": "declarations",
      "description": "Inspect selected note declarations for structural or routing errors",
      "next": "references/declarations.md"
    }
  ],
  "activation": {
    "occasions": [
      "need"
    ],
    "applicability": "Selected Memory advice is stale, duplicated or no longer useful.",
    "outcome": "Useful advice is preserved and an authorised disposition stops misleading selection."
  }
}
```
