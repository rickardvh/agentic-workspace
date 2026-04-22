# Pre-Work Memory Pull

Compact inactive-plan residue generated at archive time.
Use git history for superseded active-step detail; keep only the closure, continuation, proof, and cheap-resume residue here.

## Origin

- Archived from: .agentic-workspace/planning/execplans/pre-work-memory-pull-2026-04-22.md

## Intent Continuity

- Larger Intended Outcome: make planning and Memory cooperate tightly at the workflow level so work pulls relevant durable understanding before execution and preserves later-useful residue after finishing, while keeping both modules independently usable.
- This Slice Completes The Larger Intended Outcome: no
- Continuation Surface: .agentic-workspace/planning/state.toml
- Parent Lane: `planning-memory-operating-loop`

## Required Continuation

- Required Follow-On For The Larger Intended Outcome: yes
- Owner Surface: .agentic-workspace/planning/state.toml
- Activation Trigger: activate the next bounded slice when pre-work retrieval is shipped and the remaining post-work posterity or recurring-friction follow-through still needs an explicit owner.

## Delegated Judgment

- Requested Outcome: land the smallest useful pre-work memory-pull prompt in the planning chain and prove it is cheap enough for routine use
- Hard Constraints: keep the change compact, planning-owned, and explicitly about pre-work durable understanding rather than broad ritual
- Agent May Decide Locally: the exact field or prompt wording, the narrowest host surface, and the smallest proof that ordinary work will actually see it
- Escalate When: the change would require a larger planning-memory architecture pass or a second durable planning store

## Intent Interpretation

- Literal Request: finish any open work and close existing gaps, then activate the top candidate lane
- Inferred Intended Outcome: leave the queue with no stale completed residue and one honest active owner for the next most important bounded planning slice
- Chosen Concrete What: clean stale `#259`/`#206` residue, then promote `#265` as the first bounded slice under the new planning-memory lane
- Interpretation Distance: low
- Review Guidance: reject the slice if it widens into the full handshake lane or tries to solve posterity capture in the same pass without explicit proof that the first slice stays bounded

## Execution Bounds

- Allowed Paths: `.agentic-workspace/planning/`, `.agentic-workspace/docs/`, `packages/planning/`, `tests/`
- Max Changed Files: 20
- Required Validation Commands: `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace summary --format json`; `uv run agentic-workspace report --target . --format json`
- Ask-Before-Refactor Threshold: stop before broad planning-summary or memory-routing redesign beyond what the pre-work prompt directly needs
- Stop Before Touching: unrelated graceful-compliance, portability, machine-first planning, or post-work posterity-capture implementation

## Stop Conditions

- Stop When: the smallest honest insertion point for the prompt would still require simultaneous redesign of startup, summary, and memory routing contracts
- Escalate When Boundary Reached: the pre-work prompt cannot be made useful without bundling it with post-work posterity capture or broader planning-memory loop changes
- Escalate On Scope Drift: more than the planning-owned prompt surface, its nearest docs/tests, and the narrowest reporting proof would need reshaping
- Escalate On Proof Failure: the slice cannot show that the prompt is visible in ordinary planning use without adding more ceremony than value

## Context Budget

- Live Working Set: issue `#265`, the active planning template/surfaces ordinary work touches first, and the compact planning/report validation path
- Recoverable Later: broader handshake-lane rationale from `#264`, recurring-friction evidence shaping from `#263`, and startup drift work from `#262`
- Externalize Before Shift: the chosen insertion point, the exact prompt shape, and why it is compact enough for ordinary use
- Tiny Resumability Note: keep this slice about pre-work retrieval only; do not silently absorb posterity capture
- Context-Shift Triggers: shift once the insertion point is chosen or if the narrow prompt requires broader startup-chain redesign

## Execution Run

- Run Status: completed
- Executor: Codex
- Handoff Source: active execplan plus checked-in planning summary
- What Happened: added `Pre-work memory pull` to the execplan template and context-budget contract, threaded it through planning summary/report/handoff and CLI text views, updated docs/tests/checker enforcement, and set the active slice's prompt to the planning-memory retrieval question it needs.
- Scope Touched: `.agentic-workspace/planning/execplans/`, `.agentic-workspace/docs/`, `packages/planning/`, `tests/`
- Validations Run: `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`; `uv run pytest tests/test_workspace_cli.py -q`; `uv run python scripts/check/check_planning_surfaces.py`
- Result For Continuation: the active planning chain now asks the pre-work durable-context question explicitly; later slices can build on that same loop instead of inventing a new startup ritual.
- Next Step: archive the slice and route the broader lane back to the candidate queue for `#266` or `#262`.

## Finished-Run Review

- Review Status: approved
- Scope Respected: yes
- Proof Status: satisfied
- Intent Served: yes
- Misinterpretation Risk: low
- Follow-On Decision: archive-but-keep-lane-open

## Proof Report

- Validation proof: `packages/planning` installer and checker tests pass, workspace CLI tests pass, and the repo planning-surface checker stays clean after the new field becomes required.
- Proof achieved now: ordinary planning surfaces now carry the explicit pre-work retrieval prompt end to end through template, checker, summary/report/handoff JSON, and CLI text output.
- Evidence for "proof achieved" state: `79` planning installer tests passed, `28` planning-surface checker tests passed, `114` workspace CLI tests passed, and `uv run python scripts/check/check_planning_surfaces.py` reported no drift warnings.

## Intent Satisfaction

- Original intent: make planning and Memory behave like one operating loop that pulls relevant durable understanding before work and preserves later-useful residue after work
- Was original intent fully satisfied?: no
- Evidence of intent satisfaction: this slice fully implemented and proved the bounded `#265` pre-work half of that larger operating-loop intent by adding the explicit `Pre-work memory pull` field and surfacing it through ordinary summary/report/handoff paths, but it did not complete the broader loop.
- Unsolved intent passed to: .agentic-workspace/planning/state.toml, where the `planning-memory-operating-loop` candidate lane now carries later slices such as `#266` and `#262`

## Closure Check

- Slice status: completed
- Larger-intent status: open
- Closure decision: archive-but-keep-lane-open
- Why this decision is honest: the bounded `#265` slice is fully implemented and proved, while the larger planning-memory operating-loop intent remains open because post-work posterity capture (`#266`) and possible startup/resume drift follow-through (`#262`) still need their own bounded owners.
- Evidence carried forward: the shipped contract/docs/tests for `Pre-work memory pull`, this archived execplan, and the `planning-memory-operating-loop` candidate lane in .agentic-workspace/planning/state.toml
- Reopen trigger: reopen only if the new field is not actually enough to make ordinary work ask the pre-work durable-context question cheaply.

## Execution Summary

- Outcome delivered: the planning chain now has an explicit `Pre-work memory pull` field in `Context Budget`, and the summary/report/handoff views expose it as the compact pre-work retrieval prompt for bounded execution.
- Validation confirmed: `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`; `uv run pytest tests/test_workspace_cli.py -q`; `uv run python scripts/check/check_planning_surfaces.py`
- Follow-on routed to: .agentic-workspace/planning/state.toml, with `planning-memory-operating-loop` still active as the candidate lane and `#266` as the next suggested bounded slice.
- Knowledge promoted (memory/docs/config): planning docs and contract surfaces now encode the pre-work retrieval question directly; no separate memory note was needed for this slice.
- Resume from: promote the next bounded planning-memory slice when you want to add post-work posterity capture or startup/resume follow-through.
