# Config-Aware Operating-Loop Handshakes First Slice

Compact inactive-plan residue generated at archive time.
Use git history for superseded active-step detail; keep only the closure, continuation, proof, and cheap-resume residue here.

## Origin

- Archived from: `.agentic-workspace/planning/execplans/config-aware-operating-loop-handshakes-first-slice-2026-04-22.md`

## Intent Continuity

- Larger Intended Outcome: make Planning and Memory treat materially relevant config as part of the normal operating loop so bounded work and signal handling pull config before acting, then check compliance and treatment honestly after finishing.
- This Slice Completes The Larger Intended Outcome: no
- Continuation Surface: `ROADMAP.md` candidate lane `config-aware-operating-loop-handshakes`
- Parent Lane: `config-aware-operating-loop-handshakes`

## Required Continuation

- Required Follow-On For The Larger Intended Outcome: yes
- Owner Surface: `ROADMAP.md` candidate lane `config-aware-operating-loop-handshakes`
- Activation Trigger: activate the next bounded slice when real ordinary use shows whether the new config handshake fields actually catch bypass, missing config-derived bounds, or ambiguous memory signal treatment.

## Delegated Judgment

- Requested Outcome: land one compact first slice that makes config retrieval and config-compliance questions explicit in the planning loop while giving memory signals one compact home for config-shaped treatment.
- Hard Constraints: keep the slice compact; avoid turning config into a scheduler or policy engine; preserve the existing planning and memory boundaries; keep memory changes focused on signal-treatment metadata rather than a broader routing redesign.
- Agent May Decide Locally: exact field names, the minimum surfaces that must carry them, and the narrowest tests and docs needed to prove the slice.
- Escalate When: the change would require new runtime config resolution logic, broader planning schema redesign, or forcing heavy metadata onto ordinary memory notes.

## Intent Interpretation

- Literal Request: implement the next lane and commit it
- Inferred Intended Outcome: keep progressing the newly promoted roadmap lane through one honest bounded slice that materially reduces missed config retrieval and missed config-treatment handling without widening into a full policy system.
- Chosen Concrete What: add explicit pre-work config pull and finished-run config compliance fields to planning's compact contract chain, add compact config-treatment metadata to memory improvement-signal surfaces, then archive the slice and keep the lane open for ordinary-use proof.
- Interpretation Distance: low
- Review Guidance: reject the slice if it behaves like config-engine expansion, if memory changes widen into broader routing redesign, or if the new prompts are not visible in the ordinary planning/memory surfaces agents actually touch.

## Execution Bounds

- Allowed Paths: `.agentic-workspace/planning/`, `.agentic-workspace/docs/`, `packages/planning/`, `packages/memory/`, `scripts/check/check_planning_surfaces.py`, `AGENTS.md`, `README.md`, `SYSTEM_INTENT.md`
- Max Changed Files: 30
- Required Validation Commands: `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`; `uv run pytest packages/memory/tests/test_installer.py -q`; `uv run pytest packages/memory/tests/test_packaging.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace summary --format json`
- Ask-Before-Refactor Threshold: stop before broader planning-summary redesign, runtime config execution changes, or memory-routing architecture work beyond compact signal-treatment metadata
- Stop Before Touching: unrelated graceful-compliance, machine-first planning, portability, or recurring-friction dogfooding work

## Stop Conditions

- Stop When: making the handshake visible would require a broader config engine, a second durable planning state store, or a broad memory-routing redesign.
- Escalate When Boundary Reached: the compact fields are not enough to carry config-derived bounds or config-shaped memory treatment into ordinary work.
- Escalate On Scope Drift: more than the nearest planning and memory contract surfaces, their tests, and the repo's planning residue would need reshaping.
- Escalate On Proof Failure: the slice cannot show the new questions in ordinary planning and memory surfaces without adding more ritual than value.

## Context Budget

- Live Working Set: issues `#267` and `#268`, the planning summary/handoff/report chain, the execplan template and checker rules, and the memory improvement-signal metadata contract.
- Recoverable Later: broader graceful-compliance follow-on, recurring-friction dogfooding, and any future lower-trust closeout surfacing for config bypass.
- Externalize Before Shift: the chosen planning handshake fields, the memory signal-treatment metadata, and the reason the slice stopped before stronger enforcement or lower-trust review.
- Tiny Resumability Note: planning now asks the config question explicitly before and after work; memory signals now have a compact config-treatment home, but the lane still needs ordinary-use proof.
- Context-Shift Triggers: shift once the package/root validations finish or if real dogfooding shows the new fields are still too weak.

## Execution Run

- Run Status: completed
- Executor: Codex
- Handoff Source: roadmap lane plus live issue bodies for `#267` and `#268`
- What Happened: added `Pre-work config pull` and `Config compliance` to planning's template, summary schema, handoff contract, CLI output, and checker/test surfaces; added `config_treatment` and `config_note` to memory improvement-signal metadata plus the recurring-friction runbook and manifest guidance; refreshed the system-intent contract wording so installed planning still treats `SYSTEM_INTENT.md` as a compass.
- Scope Touched: planning package source/payload/tests, memory package source/payload/tests, the repo planning checker/install mirror, and roadmap/archive residue for the lane.
- Changed Surfaces: planning contract fields and CLI views now expose config pull/compliance explicitly; memory improvement-signal metadata now exposes config-shaped treatment explicitly.
- Validations Run: `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`; `uv run pytest packages/memory/tests/test_installer.py -q`; `uv run pytest packages/memory/tests/test_packaging.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`; `uv run agentic-workspace summary --format json`
- Result For Continuation: the operating loop now has one compact planning-side config handshake and one compact memory-side signal-treatment handshake, so the next slice can judge real effectiveness instead of debating where the fields should live.
- Next Step: archive this slice, keep the lane open, and dogfood the new fields on a real bounded task before deciding whether stronger lower-trust review or config-gap surfacing is needed.

## Finished-Run Review

- Review Status: completed
- Scope Respected: yes
- Proof Status: satisfied
- Intent Served: yes
- Config Compliance: respected the existing config boundary by making config an explicit compact question instead of building a scheduler or broad policy engine
- Misinterpretation Risk: low
- Follow-On Decision: archive-but-keep-lane-open

## Proof Report

- Validation proof: planning installer and checker tests passed, memory installer and packaging tests passed, the repo planning-surface checker stayed clean, and the installed root surfaces refreshed to the current package payload.
- Proof achieved now: ordinary planning surfaces now ask which config materially constrains the run before execution and whether config was respected after finishing, while memory improvement-signal surfaces now have a compact config-shaped treatment home.
- Evidence for "Proof achieved" state: the new planning fields are required in template/checker/test coverage and visible in summary/handoff/CLI output; the new memory fields are documented, parsed, validated, and surfaced in improvement metadata.

## Intent Satisfaction

- Original intent: make Planning and Memory ask materially relevant config questions at the moments that shape execution, signal treatment, cleanup, and closeout so config behaves like part of the operating loop instead of ambient advice
- Was original intent fully satisfied?: no
- Evidence of intent satisfaction: the first compact handshake fields are now shipped end to end through planning and memory contracts, but the lane still lacks real ordinary-use proof about whether those prompts are enough to catch config bypass and ambiguous memory treatment.
- Unsolved intent passed to: `.agentic-workspace/planning/state.toml`

## Closure Check

- Slice status: bounded slice complete
- Larger-intent status: open
- Closure decision: archive-but-keep-lane-open
- Why this decision is honest: the first slice fully landed its compact handshake contract, but the larger lane remains open until ordinary use proves whether the new prompts are sufficient or whether lower-trust config-bypass surfacing must tighten.
- Evidence carried forward: the shipped planning fields, the shipped memory metadata, this archived execplan, and the roadmap lane in `.agentic-workspace/planning/state.toml`
- Reopen trigger: reopen only if the new fields fail to show up cheaply in ordinary planning/memory work or if config bypass still goes unnoticed despite the new contract.

## Execution Summary

- Outcome delivered: shipped explicit planning-side config pull and config-compliance fields through template, summary, handoff, CLI, and checker/test surfaces, and shipped explicit memory-side config-treatment metadata through improvement-signal docs, parsing, validation, and recurring-friction guidance.
- Validation confirmed: `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`; `uv run pytest packages/memory/tests/test_installer.py -q`; `uv run pytest packages/memory/tests/test_packaging.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`; `uv run agentic-workspace summary --format json`
- Follow-on routed to: `.agentic-workspace/planning/state.toml`, with `config-aware-operating-loop-handshakes` still active as the first roadmap lane.
- Post-work posterity capture: preserve the rule that config should now be asked explicitly at run start and run close, and that memory improvement signals should record config-shaped treatment when it materially affects promotion, cleanup, retention, or no-action.
- Knowledge promoted (Memory/Docs/Config): planning and memory package contracts now encode the compact handshake directly; the system-intent contract also now preserves the repo's compass wording in the shipped planning payload.
- Resume from: dogfood the new fields on a real bounded task and tighten lower-trust review or reporting only if config bypass still slips through.
