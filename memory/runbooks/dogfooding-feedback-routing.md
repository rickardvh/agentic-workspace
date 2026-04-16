# Dogfooding Feedback Routing

## Status

Stable

## Scope

Local dogfooding evaluation procedure for classifying internal-use friction before routing it onward.

## Applies to

- `docs/contributor-playbook.md`
- `docs/lazy-discovery-measurements.md`
- `memory/runbooks/dogfooding-usage-ledger.md`
- repo-local dogfooding notes captured during normal work

## Load when

- You are recording internal friction, ordinary-use pull, feature-choice reasons, or skip reasons during a repo task.

## Review when

- The capture categories change.
- The ordinary-use pull pattern changes.
- Repeated friction suggests low-pull surfaces should be merged, demoted, or retired.

## Failure signals

- The same friction keeps landing in chat instead of the repo.
- Usage entries omit choice or skip reasoning.
- Outsider-legibility or self-hosting bias is only discussed informally.

## When to use this

- A task is small enough that the useful signal is which surfaces were actually chosen.
- You want to classify a friction signal before it routes onward.
- You want to ask whether a fresh external agent would have reached the same first safe action.

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
- If the signal suggests a fresh external or cheaper agent would struggle, record that as an outsider-legibility or self-hosting-bias note in the same pass.
- If the signal changes active execution, route it into `TODO.md` or an execplan.
- If it is a future candidate, record it in `ROADMAP.md` with a promotion signal.
- If it is durable operating knowledge, capture it in memory or canonical docs.
- If it is the post-completion reflection for a finished execplan, record one compact `Product improvement signal` in that plan's `Execution Summary` and route any required follow-on separately.
- If the same class of human steering repeats across sessions, treat that as an improvement signal too. Capture the repeated correction class explicitly so the repo can improve defaults, contracts, proof, ownership, or handoff instead of asking the human to restate the same steering forever.
- If a normal repo task naturally proves a strong-planner / cheap-implementer handoff, record that as evidence that the mixed-agent loop is becoming routine rather than exceptional.
- If cleanup burden repeats, classify it as stewardship friction and route it into planning rather than letting it become invisible task residue.
- If it is monorepo-only friction, say that explicitly so it does not silently become product policy.

## Preferred Resolution Order

- Fix the shipped package or contract first when the problem is repeatable outside this monorepo.
- Add repo-local workaround guidance only when the issue is genuinely repo-specific or temporary.
- When the root cause is unclear, capture the signal with the most likely category instead of leaving it unclassified.

## Review Prompt

When recording friction, answer this sentence once:

`This is primarily a <category> because ...`

For daily-use usage entries, add one more sentence:

`I chose <surface> over <skipped surface> because ...`

For ordinary-use pull audits, ask two extra questions:

- Would a fresh external agent have reached the same first safe action without extra explanation?
- Was the friction caused by product shape or by local familiarity bias?

## Verification

- The capture convention routes friction into the ledger, planning, review, or memory instead of leaving it in chat.
- Ordinary-use pull and bias notes have a stable checked-in home.

## Last confirmed

2026-04-16 during the simplification pass for issues `#120`, `#115`, `#116`, and `#114`
