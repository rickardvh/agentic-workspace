# Choose evidence for a change

Use this procedure before choosing validation or adding, changing or removing a
test. The aim is to find the smallest observation that could expose a real error
in the changed behaviour. Required repository checks and independent review still
apply. A passing command supports only the behaviour it actually exercises.

## Make the selection

1. **Name the claim.** State what should now happen, for which input or situation.
   For example: “The CLI forwards every repeated `--changed` value.” Avoid claims
   such as “the feature works” that give no way to recognise failure.
2. **Name what could go wrong.** Identify the error that would make the claim
   false: a dropped argument, stale permission accepted, missing source delivered,
   or an agent choosing the wrong branch. Group examples of the same error.
3. **Inspect existing evidence.** Find the current test or observation that already
   covers that error. Check its inputs, assertions and relevant dependencies.
   Reuse sufficient current evidence; rerun it when the patch changes what it tests.
4. **Choose the smallest sufficient boundary.** Test shared semantics in the Rust
   component that owns them. Use an operation test when several components must
   work together. Exercise a public adapter only for a distinct argument, encoding,
   packaging or result-transport risk. A private function's implementation shape
   is not a stable contract merely because it is easy to assert.
5. **Validate this patch.** Run or inspect the evidence selected above, with its
   actual prerequisites. A temporary reproduction or focused manual observation
   can be enough. Explain what it establishes and any remaining uncertainty.
6. **Decide separately what to retain.** No new permanent test is a normal result.
   Retain a test only for a recurring kind of failure that current stable evidence
   does not cover. Prefer extending, merging or moving an existing case. A bug
   reproduction that fails before a fix is useful validation, but does not alone
   justify another permanent regression or another ordinary CI job.
7. **Broaden only for a named remaining risk.** State which observation is missing
   and why a broader suite, public surface, platform or real model can supply it.
   More confidence, by itself, is not a reason to run everything.
8. **Stop when the claim is supported.** Once the selected evidence and required
   checks cover the material risks, stop. Report any failed, skipped, unavailable
   or incomplete required evidence accurately. A narrow success does not establish
   whole-repository readiness, issue completion or independent acceptance.

These are questions to answer during the work, not a new form or proof ledger.
Use the existing proof-selection and Verification paths for current requirements,
execution receipts and claim decisions.

## Recognise evidence at the wrong level

| Change or claim | Useful evidence | Unnecessary or misleading evidence |
| --- | --- | --- |
| A skill should help an agent choose between direct work and a current-state query | Review the decision boundary; for material behaviour changes, a bounded fresh-reader exercise with an unrelated control | Phrase, regex, snapshot or whole-document assertions about the author's wording |
| An owner rejects stale source identity | Its existing semantic admission/currentness cases, extended only for a missing failure class | Repeating the same rejection through every binding |
| CLI argument forwarding or package contents changed | Focused adapter or installed-package evidence for the affected boundary | Re-proving unchanged owner semantics through those adapters |
| Generated guidance must match its source | Source/payload parity, schema checks and resolvable links | Treating generated-byte equality as evidence that the guidance is understandable |
| A deterministic implementation changes while existing tests already cover its failure modes | Run the affected stable cases and inspect the patch | Adding a permanent test for every acceptance bullet |
| Agent interpretation or a provider interaction materially changes | A finite real-agent/provider exercise for that behaviour, with failures and interventions recorded | Treating deterministic fixtures as model behaviour, or running a provider matrix for every code edit |

Do not freeze human or agent prose with executable wording assertions. Preserve
text-bearing tests when exact text is the behaviour: input/output transport,
public identifiers, generated-source parity, schema/front-matter validity or
link resolution. A sentence asserting a policy does not prove that policy is
followed. Delete that assertion rather than changing the expected sentence.

## Retain, combine or remove a test

Keep distinct behavioural coverage at the lowest stable boundary. Merge cases
that share setup and establish the same behaviour; move misplaced command-level
semantics to their owner. Remove duplicate, obsolete and implementation-shape
assertions. Preserve equivalent or stronger coverage for real lifecycle,
authority, recovery, installation and public-transport risks. A prose-only test
needs no executable replacement because it never established those behaviours.

Permanent tests describe durable behaviour, not an issue number or temporary
batch. Repeating an adapter case requires a failure that adapter can have
independently. Selecting a test for this patch does not automatically put it in
ordinary CI. Required broad or release checks remain binding at their own scope.

## Explain the decision in the PR

A short paragraph or table should identify the changed claim, failure risk,
existing evidence reused, any test added/merged/moved/removed, and why the chosen
level is sufficient. Explain any recurring CI cost or public-surface repetition.
End with the observation that allowed proof to stop, or the named remaining risk
and bounded next check. Passing tests do not justify meaningless test retention.

For example: “The changed CLI path could drop repeated arguments. The focused
adapter case exercises both values; existing owner cases cover their meaning.
No new semantic test is needed. Stop after argument fidelity and required checks
pass; broaden only if platform-specific encoding remains unresolved.”

## Look up detail only when needed

- [CI composition and broad/release invocation](testing-reference.md#validation-runtime-composition)
- [Native and binding ownership](testing-reference.md#native-and-binding-ownership)
- [Contract levels and retained case guidance](testing-reference.md#contract-ladder)
- [Historical reductions and dated budgets](testing-reference.md#historical-reduction-evidence)
- [Lazy decision and continuation boundaries](testing-reference.md#lazy-frontier-regression-boundary)
- [Retained test knowledge](test-knowledge-inventory.md)
