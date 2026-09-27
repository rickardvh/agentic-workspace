# Select Memory method

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "current-need",
  "question": "Would this finding prevent future rediscovery, and which source should hold it?",
  "branches": [
    {
      "id": "destination",
      "description": "Choose between correcting a controlling source, saving advice, and saving nothing",
      "next": "references/destination.md"
    },
    {
      "id": "publication",
      "description": "An authored decision needs its current publication request",
      "next": "references/publication.md"
    },
    {
      "id": "candidate",
      "description": "The current result asks what to do with a proposed lesson",
      "next": "references/candidate.md"
    }
  ],
  "activation": {
    "occasions": [
      "binding"
    ],
    "applicability": "A returned lesson still needs a decision about correcting its controlling source, saving advice or retaining nothing.",
    "outcome": "The controlling source is corrected, advice is saved with authorisation, or no retention is justified.",
    "binding_owners": [
      "memory"
    ]
  }
}
```
