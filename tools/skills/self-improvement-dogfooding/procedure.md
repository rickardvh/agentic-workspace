# Disposition a current repository finding

Read [the triage and authority boundary](SKILL.md), select the smallest consequence
the current evidence supports, then return to the original task. A weak annoyance
can be dismissed with justified `no-retention`, without an issue or retained note.

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "repo-dogfooding",
  "question": "What bounded consequence does this incidental AW finding require?",
  "branches": [
    {"id": "repair", "description": "Repair bounded defect or material friction within established intent", "next": "SKILL.md"},
    {"id": "evidence", "description": "Repair the evidence or conformance gap at its current owner", "next": "SKILL.md"},
    {"id": "follow-up", "description": "Route a distinct bounded issue or follow-up through the existing issue owner", "next": "SKILL.md"},
    {"id": "direction", "description": "Obtain human direction for a genuine product-shaping change", "next": "SKILL.md"}
  ],
  "activation": {
    "occasions": ["observation"],
    "applicability": "Current work in the AW repository exposes an incidental material defect, friction or wasted work attributable to AW, outside the adopted task outcome, even when that task can still succeed.",
    "outcome": "One bounded repair, evidence/conformance repair, distinct issue/follow-up, or human product-shaping decision is dispositioned through its existing owner; the original task continues. Weak findings may be dismissed without retention. Activation grants no write, proof, publication or closure authority."
  }
}
```
