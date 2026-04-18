# Startup Front Door Clarity And Compatibility

## Goal

- Close issues `#181`-`#187` by making the startup path cheaper and less ambiguous for ordinary repo work, external bootstrap/adopt handoff, and non-Codex first contact.

## Non-Goals

- Do not create another overlapping startup owner surface.
- Do not build a vendor-specific compatibility framework.
- Do not turn generated startup docs into canonical doctrine owners.

## Intent Continuity

- Larger intended outcome: keep first contact cheap by making the canonical startup route, compact query path, and generated helper surfaces visibly ordered and agent-agnostic.
- This slice completes the larger intended outcome: yes
- Continuation surface: none
- Parent lane: startup-front-door-clarity-and-compatibility

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: one coherent startup/front-door contract that distinguishes ordinary repo startup from external install/adopt handoff, foregrounds CLI-first active-state recovery, and keeps generated helpers clearly secondary.
- Intentionally deferred: none if the tranche closes cleanly.
- Discovered implications: startup clarity should lean on existing defaults/config/summary/report surfaces rather than adding new front-door files.
- Proof achieved now: focused workspace and planning tests, planning-surface checks, generated-surface rerender, and package/root refresh checks all passed.
- Validation still needed: none.
- Next likely slice: none; the tranche closes here.

## Delegated Judgment

- Requested outcome: make startup and first-contact behavior cheaper and less ambiguous without inventing new owners or vendor-specific workflows.
- Hard constraints: keep `AGENTS.md` as the ordinary repo startup owner, keep `llms.txt` bounded to external install/adopt handoff, keep generated docs helper-only, and keep the compact path machine-readable first.
- Agent may decide locally: the exact wording, the smallest compact query map to expose, and how to express the active-surface hygiene rule in the checker as long as it remains simple and merge-safe.
- Escalate when: the lane would require renaming public surfaces in a way that breaks current shipped contracts broadly, or when the compact query map cannot be made cheaper without adding another startup owner.

## Active Milestone

- Status: completed
- Scope: `AGENTS.md`, `README.md`, `llms.txt`, `docs/default-path-contract.md`, `.agentic-workspace/planning/agent-manifest.json`, generated startup docs, startup defaults payloads, and planning-surface hygiene checks/tests.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Tighten the startup/defaults contracts and planning checker together, then rerender the generated startup docs from the planning manifest.

## Blockers

- None.

## Touched Paths

- Root startup and front-door docs: `AGENTS.md`, `README.md`, `llms.txt`, `docs/default-path-contract.md`, `docs/contributor-playbook.md`
- Active planning surfaces: `TODO.md`, `ROADMAP.md`, `docs/execplans/`, `docs/reviews/`
- Planning startup source and generated helpers: `.agentic-workspace/planning/agent-manifest.json`, `.agentic-workspace/planning/scripts/check/check_planning_surfaces.py`, `.agentic-workspace/planning/scripts/render_agent_docs.py`, `tools/`
- Workspace defaults and tests: `src/agentic_workspace/cli.py`, `tests/test_workspace_cli.py`, `packages/planning/tests/`

## Invariants

- `AGENTS.md` remains the canonical startup entrypoint for ordinary repo work after bootstrap/adoption.
- `llms.txt` remains the bounded external install/adopt handoff surface rather than a general repo doctrine file.
- Generated startup docs stay generated and helper-only.
- The compact query path should get cheaper before adding new prose.

## Contract Decisions To Freeze

- `llms.txt` stays in place as the external install/adopt handoff surface instead of being renamed in this slice.
- `AGENTS.md` remains the ordinary repo startup owner; generated helper docs must point back to canonical startup and compact query surfaces rather than compete with them.
- `agentic-workspace defaults --section startup --format json` is the compact first-contact map for startup order, surface roles, and fallback rules.

## Open Questions To Close

- None; the lane is implementing the bounded clarity pass without introducing another startup owner or vendor-specific compatibility layer.

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py -q`
- `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-workspace defaults --section startup --format json`
- `uv run agentic-planning-bootstrap summary --format json`
- `make maintainer-surfaces`
- `uv run agentic-planning-bootstrap upgrade --target .`
- `uv run agentic-memory-bootstrap upgrade --target .`

## Required Tools

- `uv`
- `gh`

## Completion Criteria

- The startup-facing surfaces distinguish ordinary repo startup, external install/adopt handoff, compact query surfaces, and generated helper docs clearly enough that a fresh agent needs less prose reading than before.
- `defaults --section startup --format json` provides the compact first-query map and fallback rules needed for first contact.
- The planning checker enforces the active-surface hygiene rule for non-active artifacts in active locations.
- Generated startup docs are rerendered from the planning manifest and stay aligned with the canonical sources.
- Issues `#181`-`#187` are closed with the lane archived.

## Execution Summary

- Outcome delivered: startup/front-door surfaces now distinguish ordinary repo startup, external install/adopt handoff, compact query-first recovery, and generated helper docs without adding a new owner surface.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q`; `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`; `make maintainer-surfaces`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace defaults --section startup --format json`; `uv run agentic-planning-bootstrap summary --format json`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`
- Follow-on routed to: `ROADMAP.md`
- Resume from: `ROADMAP.md` first candidate lane `portable-declarative-contracts-beyond-python-cli`

## Drift Log

- 2026-04-18: Promoted the new issue tranche as one coherent startup/front-door clarity lane instead of treating the issues as separate startup, compatibility, and hygiene epics.
- 2026-04-18: Closed the tranche after tightening startup authority, shipping a compact startup query/surface-role map, and hardening active-surface hygiene in the planning checker.
