# Select intent guidance

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "intent-need",
  "question": "Does current work need clarification of intent, classification for continuity, or both? Clear direct work needs neither ceremony nor a retained artifact.",
  "branches": [
    {
      "id": "intent",
      "description": "Resolve material uncertainty in the intended outcome",
      "next": "references/intent.md"
    },
    {
      "id": "shape",
      "description": "Classify continuity and distinguish implementation from reporting targets",
      "next": "references/shape.md"
    }
  ],
  "activation": {
    "occasions": [
      "observation"
    ],
    "applicability": "New information changes the intended outcome or leaves a material scope or instruction conflict unresolved.",
    "outcome": "A scoped intent judgment or exact source-owner reconciliation."
  }
}
```
