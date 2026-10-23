---
name: memory-reporting
description: Report selected Memory advice, disposition and current limits without a compulsory full-state read.
---

# Report current Memory findings

Use for a question about Memory advice, its scope or its disposition. First read
the current `advisory_context` and any already-delivered selected Memory detail.
When these facts are sufficient and still current, report them directly.

If the question depends on missing or changed native facts, use the repository's
[configured AW invocation](../../../../skills/workspace-startup/references/ordinary.md)
with `start --target . --task "<actual Memory question>"`. Start with compact
output and follow only the exact owner/detail references needed for the answer.
Distinguish no matching advice from unavailable or unresolved selection.

For a requested Memory change, answer only the current owner's exact question
and invoke only its admitted action. A reporting request alone authorises no
cleanup, retirement, promotion or completion claim. Report the actual source,
evidence, validity limits and any remaining owner gap.

## Source-maintenance diagnostics

For repository source maintenance, `make verify-memory` checks declarations and
`make memory-freshness` checks freshness. Inspect the current Makefile targets
before relying on their scope. Retired `agentic-memory doctor/report` commands
are not entry points. A successful check is evidence for that check, not proof
of workspace health or task completion.
