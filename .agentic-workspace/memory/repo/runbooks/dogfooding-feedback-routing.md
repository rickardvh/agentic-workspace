# Dogfooding Feedback Routing

## Status

Stable

## Scope

Local dogfooding evaluation procedure for classifying internal-use friction before routing it onward.

## Applies to

- `docs/maintainer/contributor-playbook.md`
- `docs/maintainer/lazy-discovery-measurements.md`
- `.agentic-workspace/memory/repo/runbooks/dogfooding-usage-ledger.md`
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
- A dogfooding report stops at chat summary without creating/updating issues, routing improvement pressure through Memory, or explicitly dismissing each concrete signal. Treat this as a procedural defect in normal AW use, not as something the human should correct in chat.

## When to use this

- A task is small enough that the useful signal is which surfaces were actually chosen.
- You want to classify a friction signal before it routes onward.
- You want to ask whether a fresh external agent would have reached the same first safe action.
- Any routine AW dogfooding reflection asks what made AW feel less smooth, streamlined, or helpful, what could be better even when it worked, where AW could help more, and which unused features should have been used in retrospect.

## Routine dogfooding reflection contract

When asked for dogfooding feedback, report all of the following and route each concrete signal to an owner:

- Anything that made using AW feel less smooth, streamlined, or helpful.
- Anything that worked but seems like it could be done in a better way.
- Any gap where AW could have helped more than it did.
- Features, commands, skills, Memory notes, delegation paths, or issue/planning routes that were not used, plus whether they should have been used in retrospect.

Routing owners may be issue follow-up, Memory improvement pressure, planning, docs, tests/checks/contracts, direct implementation, or explicit dismissal. Do not stop at a chat-only report when the signal is concrete enough to preserve. If the user has to remind the agent to route dogfooding pressure through Memory, record that as evidence that AW's normal procedure is still incomplete.

## Categories

Classify each signal into exactly one primary bucket first:

- Package defect: shipped module behavior is wrong, missing, or too awkward inside Agentic Memory or Agentic Planning.
- Boundary issue: ownership between memory, planning, routing, checks, or workspace composition is unclear or drifting.
- Install-flow issue: install, adopt, upgrade, uninstall, or doctor behavior is confusing or unsafe.
- Docs or routing issue: maintainer guidance, startup path, generated docs, or command discovery drifted away from reality.
- Stewardship friction: the repository keeps needing extra cleanup at the end of tasks or the touched scope is too unclear to finish cleanly.
- Monorepo-only friction: the problem appears in this dogfooding repo but should not automatically change the external product contract.

## Capture Rules

- If the signal is about ordinary daily use, feature choice, or repeated surface pull, record it in `.agentic-workspace/memory/repo/runbooks/dogfooding-usage-ledger.md` first and then route any repeated pattern onward.
- If the signal suggests a fresh external or cheaper agent would struggle, record that as an outsider-legibility or self-hosting-bias note in the same pass.
- If the signal changes active execution, route it into `.agentic-workspace/planning/state.toml` and/or an active execplan.
- If it is a future candidate, record it in planning state candidate lanes with a promotion signal.
- If it is durable operating knowledge, capture it in memory or canonical docs.
- If it is the post-completion reflection for a finished execplan, record one compact `Product improvement signal` in that plan's `Execution Summary` and route any required follow-on separately.
- If the same class of human steering repeats across sessions, treat that as an improvement signal too. Capture the repeated correction class explicitly so the repo can improve defaults, contracts, proof, ownership, or handoff instead of asking the human to restate the same steering forever.
- Treat explicit dogfooding feedback requests as routine routing work, not one-off reporting. Before closing, create or update GitHub issues for actionable findings when issue ownership is appropriate, route durable improvement pressure through Memory when it should shape future behavior, and explicitly dismiss weak or duplicate signals. The desired future behavior is procedural: AW should naturally prompt, route, and preserve these signals without relying on a corrective chat instruction.
- Use Memory for repeated dogfooding pressure that should change future agent behavior, especially when the lesson is about when to route findings rather than the product fix itself. Use issues for actionable product, workflow, validation, or trust gaps.
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
- Dogfooding feedback reports name the created/updated issues, Memory owner, planning owner, or dismissal for each concrete signal.

## Last confirmed

2026-05-18 during dogfooding feedback routing after PR `#1045`
