# Choose the useful continuation

Identify an independently bounded outcome, needed capabilities, coupling to current
work, and the receiving context. Compare expected successful-completion burden,
including validation and integration. State uncertainty when there is no adequate
basis; use an unknown/defer answer rather than selecting a target speculatively.

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "continuation",
  "question": "Which continuation does the current outcome and evidence justify?",
  "branches": [
    {"id": "local", "description": "Local work has sufficient capability and delegation adds no justified value", "next": "references/local.md"},
    {"id": "delegate", "description": "An independent bounded outcome benefits from a receiving worker", "next": "references/delegate.md"},
    {"id": "handoff", "description": "A current admitted assignment needs a bounded receiving frontier", "next": "references/frontier.md"},
    {"id": "resume", "description": "A return, interruption or replacement requires current owner reconciliation", "next": "references/resume.md"}
  ]
}
```
