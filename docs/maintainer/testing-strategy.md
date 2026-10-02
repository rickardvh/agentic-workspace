# Choose evidence for a change

Use this procedure before choosing validation or adding, changing or removing a
test. The goal is to find the smallest observation that could expose a real error
in the changed behaviour. Required repository checks and independent review still
apply.

A passing command supports only the behaviour it actually exercises.

Changing a test also requires a semantic evidence decision: explain why added,
removed, merged or converted coverage is sufficient. That review does not require
an executable command of its own. Use the changed behaviour's existing proof
owner, reuse current evidence when sufficient, and retain the review through
Verification's current judgment. Run Verification-strategy tests when that
machinery changes or a named remaining risk needs them; an unrelated test edit
does not make that suite relevant. A source-only change that leaves test evidence
unchanged does not acquire this review merely because the repository has tests.

## Choose the right check

1. **State what should now be true.** Be specific about the input and expected
   result. “The CLI forwards every repeated `--changed` value” is useful;
   “the feature works” is not.
2. **State what could go wrong.** Name the error that would make that statement
   false: a dropped argument, stale permission, missing source, wrong branch or
   similar concrete failure.
3. **Look for an existing test or observation.** Reuse it when it already catches
   that failure and still applies to the changed code.
4. **Test at the lowest useful level.** Shared Rust behaviour belongs in the Rust
   component that implements it. Use a higher-level operation or package test only
   when components must work together or that interface can fail independently.
5. **Validate this patch.** Run or inspect the focused evidence with its real
   prerequisites. Explain what it proves and what it does not.
6. **Decide separately whether a permanent test is needed.** “No new test” is a
   normal outcome. Keep a new regression only for a recurring kind of failure
   that existing stable tests do not catch.
7. **Broaden only for a specific remaining risk.** Another platform, provider,
   package interface or broad suite needs a reason beyond “more confidence”.
8. **Stop when the relevant statement is supported.** Report failed, skipped or
   unavailable required checks accurately.

These are questions to answer during the work, not a new form or ledger.

## Recognise a check at the wrong level

| Change | Useful evidence | Usually unnecessary |
| --- | --- | --- |
| Agent-facing prose changes how an agent chooses a path | Review the decision and, for material behaviour, use a small fresh-reader exercise with an unrelated control | Phrase, regex, snapshot or whole-document assertions about wording |
| A component rejects stale source data | Its existing source-change cases, extended only when a failure is missing | Repeating the same rejection through every language binding |
| CLI argument forwarding or package contents change | Focused adapter or installed-package evidence | Re-proving unchanged shared semantics through those adapters |
| Generated guidance must match its source | Generation parity, schema checks and resolvable links | Treating byte equality as evidence that the prose is understandable |
| Existing tests already cover the changed deterministic behaviour | Run the affected stable cases and inspect the patch | Adding a test for every acceptance bullet |
| Agent/provider behaviour materially changes | One finite real-agent/provider exercise for that behaviour | Treating fixtures as model behaviour or running a provider matrix for every edit |

Do not freeze human or agent prose with executable wording assertions. Exact text
belongs in tests only when the text itself is the interface: public identifiers,
transport bytes, generated-source parity, schema/front-matter validity or link
resolution.

## Keep, merge or remove a test

Keep distinct behavioural coverage at the lowest stable level. Merge tests that
share setup and catch the same failure. Remove duplicate, obsolete or
implementation-shape assertions.

Preserve higher-level tests when they catch a real interface, installation,
recovery or packaging failure that lower-level tests cannot.

A bug reproduction is useful while fixing the bug, but the incident alone does
not justify another permanent test. The lasting test should protect a recurring
failure class.

Selecting a test for this patch does not automatically put it in ordinary CI.

## Explain the choice in the PR

A short paragraph or table should say:

- what changed;
- what could be wrong;
- which existing evidence was reused;
- which test was added, changed or removed, if any;
- why broader testing was unnecessary or what specific remaining risk requires it.

End with the observation that allowed testing to stop.

For example:

> The CLI change could drop repeated arguments. The focused adapter case exercises
> both values, while existing Rust tests cover their meaning. No new semantic test
> is needed. Stop after argument forwarding and required repository checks pass;
> broaden only if a platform-specific encoding problem is observed.

## Detailed references

Use these only when the change needs them:

- [CI and release-check composition](testing-reference.md#validation-runtime-composition)
- [Rust and language-binding responsibilities](testing-reference.md#native-and-binding-ownership)
- [Which level should own a test](testing-reference.md#contract-ladder)
- [Historical test reductions and budgets](testing-reference.md#historical-reduction-evidence)
- [Decision and continuation cases](testing-reference.md#lazy-frontier-regression-boundary)
- [Retained test knowledge](test-knowledge-inventory.md)
