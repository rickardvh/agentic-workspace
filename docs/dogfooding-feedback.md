# Dogfooding Feedback Capture

Use this convention when internal use reveals friction.

## Goal

Turn friction into a classified improvement signal instead of leaving it in chat residue.

## Categories

Classify each signal into exactly one primary bucket first:

- Package defect: shipped module behavior is wrong, missing, or too awkward inside Agentic Memory or Agentic Planning.
- Boundary issue: ownership between memory, planning, routing, checks, or workspace composition is unclear or drifting.
- Install-flow issue: install, adopt, upgrade, uninstall, or doctor behavior is confusing or unsafe.
- Docs or routing issue: maintainer guidance, startup path, generated docs, or command discovery drifted away from reality.
- Monorepo-only friction: the problem appears in this dogfooding repo but should not automatically change the external product contract.

## Capture Rules

- If the signal changes active execution, route it into `TODO.md` or an execplan.
- If it is a future candidate, record it in `ROADMAP.md` with a promotion signal.
- If it is durable operating knowledge, capture it in memory or canonical docs.
- If it is monorepo-only friction, say that explicitly so it does not silently become product policy.

## Preferred Resolution Order

- Fix the shipped package or contract first when the problem is repeatable outside this monorepo.
- Add repo-local workaround guidance only when the issue is genuinely repo-specific or temporary.
- When the root cause is unclear, capture the signal with the most likely category instead of leaving it unclassified.

## Good Capture Examples

- A generated routing doc drifts after manifest edits: docs or routing issue.
- A package upgrade leaves stale managed wrappers behind: install-flow issue.
- The workspace layer starts growing package-specific flags: boundary issue.
- Memory capture keeps papering over the same missing package behavior: package defect.

## Review Prompt

When recording friction, answer this sentence once:

`This is primarily a <category> because ...`
