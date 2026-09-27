# Select intent guidance

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "intent-need",
  "question": "Would unresolved intent change the next action, or does unfinished work need a saved plan?",
  "branches": [
    {
      "id": "intent",
      "description": "Plausible interpretations lead to different requested outcomes",
      "next": "references/intent.md"
    },
    {
      "id": "shape",
      "description": "Decide whether work needs continuity and which issue is the implementation target",
      "next": "references/shape.md"
    }
  ],
  "activation": {
    "occasions": [
      "observation"
    ],
    "applicability": "New information changes the intended outcome or leaves a material scope or instruction conflict unresolved.",
    "outcome": "The intended outcome is clear enough to proceed, or the exact unresolved source decision is named."
  }
}
```
