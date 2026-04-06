# <Title>

## Status

Stable | Active | Needs verification | Deprecated

Use one status exactly as written above.

## Scope

<system / workflow / operator task>

## Applies to

List concrete files, modules, tools, commands, or runtime surfaces that this note relates to.

Use concrete paths, modules, tools, commands, or runtime surfaces so agents can match touched files to relevant notes quickly.

This helps agents determine relevance from touched files during a task.

Examples:
- scripts/<operator-task>.sh
- <deployment or maintenance command>
- <runtime endpoint or admin surface>

## Load when

- <When an operator or agent should use this runbook>

## Review when

- <What changes require the runbook to be re-checked>

## Failure signals

- <Operational symptoms that indicate this runbook may apply>

## When to use this

- <Entry conditions>

## Symptoms

- <Observed behaviour>

## Checks

- <Facts or diagnostics to gather first>

## Steps

1. <Step one>
2. <Step two>
3. <Step three>

## Verification

- <How to confirm the procedure worked>
- Optional: add a short expected-state checklist here when production verification matters.

## Boundary reminder

- Keep the runbook focused on durable facts, entry conditions, symptoms, checks, boundaries, and verification.
- Move reusable maintenance choreography, refresh cadence, and multi-step workflow prose into a skill instead of expanding the runbook.

## Verified against

- Optional: list the exact files, interfaces, commands, or environments this runbook was last checked against.

## Pitfalls

- <Common mistakes or misleading signals>

## Last confirmed

YYYY-MM-DD during <task / PR / investigation>
