# Select the current review question

Establish independent eligibility from the trusted source before answering.
Choose the question that can change the current review decision. Rechecks begin
with the changed subject and prior findings; first reviews establish scope.
Unresolved scope, risk or authority admits unknown/defer, not guessed approval.

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "review-need",
  "question": "Which current uncertainty or obligation needs review procedure?",
  "context": [
    "references/eligibility.md"
  ],
  "branches": [
    {
      "id": "scope",
      "description": "Establish intended outcome and complete changed scope",
      "next": "references/scope.md"
    },
    {
      "id": "compatibility",
      "description": "Judge compatibility or a material risk boundary",
      "next": "references/compatibility.md"
    },
    {
      "id": "proof",
      "description": "Resolve evidence sufficiency and source-owner currentness",
      "next": "references/proof.md"
    },
    {
      "id": "recheck",
      "description": "Reobserve a changed subject and still-current prior findings",
      "next": "references/recheck.md"
    },
    {
      "id": "closure",
      "description": "Judge whether the bounded issue or parent outcome is satisfied",
      "next": "references/closure.md"
    },
    {
      "id": "decision",
      "description": "Report the supported outcome after required proof and eligibility",
      "next": "references/decision.md"
    }
  ],
  "activation": {
    "occasions": [
      "need"
    ],
    "applicability": "An externally initiated review needs an eligible independent reviewer and current proof.",
    "outcome": "Independent bounded findings and current review judgment; implementation custody cannot review itself."
  }
}
```

Selection supplies method only. It cannot record a verdict, waive proof, satisfy
independent review or authorise merge. Inspect additional context when it could
change the disposition; do not visit every branch by default.
