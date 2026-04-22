# Recurring Friction Ledger

## Status

Active

## Scope

- Lightweight evidence for repeated package or workflow friction that is real enough to preserve, but not yet strong enough to justify a dedicated issue or active plan.

## Applies to

- `.agentic-workspace/memory/repo/runbooks/dogfooding-feedback-routing.md`
- `.agentic-workspace/memory/repo/runbooks/dogfooding-usage-ledger.md`
- `.agentic-workspace/memory/repo/mistakes/recurring-failures.md`
- repo-local repeated friction discovered during ordinary work

## Load when

- The same ordinary package or workflow friction shows up again.
- You want to preserve a weak signal without opening a new issue yet.

## Review when

- Entries stop representing real repeated friction.
- A friction class graduates into planning, docs, tests, validation, automation, or direct implementation.
- The capture contract becomes too heavy for ordinary work.

## Failure signals

- The same friction is noticed in chat more than once without durable residue.
- A one-off signal keeps resetting because no issue was justified yet.
- Repeated friction is visible only in ad hoc retrospectives.

## When to use this

- The signal is real and recurring, but still below the threshold for active planned work or issue creation.
- You need one compact place to accumulate repeated package friction across sessions.
- You want a later promotion decision to be justified by actual recurrence rather than hindsight.

## Rules

- Keep one entry per friction class.
- Add only short recurrence bullets with a date plus the smallest useful context.
- Record the compact config-treatment answer on every entry; use `no_action` when current repo or local config does not materially change the treatment so that non-effect is still explicit.
- Route stronger follow-on into planning, canonical docs, tests, validation, automation, or code once the same class clearly repeats.
- Do not mirror issue bodies, execution logs, or narrative incident history here.

## Entry format

### Friction: <short recurring friction label>

Observed recurrences
- 2026-04-22: <short symptom plus surface>

Keep now
- <why this is still below issue or active-plan level for now>

Promote when
- <clear trigger for planning, issue creation, docs, test, validation, or automation>

Most likely remediation
- <docs | skill | script | test | validation | refactor | code>

Config treatment
- <promote | cleanup | retain | no_action plus the config cue that shaped this decision, or say that current config does not materially change it>

Last seen
2026-04-22 during <task or investigation>

## Verification

- Repeated friction can be preserved without opening an issue immediately.
- A later promotion decision can cite concrete recurrence bullets instead of chat memory.
- The note stays compact enough for routine maintenance.

## Boundary reminder

- This note is pre-backlog evidence, not a backlog, issue mirror, or execution log.
- Remove or shrink an entry once stronger remediation lands and the recurrence pressure is no longer needed.

## Last confirmed

2026-04-22 during issue #263 first slice
