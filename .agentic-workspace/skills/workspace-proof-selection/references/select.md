# Choose evidence before designing tests

Choose evidence for intended behaviour and plausible consequences of failure,
not patch size or shape. Minimise the lifetime cost of incorrect software and of
obtaining and using sufficient evidence: execution, maintenance, brittleness,
false failures, selection, diagnosis, safe change and future human/agent repair.
This default needs no configuration or Verification. Explicit applicable
repository, user and host requirements govern, including stronger proof floors
or different methods. They are constraints, not costs to trade away. Never invent
host commands, numerical risk scores, quotas or universal coverage targets.

**Design from the contract.** Before adding, changing or removing tests, identify
the contract, inspect existing coverage and select the relevant input classes,
boundaries, decisions, state transitions or interactions. Use properties, generated cases, real
integration checks or exploratory evaluation where they expose the risk better;
these are alternatives, not a checklist or a demand for new tooling.

**Check this change.** Use the smallest stable boundary that faithfully exercises
the risk. Do not mock away the behaviour being verified. Assert an expected result or invariant
justified independently of the new implementation. Avoid freezing incidental
wording, layout, internal calls or representation. Exact bytes, ordering,
accessibility and interactions remain testable when they are the contract;
word matching cannot judge prose quality or agent comprehension. Shared semantics
belong with their owner; transport, persistence, packaging or wiring can warrant
additional evidence for their own risks.

**Decide what to retain.** Checking this change, retaining test machinery and
choosing its recurring execution are separate decisions. Reuse sufficient
current evidence, extend coherent families and add distinct cases when they
improve protection, clarity or diagnosis. **No new
permanent test** is a normal outcome. A separate function is not a last resort;
one failure class may need several representatives, and a rare catastrophic risk
or new feature can warrant coverage before any escape. Do not optimise counts or
hide unchanged workload in giant parameterised tests.

**Repair the evidence gap.** Regression testing includes rerunning established
tests. For an escaped defect, reproduce it where practical and diagnose what prior evidence missed: input,
assertion, state, dependency fidelity, test boundary, execution selection or
requirement. Repair that gap at its natural owner. Retain a small deterministic
counterexample when broader coverage does not reliably protect it; incident
history alone neither requires nor disqualifies retention. Keep diagnosis bounded
to the relevant abstraction, not a repository-wide audit.

**Choose when and what to run.** Retention does not put a test in every CI run or
authorise changing required gates or schedules. Run the cheapest adequate set,
including selection overhead: a fast relevant suite can cost less than meticulous
filtering. Broaden for material risk,
uncertain impact or a binding requirement; include discovery where established
tests may share a blind spot. Missing impact data is not evidence of no impact.
Reuse evidence only while relevant code, dependencies, configuration, environment
and assertion scope still apply.

**Preserve protection.** Merge or remove tests only when surviving evidence
preserves meaningful assertions, inputs, sequences, environmental distinctions and diagnostic value.
Shared line coverage or a history of passing does not establish redundancy.
Keep tests reliable, bounded and diagnosable; do not weaken expectations or retry
failures into an unqualified pass. Disclose missing protection during quarantine
and its responsible recovery path.

**Stop with an honest claim.** Stop when applicable obligations and material risks
have adequate current support, relevant failures are explained, and further optional checking is
unlikely to change the decision at proportionate cost. Disclose remaining
uncertainty without waiving unmet requirements. Use the existing work summary
when useful; no new ledger, permission request, full-suite ritual or AW
acknowledgement is required.

For a design, oracle, fidelity, retention or selection question needing more
detail, read the relevant part of [design examples and research](design.md).

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
