# Agent Judgment Over Keyword Matching

## Status

Active

## Canonicality

candidate_for_promotion

## Scope

Agentic Workspace routing, Memory consultation, Verification classification, delegation, closeout, and other agent-facing decision support.

## Applies to

- `.agentic-workspace/WORKFLOW.md`
- `.agentic-workspace/memory/skills/`
- `.agentic-workspace/memory/repo/skills/`
- `src/agentic_workspace/contracts/skill_specs.json`
- `src/agentic_workspace/workspace_runtime_primitives.py`
- `packages/verification/src/repo_verification_bootstrap/runtime_primitives.py`

## Load when

- A feature would route agent behavior from prompt keyword or phrase matches.
- A workflow surface needs to tell agents when to consult Memory, delegate, verify, capture residue, or choose proof.
- Repeated user correction says AW is making the right action hard to notice or too dependent on chat memory.

## Review when

- Startup, implement, closeout, Memory, Verification, or delegation routing changes.
- A new classifier, heuristic, or report starts treating natural-language markers as decision authority.
- A skill or compact report is promoted into core guidance.

## Failure signals

- A string match outside declared enums or structured fields determines policy, proof ownership, completion, or disposition.
- A report tells the agent what to decide instead of surfacing facts, risks, commands, and tradeoffs.
- A repeated user preference remains only in chat and is not captured, routed, or promoted.

## Rule or lesson

- Do not encode AW decisions as keyword matching over prompt text, filenames, or prose snippets.
- Prefer skills and structured signals that tell the agent when a question should be considered, what information to inspect, and what owner surfaces exist.
- Leave reasoning and decision-making to the agent unless a hard gate is explicitly owned by AW.
- When user guidance repeats often enough to shape future behavior, capture it in Memory and promote stable rules into core repo guidance.
- For #1579, the useful product shape is a command-backed `memory_decision_packet`, not smarter phrase matching: surface the pull/capture decision in startup, implement, and closeout/report views, then let the agent decide whether Memory was consulted, found relevant notes, found none, should capture, should route elsewhere, or should dismiss.

## How to recognise it

- The proposed implementation depends on a phrase such as "dogfood", "memory", "review", or "again" as if the phrase itself were authority.
- The better implementation can expose a skill, checklist field, selected-output section, command, enum, or owner boundary while preserving agent judgment.

## What to do

- Replace phrase authority with explicit structured signals, skills, or report fields.
- Show the cheap next command or note set when a workflow should be considered.
- Require an explicit agent-owned decision in closeout when Memory consultation, durable capture, delegation, or verification strategy may matter.
- Promote the stable rule into core guidance when repeated corrections show it should not remain Memory-only.
- Treat `none_found`, `dismissed`, and `routed_elsewhere` as valid outcomes alongside Memory capture; do not create notes just to satisfy closeout.

## Verify

- A future agent can find this note through Memory route or core workflow guidance without knowing the exact chat wording.
- The corresponding product change does not add new keyword authority outside existing enums or structured fields.
- `agentic-workspace memory route --stage closeout --files src/agentic_workspace/workspace_runtime_primitives.py tests/test_workspace_summary_cli.py --task "<paraphrased task>" --format json` finds this note through structured surface/file context and reports `task_used_for_matching: false`.
- `agentic-workspace memory capture-note --stage closeout --task "<paraphrased task>" --files <changed surfaces> --format json` routes new #1579 closeout-state learning to this existing note rather than creating an extra task-local Memory note.

## Verified against

- `.agentic-workspace/WORKFLOW.md`
- `.agentic-workspace/memory/repo/current/routing-feedback.md`
- GitHub issue #1579
- PR #1580 dogfooding closeout evidence

## Last confirmed

2026-06-17 during #1579 pull/capture loop dogfooding.
