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

- This note is anti-trap memory, not a bug tracker, issue mirror, or backlog.
- Add an entry after repeated recurrence, or after one verified incident that clearly exposes a trap likely to recur.
- Prefer stable lessons, verification cues, and practical fixes over incident history or triage detail.
- Keep entries concise, symptom-driven, and operational.
- Use one entry per recurring trap or root lesson.
- Move one-off bugs, active debugging, and status tracking into tests, canonical docs, issues, or the planning surface instead.

### Failure: broad planned work bypasses active planning

Symptom
- A broad roadmap or autopilot run implements and closes issues while `agentic-workspace summary --format json` reports no active execplan.

Likely cause
- The agent treats GitHub issues, roadmap candidates, and chat context as enough execution authority, then uses Agentic Workspace only as an after-the-fact checker.

Verify
- Run `agentic-workspace summary --format json` and inspect `execution_readiness`, `planning_record`, and `execplans.active_count` before broad work.

Fix
- Promote the selected lane into `todo.active_items` plus an execplan before implementation; for roadmap-backed no-active-plan states, the compact output should recommend `promote-before-broad-work`.

Load when
- The user asks for autopilot, planned lanes, milestone sequences, broad roadmap implementation, or issue-closing implementation work.

Review when
- Summary/report execution-readiness behavior changes, or hard commit/closeout enforcement replaces the advisory guardrail.

Failure signals
- `execution_readiness.status` is `roadmap-needs-promotion` but implementation starts anyway.
- Closeout claims roadmap progress without checked-in planning residue.

Last confirmed
2026-04-26 during issue #322 planning-backed dogfooding guardrail work.

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
2026-04-05 during <task / investigation>

## Verified against

- `.agentic-workspace/memory/repo/templates/`

## Last confirmed

2026-04-05 during bootstrap adoption
