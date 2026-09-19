# Select Memory method

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "Which current Memory need is supported by the selected evidence?",
  "branches": [
    {
      "id": "disposition",
      "description": "Retain, retire or promote selected material",
      "next": "references/disposition.md"
    },
    {
      "id": "repair",
      "description": "Repair and receiving evidence",
      "next": "references/repair.md"
    },
    {
      "id": "declarations",
      "description": "Inspect bounded declaration hygiene",
      "next": "references/declarations.md"
    }
  ]
}
```
