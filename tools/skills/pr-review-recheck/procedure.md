# Select the current review question

Establish independent eligibility from the trusted source before answering.
Choose the question that can change the current review decision. Rechecks begin
with the changed subject and prior findings; first reviews establish scope.
Unresolved scope, risk or authority admits unknown/defer, not guessed approval.

```agentic-procedure
{
  "kind": "agentic-workspace/procedure/v1",
  "id": "review-need",
  "question": "Which fact is missing before the reviewer can decide?",
  "context": [
    "references/eligibility.md"
  ],
  "branches": [
    {
      "id": "scope",
      "description": "Identify the requested outcome and every changed file",
      "next": "references/scope.md"
    },
    {
      "id": "compatibility",
      "description": "Check changed public inputs, outputs and material risks",
      "next": "references/compatibility.md"
    },
    {
      "id": "proof",
      "description": "Check whether the evidence proves this patch and its sources are still current",
      "next": "references/proof.md"
    },
    {
      "id": "recheck",
      "description": "Compare the new patch with prior findings and recheck affected evidence",
      "next": "references/recheck.md"
    },
    {
      "id": "closure",
      "description": "Judge whether the bounded issue or parent outcome is satisfied",
      "next": "references/closure.md"
    },
    {
      "id": "decision",
      "description": "Report a decision supported by the evidence and independent eligibility",
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
