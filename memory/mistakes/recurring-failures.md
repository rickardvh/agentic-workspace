# Recurring Failures

## Status

Active

## Scope

- Symptom-first recurring failure patterns that matter across tasks.

## Applies to

- `<RELEVANT_MODULES_OR_SURFACES>`

## Load when

- Debugging a regression with familiar symptoms.
- A behaviour mismatch looks likely to repeat in future work.

## Review when

- A recurring failure entry no longer matches the real root cause.
- Related contracts, tools, or runtime surfaces change.

## Failure signals

- The same failure pattern keeps returning after unrelated changes.
- Contributors repeatedly ask whether a behaviour is expected or broken.

## Rule or lesson

- Keep entries concise, symptom-driven, and operational.
- Use one entry per recurring root problem.

### <Failure name>

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
YYYY-MM-DD during <task / investigation>

## Verified against

- `scripts/check/check_memory_freshness.py`
- `memory/templates/`

## Last confirmed

2026-03-17 during memory hardening review
