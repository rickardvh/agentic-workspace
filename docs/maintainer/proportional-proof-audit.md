# Proportional proof selection: implementation evidence

This records the bounded author validation for #3673. It does not supply
independent PR review or parent-lane acceptance.

## Reading path

Previously, `testing-strategy.md` mixed evidence design, retention, review examples,
historical suite reductions, dated budgets, CI composition and contract guidance.
The ordinary path now starts with eight decisions: claim, possible failure,
existing evidence, smallest sufficient boundary, current validation, permanent
retention, escalation and stopping. Examples distinguish semantic, transport,
prose, generated-source and real-agent evidence.

The detailed historical reductions, budgets, CI composition and contract guidance
remain in [testing-reference.md](testing-reference.md), linked from the strategy.
The proof-selection entry and selection/claim references use the same decisions.
The repository operating instruction and Verification's test-evidence route point
to this model. No runtime proof authority or new test-policy engine was added.

## Assertion audit

The audit inspected text assertions in Python tests and Rust owner tests,
including positive/negative substrings, prefix checks, regexes and equality.
Each removed case asked whether authored guidance still contained particular
words. The surviving cases below establish independently observable contracts.
The PR diff supplies the exact before/after assertion inventory.

| Source family | Removed or changed | Retained evidence and reason |
| --- | --- | --- |
| Skills-first interface | Hard-coded bootstrap prose, wording checks on fallback uncertainty/recovery/authority; policy phrase check changed to source-body delivery parity | Actual source delivery, one ordinary registry entry, source links, generated parity and native write/currentness journeys |
| Contract catalogues and schema reference | Frozen headings, explanatory sentences and curated description wording | Public commands/field identifiers, schema validity, source-derived examples and generated-file parity |
| Issue and PR templates | Entire completion-audit wording test | Required issue field IDs, routes, template parsing and rendering behaviour |
| Historical external-agent evaluation | Frozen fallback, availability, coverage, authority and disposition prose | Structured outcome, provenance, schema and evidence-validation contracts |
| Release workflows and recovery | Explanatory source comments, help prose, recovery sentences and prose-only documentation test | Workflow conditions, exact commands, immutable artefact identity, structured release states and admission negatives |
| Reconstruction dispositions | Rationale, privacy and authority wording | Declared source classes, dispositions, ownership, structured destructive-readiness controls and coverage |
| PR comment handling and review preparation | Proof-hint, readiness and next-action wording; review authority sentence | Category selection, action status, source anchors, pagination, currentness and tool-command transport |
| Native startup, intent and source reconciliation | Asserted cautionary wording | Actual claim boundaries, restrictions, exact source delivery, stale request rejection and write custody |
| Compact command runner | Heartbeat disclaimer wording | Heartbeat cadence, process identity, result location and duplicate-run controls |

No prose-only fixture or independent runner remained orphaned: the removed
functions read shared templates/documents still used by the product, while mixed
tests retain their behavioural assertions. No replacement prose linter, wording
snapshot or permanent fresh-reader benchmark was introduced. Error diagnostics
that distinguish an observed failure and fixture text used to verify byte/content
transport remain text-bearing behaviour, not tests of writing quality.

## Fresh-reader selection exercise

On 27 September 2026, a fresh agent received four hypothetical change descriptions
and the current repository guidance, with no parent conversation, issue acceptance
list, diff or prescribed command. It was asked to select evidence rather than
execute hypothetical changes. These are author-side observations of selection,
not evidence that those four hypothetical patches were implemented.

| Case | Selected claim and risk | Evidence and retention choice | Escalation and stopping boundary |
| --- | --- | --- | --- |
| Startup prose distinguishing supplied text from live prerequisites | Readers choose the correct branch; wrong choices or needless queries falsify the claim | Decision-boundary inspection and a bounded reader exercise with unrelated control; no wording test | Repair observed confusion, repeat the affected exercise, stop when choices and required checks are supported |
| Rust stale-source fix with existing stale/fresh cases | Reject stale identity and admit current identity | Inspect and run existing owner cases; extend only for a missing recurring failure | Broaden only for an uncovered composition risk; stop after affected cases and required checks |
| Python/Node Unicode request transport | Changed adapters preserve Unicode without corruption or truncation | Focused cases at each independently affected adapter; reuse owner semantics | Installed/platform evidence only for unresolved packaging or encoding risk |
| Removing duplicate owner cases | Surviving scenario preserves distinct inputs, assertions and prerequisites | Compare coverage and run the surviving scenario; no new test | Merge any genuinely unique coverage, then stop after equivalence and required checks |

The reader avoided prose snapshots, repeated binding semantics, one test per
acceptance bullet and broad provider matrices. It needed no command discovery or
user correction during the exercise. It did flag that the proof-selection entry
could imply a runtime call for hypothetical questions. The entry now distinguishes
actual validation from explaining a hypothetical choice using supplied facts.

## Validation and limits

The initial focused checks passed 114 cases across the affected catalogue,
evaluation, issue-template, preview, reconstruction, schema, workflow and comment
families. The native/interface subset passed 98 cases in 299.94 seconds. After
further mixed-test cleanup, 86 affected comment, review, recovery, command-runner,
schema and preview cases passed. These observations overlap; their counts are
not a count of unique requirements or a quality score.

The native subset covered more public adapters than the prose-only changes
required. That cost does not justify repeating it: unchanged owner semantics need
no further matrix. The two affected bootstrap and policy-delivery cases pass; generated payloads
are current and the repository Markdown check passes. Remaining checks are the
mandatory repository hooks and hosted checks. Stop
there unless a failure identifies a distinct remaining risk. No new permanent
test is needed for the strategy rewrite.
