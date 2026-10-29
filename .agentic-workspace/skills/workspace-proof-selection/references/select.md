# Choose evidence before designing tests

Optimise for the repository's lifetime: useful defect detection weighed against
maintenance, brittleness, refactoring coupling, execution frequency and cost,
false failures, duplicated semantics and future-agent rereads and repair. Include
the cost of missing an important regression. Test counts and raw coverage
percentages do not decide sufficiency.

This default applies without configuration or Verification. Explicit applicable
repository, user and host requirements take precedence, including stronger proof
floors or different test methods. A project strategy can specialise those choices
without repeating this baseline. Never weaken required evidence or invent host
commands. Make three separate judgments, not a new form or ledger:

1. **Evidence for this change.** State the behaviour or claim and a plausible
   material failure. Inspect existing current evidence, then choose the cheapest
   adequate focused observation: inspection, a one-off reproduction or a test
   run. Reuse sufficient evidence. Shared semantics belong with their owner;
   independently fallible public transport, packaging or composition may need
   their own proof.
2. **Permanent coverage.** Before adding a regression for an escaped bug,
   diagnose why existing evidence missed it: an absent input class or corner
   case, weak assertion, inaccurate mock, wrong test level, changed requirement
   or relevant test not run. Repair the natural contract owner first. Extend or
   correct its expectations, input partitions, boundary, property or conformance
   coverage where that keeps a coherent test family. A dedicated incident-specific
   regression is a last resort: explain its distinct durable failure class,
   ownership and why existing contract coverage cannot express it better.
   New feature contracts can independently warrant lasting tests. Merge, replace
   or remove redundant or brittle coverage when appropriate. **No new permanent
   test** is an ordinary successful outcome, requiring no exception or permission.
3. **Recurring execution.** Retaining a test does not put it in every PR or CI
   run. Choose its level and cadence for the risk and total recurring cost within
   binding requirements. Broaden only for a named residual risk or source
   requirement; stop when the claim and required checks have adequate support.

For example, inspect an incidental copy or layout edit instead of adding string
or DOM-order assertions. Exercise accessibility and interaction when affected;
exact wording or order remains testable when it is the required interface.
A serializer's missed Unicode boundary usually belongs in its existing
parameterised or property tests. A bad mock or omitted test may need fixture or
validation-selection repair with no new test. Discard temporary reproductions
once sufficient durable coverage exists. A new security or authority boundary
may justify a focused permanent test even as the suite grows.

Do not use wording assertions to judge prose quality or agent comprehension.
Structural checks and exact text transport can establish their own contracts.

## Obtain missing proof facts when needed

Resolve missing current Verification facts through `start` when needed. Read selected protocol purpose,
expected observations, escalation and review aids. Optional profiles remain behind
exact detail references; omitted alternatives are not absent alternatives.

Keep a known selected command on its existing `proof.report` path; a worker is
unnecessary merely to launch or monitor it. For a source-defined protocol
`analysis`, use the current Verification requirements request to select its
`analysis_receipt_ref`. The owner derives the question, relevant source inputs and
exact committed execution log. Confirm captured context sufficiency once, then use
current Assignment policy and its sealed read-only handoff. No Planning owner or
new prose task is needed. Missing or changed receipt, subject, log or environment
returns to Verification recovery/selection before export.

The analyst returns explanation or a specific blocker. Assignment admission makes
that analysis usable at the originating Verification investigation; it supplies no
passing receipt, sufficiency, independent approval or completion. Additional checks
use current Verification execution; repairs require separately authorised scope.

Before an upcoming check, establish its actual environment prerequisites through
the repository's current configuration and readiness mechanism. Reobserve live
services; durable knowledge of how to start a service is not evidence that it is
running. Use authorised readiness/start tooling or report its current blocker.
When new information repairs a missed prerequisite, verify that the stable
configuration/tooling affects the test journey, then disposition future value
through the strongest owner or no-retention. Do not assume `.env` is the owner.

If `required_execution.status` is `unique-required-action`, Verification has
established a unique missing requirement across current scope and alternatives.
Carry its exact request. Otherwise choose the relevant `execution_requests` item
only after judging current scope and strategy. One candidate is not a requirement.
Unknown applicability, real choices and unavailable evidence yield for judgment.

The following identity resolves a current exact selection request, or yields
missing/ambiguous. It never chooses the first check or executes it:

```agentic-owner-reference
{"kind":"request","owner":"verification","id":"verification/execute-selected/v1"}
```
