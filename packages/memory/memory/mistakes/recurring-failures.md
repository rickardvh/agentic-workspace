# Recurring Failures

## Status

Active

## Scope

- Anti-trap notes for repeated or high-likelihood failure patterns that future contributors or agents could plausibly rediscover.

## Applies to

- Add concrete files, commands, or surfaces once the first recurring failure is known.

## Load when

- Debugging a regression with familiar symptoms.
- A verified lesson from one incident looks likely to catch future work in the same way.

## Review when

- A recurring failure entry no longer matches the real root cause.
- Related contracts, tools, or runtime surfaces change.

## Failure signals

- The same failure pattern keeps returning after unrelated changes.
- A competent contributor could plausibly repeat the same mistake without a durable warning.

## Rule or lesson

- No recurring failure pattern is recorded here yet.
- This note is anti-trap memory, not a bug tracker, issue mirror, or backlog.
- Add an entry after repeated recurrence, or after one verified incident that clearly exposes a trap likely to recur.
- Prefer stable lessons, verification cues, and practical fixes over incident history or triage detail.
- Keep entries concise, symptom-driven, and operational.
- Use one entry per recurring trap or root lesson.
- Move one-off bugs, active debugging, and status tracking into tests, canonical docs, issues, or the planning surface instead.

## Entry format

### Failure: <short symptom-first label>

Symptom
- <What users or developers observe>

Likely cause
- <Most common root cause>

Verify
- <Command, file, or test to check>

Fix
- <Practical correction>

Load when
- <When to read this entry>

Review when
- <When this entry must be re-checked>

Failure signals
- <Specific signal that this entry applies>

Last confirmed
2026-04-06 during <task / investigation>

## Verified against

- `memory/templates/`

## Last confirmed

2026-04-06 during bootstrap adoption
