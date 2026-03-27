# <Title>

## Status

Stable | Active | Needs verification | Deprecated

Use one status exactly as written above.

## Canonicality

agent_only | candidate_for_promotion | canonical_elsewhere | deprecated

Use `agent_only` for compact assistive memory.
Use `candidate_for_promotion` when the note is stabilising into normal repo docs.
Use `canonical_elsewhere` when checked-in docs already own the truth and this note is only residue, routing help, or a stub.
Keep the note short when it is `agent_only`: prefer lessons, pitfalls, and residue over full handbook prose.

## Scope

<files / subsystem / surface>

## Applies to

List concrete files, modules, tools, commands, or runtime surfaces that this note relates to.

Use concrete paths, modules, tools, commands, or runtime surfaces so agents can match touched files to relevant notes quickly.

This helps agents determine relevance from touched files during a task.

Examples:
- src/<subsystem>/*
- <interface entrypoint path>
- <runtime surface or command>

## Load when

- <When an agent should read this note>

## Review when

- <What changes should trigger re-checking this note>

## Failure signals

- <Signals indicating this note may apply>

## Rule or lesson

- <Core rule or durable lesson>
- Prefer durable orientation or boundary knowledge here; move procedure-heavy repeated steps into a skill or runbook as appropriate.
- If the note starts to read like a reusable maintenance script or refresh checklist, prefer a skill instead.
- If the content becomes stable human-facing policy or procedure, promote it into checked-in canonical docs and reduce this note to a short stub or fallback summary.

Examples

- Good compact memory: "Rollback usually fails when release verification races cache invalidation; verify service health before retrying."
- Likely canonical doc instead: "Full deployment procedure for production, staging, and rollback."

## How to recognise it

- <How to know this note is relevant>

## What to do

- <Action to take when the note applies>

## Verify

- <Files, tests, commands, or checks that confirm this note is still correct>

## Verified against

- Optional: list the exact files, interfaces, commands, or test suites this note was last checked against.

## Last confirmed

YYYY-MM-DD during <task / PR / investigation>
