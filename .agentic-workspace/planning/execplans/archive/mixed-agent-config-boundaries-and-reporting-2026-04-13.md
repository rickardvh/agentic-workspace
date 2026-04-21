# Mixed-Agent Config Boundaries And Reporting

## Goal

- Freeze the product contract for token-efficient mixed-agent operation so implementation can add bounded config and reporting support without turning Agentic Workspace into a runtime scheduler.
- Define how checked-in repo policy, optional local capability overrides, runtime inference, and checked-in handoff artifacts should relate so stronger and weaker agents can both benefit from the same repository surfaces.
- Keep cross-agent continuation cheap enough that switching between subscriptions, vendors, or future local models does not waste tokens on rediscovery that the repository could have carried forward.

## Non-Goals

- Implement the full mixed-agent config schema, parser, migration logic, or CLI output in this slice.
- Force model selection, subagent use, reasoning depth, or vendor-specific routing from checked-in repo surfaces.
- Normalize a hidden second control plane that can silently rewrite repo semantics, done criteria, ownership, or delegated-judgment boundaries.
- Expand the workspace layer into a general workflow engine or replace assistant-native delegation when the runtime already handles that well.

## Intent Continuity

- Larger intended outcome: let Agentic Workspace support strong-planner / cheap-implementer workflows and other mixed-agent modes through checked-in infrastructure that lowers restart cost, reduces total token spend over time, enables efficient agent switching across subscriptions and tools, and helps weaker agents perform above baseline without fighting capable runtimes.
- This slice completes the larger intended outcome: no
- Continuation surface: `TODO.md`

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `TODO.md`
- Activation trigger: the contract decisions in this plan are frozen and implementation begins on workspace config/reporting behavior and the smallest supporting docs/tests.

## Delegated Judgment

- Requested outcome: encode the mixed-agent product stance in checked-in planning and canonical docs so later implementation can proceed without rediscovering the boundary between repo leverage and runtime orchestration, and so token-efficiency plus cross-agent continuity stay explicit success criteria.
- Hard constraints: keep repo-owned semantics authoritative; prefer inference first, config second, prompting last; keep any future local override optional and untracked; do not overclaim unimplemented behavior in canonical docs.
- Agent may decide locally: exact wording, whether to place details in design principles versus config docs, and the smallest roadmap pruning needed to reflect promotion into active planning.
- Escalate when: the slice would require shipping a concrete schema or CLI behavior without first freezing the boundary, or when the proposed contract would let local/runtime preferences silently override checked-in repo semantics.

## Active Milestone

- ID: mixed-agent-config-boundaries-and-reporting
- Status: completed
- Scope: freeze the mixed-agent contract boundary, ship reporting-only mixed-agent output in the workspace CLI, and align the canonical docs with the shipped surface.
- Ready: ready
- Blocked: none
- optional_deps: GitHub issue `#27`

## Immediate Next Action

- None. Slice completed; promote the next narrow mixed-agent implementation plan only when ready to change behavior beyond reporting.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `.agentic-workspace/planning/execplans/mixed-agent-config-boundaries-and-reporting-2026-04-13.md`
- `docs/design-principles.md`
- `docs/workspace-config-contract.md`

## Invariants

- Checked-in files own continuity and handoff state.
- Repo config owns stable repo policy only.
- Local overrides must stay optional, untracked, and reported.
- Runtime orchestration remains tool-owned.
- Mixed-agent support should reduce ambiguity for weaker agents.
- Success means lower token burn and restart waste over time.
- Persisted shared knowledge should beat rediscovery across agents and team members.

## Contract Decisions To Freeze

- Product boundary: Agentic Workspace should optimize checked-in infrastructure for mixed-agent work, not own runtime model scheduling or subagent strategy.
- Decision logic order: prefer runtime/task inference first, then repo/local config for stable preferences or capability asymmetry, and only then explicit user prompting when the boundary is still unsafe.
- Authority split: checked-in repo config owns stable repo policy and must remain reviewable; any future local override owns machine/account/cost-profile preferences only and must not silently change ownership, done criteria, or delegated-judgment limits.
- Reporting requirement: do not expand mixed-agent config without an effective reporting surface that shows what came from repo policy, local override, product defaults, and runtime inference.
- Reporting requirement applies when inference materially changes behavior; such inference must be auditable rather than hidden.
- Handoff rule: internal delegation should be preferred when available and confidence is high, but checked-in handoff/state artifacts remain the fallback and continuity mechanism when uncertainty, restart cost, or cross-boundary work makes implicit delegation too brittle.
- Handoff quality bar: switching is successful only when the next contributor can recover intent, hard constraints, relevant durable context, proof expectations, and immediate next action without broad rereading.
- Capability language: mixed-agent surfaces should describe capability and cost posture rather than vendor- or model-specific routing rules.
- Product motivation: mixed-agent infrastructure should be judged first by whether it lowers long-run token cost and smooths agent switching across subscriptions, vendors, and future local models without loss of quality.
- Cost discipline: mixed-agent features fail when they save model tokens mainly by shifting burden onto human prompting, triage, or cleanup.

## Open Questions To Close

- Which parts of mixed-agent mode should be inferred from task shape/runtime state versus stored in checked-in or local config?
- What is the smallest effective-reporting surface that makes local override and runtime inference debuggable without adding noise to the default path?
- Which, if any, mixed-agent preferences belong in repo-owned config v2 rather than remaining purely inferred or local-only?
- What lightweight evidence should the product capture to show that a mixed-agent feature reduced restart, handoff, or token cost in real repeated work?

## Validation Commands

- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- Active planning clearly owns this mixed-agent contract slice in `TODO.md` plus an execplan.
- Canonical docs state that the product should empower smaller agents through checked-in structure while remaining advisory toward assistant-native delegation/runtime orchestration.
- The workspace config contract now records the boundary between repo-owned policy, potential future local overrides, and effective reporting requirements.
- The active plan now preserves token-efficiency and cross-agent continuity as explicit motivation for later implementation and validation.
- Canonical docs now define successful switching and handoff quality in operational terms rather than only as a general goal.
- `ROADMAP.md` no longer treats the promoted mixed-agent config/reporting work as inactive backlog.

## Execution Summary

- Outcome delivered: active planning captured the mixed-agent product boundary, `agentic-workspace defaults` and `agentic-workspace config` now expose a reporting-only mixed-agent contract, and the README/default-path/config docs now match that shipped surface.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q`; `uv run python scripts/check/check_planning_surfaces.py`.
- Follow-on routed to: `ROADMAP.md`.
- Resume from: promote a new execplan for the smallest behavior-changing mixed-agent slice, most likely careful config expansion or conservative policy-selection follow-through.

## Drift Log

- 2026-04-13: Promoted from GitHub issue `#27` and the roadmap mixed-agent operating-mode tranche after explicit maintainer direction to encode the product stance before implementation.
- 2026-04-13: Completed by shipping reporting-only mixed-agent JSON/text output in the workspace CLI, adding focused regression coverage, and aligning the front-door docs with the new contract.
