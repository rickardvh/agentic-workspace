# Review: Default Path And Combined Execution

Use this review to assess whether the repo's current front-door/default-path story, cheap-execution contract, and combined Memory/Planning interaction are now strong enough to reduce restart cost and interpretation burden in ordinary use.

## Goal

- Review how well the current repo state supports the cheapest safe default path for agents, and how well combined Memory + Planning installs reduce restart cost without blurring ownership.

## Scope

- Root README and default-path surfaces
- Capability-aware execution contract and contributor guidance
- Memory/Planning integration contract
- Current planning completion state in `TODO.md`

## Non-Goals

- Do not re-litigate the already-known absolute-path link regression in front-door docs.
- Do not activate work directly from this review alone.
- Do not re-review package-internal implementation details outside their checked-in contract surfaces.

## Review Mode

- Mode: `context-cost`
- Review question: Does the current repo state make the normal path cheap enough and make combined installs meaningfully better than either module alone?
- Default finding cap: 3
- Inputs inspected first: `README.md`, `docs/default-path-contract.md`, `docs/capability-aware-execution.md`, `docs/integration-contract.md`, `docs/contributor-playbook.md`, `TODO.md`

## Review Method

- Commands used: none; checked-in contract inspection only
- Evidence sources: root README, default-path contract, capability-aware execution contract, integration contract, contributor playbook, and current completed-work record in `TODO.md`

## Findings

### Finding: Cheap-execution support is now a real product capability, not only a philosophy

- Summary: The repo now has a credible checked-in contract for safe cheap execution. Default-path docs, capability-aware execution guidance, and task-to-skill discovery together make lower-cost execution a real supported mode rather than an informal aspiration.
- Evidence: `README.md` now presents one default lifecycle path through `agentic-workspace`; `docs/default-path-contract.md` gives one default answer for install, startup, skill discovery, validation, and combined use; `docs/capability-aware-execution.md` defines cheap direct execution, medium-reasoning direct work, stronger-planning-first, delegation-friendly, and stop-and-escalate categories while explicitly preferring quiet shaping over user interruption.
- Risk if unchanged: Low. This is a positive state change. The remaining risk is mostly that the repo could fail to keep the cheap path visibly lighter than secondary routes as more features land.
- Suggested action: Preserve this direction and treat any future increase in front-door or startup-path ambiguity as an efficiency regression.
- Confidence: high
- Source: mixed
- Promotion target: none
- Promotion trigger:
- Post-remediation note shape: not-applicable

### Finding: Validation guidance is still somewhat prose-heavy relative to the new machine-readable default-path ambition

- Summary: The repo now has a strong machine-readable/default-route direction, but validation choice still appears to depend more on contributor prose than on a clearly demonstrated structured recommendation surface. That keeps some interpretation burden in place for lower-capability agents.
- Evidence: `docs/default-path-contract.md` says the normal path should prefer machine-readable defaults for validation, but the practical proving lanes still primarily appear in `docs/contributor-playbook.md` as prose guidance keyed to route type and surface ownership. The current public docs do not yet show an equivalently concrete queryable validation-recommendation surface the way module and skill discovery now do.
- Risk if unchanged: Agents may still over-read maintainer prose or choose broader checks than necessary because the cheapest safe proving lane is documented but not yet surfaced as plainly or structurally as the newer registry-backed defaults.
- Suggested action: Treat this as a likely next efficiency refinement: either expose validation defaults more explicitly through machine-readable/default-route surfaces, or narrow the docs so the cheap proving lane is even harder to miss.
- Confidence: medium
- Source: static-analysis
- Promotion target: `ROADMAP.md`
- Promotion trigger: Promote when another audit still finds that lower-capability agents must infer the proving lane mainly from prose rather than from explicit default-path structure.
- Post-remediation note shape: delete

### Finding: Memory/Planning synergy is now clearly specified, but still needs repeated ordinary-use proof more than more contract writing

- Summary: The combined-install interaction model is now strong: Planning should borrow durable context from Memory, completed Planning work should promote durable residue into Memory or canonical docs, and repeated plan re-explanation is explicitly treated as a missing-synergy signal. The next maturity step is to demonstrate that loop repeatedly in ordinary work until it feels effortless.
- Evidence: `docs/integration-contract.md` now explicitly says combined installs should be stronger than simple compatibility, defines the borrow rule, the residue rule, the combined startup-and-resume model, and the missing-synergy signals. `TODO.md` records the `memory-planning-synergy` tranche as completed, describing planning borrowing durable context from memory and repeated plan re-explanation becoming a signal for cheaper future execution.
- Risk if unchanged: The repo could keep refining the interaction contract without generating enough lived evidence that combined installs really reduce restart cost more than either module alone. That would leave the synergy strategically correct but not yet operationally inevitable.
- Suggested action: Prefer future dogfooding and bounded reviews that inspect ordinary combined-mode work for short plans, clean residue promotion, and reduced restart reading, instead of writing much more abstract interaction policy first.
- Confidence: high
- Source: mixed
- Promotion target: `ROADMAP.md`
- Promotion trigger: Promote when another ordinary maintenance cycle still finds repeated plan re-explanation, stranded durable residue, or broad restart reading despite the current combined-install contract.
- Post-remediation note shape: delete

## Recommendation

- Promote: None immediately.
- Defer: The validation-defaults refinement and the need for repeated combined-mode proof.
- Dismiss: None.

## Validation / Inspection Commands

- `agentic-workspace defaults --format json`
- `agentic-workspace modules --format json`
- `agentic-workspace skills --target /path/to/repo --task "implement the current active milestone" --format json`

## Drift Log

- 2026-04-09: Review created after contract-integrity, cheap-execution, and memory/planning-synergy passes were consolidated, excluding the already-addressed absolute-path link regression.

## Status Footer

- Finding 1 (Cheap-execution support is now a real product capability): no promotion needed; documents current good state.
- Finding 2 (Validation guidance is still somewhat prose-heavy): deferred pending another cheap-execution or machine-readable-defaults pass.
- Finding 3 (Memory/Planning synergy now needs repeated ordinary-use proof): deferred pending more combined-install dogfooding evidence.

Review ready for deletion once Findings 2 and 3 are either promoted into active work or shown to be resolved through later dogfooding.
