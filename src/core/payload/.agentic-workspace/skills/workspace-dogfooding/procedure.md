# Select upstream reporting

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "upstream-dogfooding",
  "question": "Did current work expose a material AW product defect in an opted-in repository?",
  "branches": [
    {"id": "report", "description": "Anonymise and deduplicate the AW finding, then publish through an existing host capability when current host/repository action authority allows the write, or hand off the safe report", "next": "SKILL.md"}
  ],
  "activation": {
    "occasions": ["observation"],
    "applicability": "Repository upstream dogfooding is enabled and current material describes a material defect or repeated friction attributable to AW itself, rather than the consumer repository.",
    "outcome": "A safe report is published under current host/repository action authority, existing coverage is confirmed, or the exact report is handed off with a precise authority, capability or privacy gap; the original task continues when safe.",
    "settled_by": [{"selector": "/configuration/upstream_dogfooding", "value": false}]
  }
}
```
