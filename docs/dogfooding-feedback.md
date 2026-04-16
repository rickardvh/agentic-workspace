# Dogfooding Feedback Capture

Use this convention when internal use reveals friction.

Use planning surfaces when the signal changes active execution; this page is only for classifying and routing the signal, not for keeping a backlog.

## Goal

Turn friction into a classified improvement signal instead of leaving it in chat residue.

## Categories

Classify each signal into exactly one primary bucket first:

- Package defect: shipped module behavior is wrong, missing, or too awkward inside Agentic Memory or Agentic Planning.
- Boundary issue: ownership between memory, planning, routing, checks, or workspace composition is unclear or drifting.
- Install-flow issue: install, adopt, upgrade, uninstall, or doctor behavior is confusing or unsafe.
- Docs or routing issue: maintainer guidance, startup path, generated docs, or command discovery drifted away from reality.
- Stewardship friction: the repository keeps needing extra cleanup at the end of tasks or the touched scope is too unclear to finish cleanly.
- Monorepo-only friction: the problem appears in this dogfooding repo but should not automatically change the external product contract.

## Capture Rules

- If the signal is about ordinary daily use, feature choice, or repeated surface pull, record it in `memory/runbooks/dogfooding-usage-ledger.md` first and then route any repeated pattern onward.
- If the signal changes active execution, route it into `TODO.md` or an execplan.
- If it is a future candidate, record it in `ROADMAP.md` with a promotion signal.
- If it is durable operating knowledge, capture it in memory or canonical docs.
- If the signal is the post-completion reflection for a finished execplan, record one compact `Product improvement signal` in that plan's `Execution Summary` and route any required follow-on separately.
- If the same class of human steering repeats across sessions, treat that as an improvement signal too. Capture the repeated correction class explicitly so the repo can improve defaults, contracts, proof, ownership, or handoff instead of asking the human to restate the same steering forever.
- If a normal repo task naturally proves a strong-planner / cheap-implementer handoff, record that as evidence that the mixed-agent loop is becoming routine rather than exceptional.
- If cleanup burden repeats, classify it as stewardship friction and route it into planning rather than letting it become invisible task residue.
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

For daily-use usage entries, add one more sentence:

`I chose <surface> over <skipped surface> because ...`
