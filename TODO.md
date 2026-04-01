# TODO

## Goal

Apply the Copilot memory lessons to the reusable package without expanding the default memory surface.

Improve by tightening ownership, deletion pressure, routing precision, freshness guidance, and memory-versus-planning boundaries.

## Issue: Bias the package toward deletion and consolidation

Problem:
Memory becomes harmful quickly when ownership is unclear and old fragments accumulate.

Acceptance criteria:
- shared docs explicitly say to optimise for deletion and consolidation, not just capture
- docs reinforce one durable fact, one primary home
- docs discourage near-duplicate summary fragments across overview notes, decisions, and runbooks

## Issue: Emphasise hard-to-rediscover truth over recent state

Problem:
Recent state is often cheap to reconstruct. The durable value is usually in invariants, constraints, exceptions, and recurring traps.

Acceptance criteria:
- shared docs distinguish durable truth from merely recent state
- capture examples favour invariants, constraints, exceptions, authority boundaries, and recurring traps
- current-state and planning residue remain out of durable memory

## Issue: Make routing quality more important than memory volume

Problem:
A small memory store with strong retrieval boundaries beats a large one with weak selection.

Acceptance criteria:
- docs state that routing should help an agent read less, not more
- routing guidance prefers the smallest relevant note bundle
- route/sync wording reinforces minimal durable note selection

## Issue: Tighten current-context warnings further

Problem:
Current-context notes are the easiest place for memory to turn into a shadow task tracker or mini-changelog.

Acceptance criteria:
- docs keep current-context explicitly temporary and subordinate to the planning surface
- docs state that current-context is for interruption recovery only
- starter text and checks discourage task-tracker or historical-log sprawl

## Issue: Preserve decisions at the level of consequence, not meeting history

Problem:
Decision memory is valuable when it records durable consequences or rejected-path boundaries, not discussion history.

Acceptance criteria:
- docs tell repos to store decision consequences and still-relevant rejected-path boundaries
- docs discourage meeting-history style rationale unless it still constrains future choices
- current decisions guidance stays focused on live consequence-bearing decisions

## Issue: Tie freshness to semantic drift more explicitly

Problem:
Age alone is weak. Notes can be recent and still wrong if code, contracts, or deployment surfaces changed underneath them.

Acceptance criteria:
- docs and light tooling messaging emphasise code, command, interface, and authority-boundary drift
- current-state staleness wording continues to point at real invalidation surfaces, not only timestamps
- no new schema is required

## Issue: Keep user-specific memory separate from repo truth

Problem:
Personal preferences and collaboration habits are a different class of memory from technical repo truth.

Acceptance criteria:
- shared docs explicitly separate user-specific memory from repo-specific durable knowledge
- local/scratch guidance makes clear that personal defaults do not belong in repo memory
- package docs avoid mixing collaboration style with technical truth

## Issue: Make memory a reasoning aid, not a replacement for code inspection

Problem:
Stored guidance should narrow the search space, not replace checking the codebase when the codebase is the real source of truth.

Acceptance criteria:
- docs state that memory is a constraint/hint layer
- docs say memory should not replace reading the code, tests, or canonical docs
- routing and admission guidance stay compatible with this principle

## Regression / Guardrails

- add tests for deletion/consolidation language
- add tests for routing-helping-read-less language
- add tests for user-specific versus repo-specific separation
- add tests for consequence-level decision guidance
