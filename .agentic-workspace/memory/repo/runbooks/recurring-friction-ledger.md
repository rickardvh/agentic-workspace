# Recurring Friction Ledger

## Status

Active

## Scope

- Lightweight evidence for repeated package or workflow friction below issue or active-plan level.

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

- A friction class repeats during ordinary work.
- The signal is still below issue or active-plan level.
- You need a compact recurrence trail for later routing.

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
- <short reason this stays below issue or active-plan level for now>

Promote when
- <clear trigger for planning, issue creation, docs, test, validation, or automation>

Most likely remediation
- <docs | skill | script | test | validation | refactor | code>

Config treatment
- <promote | cleanup | retain | no_action plus the config cue that shaped this decision, or say that current config does not materially change it>

Last seen
2026-04-22 during <task or investigation>

### Friction: recurring-friction-proof-needed-manual-rescue

Observed recurrences
- 2026-04-23: Lane closeout verification showed that the recurring-friction path still needed an explicit repo-local proof entry before the installed report could demonstrate real preserved weak-signal usage.

Keep now
- Keep one short proof entry.

Promote when
- Promote if another task leaves this signal uncaptured.

Most likely remediation
- validation

Config treatment
- retain; current proactive posture favors one compact proof entry.

Last seen
2026-04-23 during issue #263 lane closeout

## Verification

- Repeated friction can be preserved without opening an issue immediately.
- A later promotion choice can cite concrete recurrence bullets instead of chat memory.
- The note stays compact enough for routine maintenance.

## Boundary reminder

- This note is pre-backlog evidence, not a backlog, issue mirror, or execution log.
- Remove or shrink an entry once stronger remediation lands and the recurrence pressure is no longer needed.

## Last confirmed

2026-04-23 during issue #263 lane closeout
