# Mixed-Agent Local Override Contract

## Goal

- Implement a narrow optional local mixed-agent override so machine-, account-, and cost-profile-specific capability posture can be expressed without entering checked-in repo policy.
- Expose the effective mixed-agent report with clear source attribution for repo policy, local override, product defaults, and runtime-owned behavior.

## Non-Goals

- Let local override silently change repo semantics, ownership, validation defaults, or delegated-judgment boundaries.
- Use local override to schedule runtime model choice, force subagent use, or replace tool-owned orchestration.
- Add a broad preference matrix or a second workflow engine.
- Change workspace lifecycle behavior beyond effective reporting in this slice.

## Intent Continuity

- Larger intended outcome: make cross-agent switching and token-efficient execution cheaper by separating reviewable repo policy from local capability/cost posture while keeping checked-in continuity authoritative.
- This slice completes the larger intended outcome: no
- Continuation surface: `TODO.md`

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `TODO.md`
- Activation trigger: the local override contract lands and the next slice is ready to use it for carefully bounded behavior or additional reporting.

## Delegated Judgment

- Requested outcome: ship the smallest useful local mixed-agent override contract with auditable reporting and no scheduler behavior.
- Hard constraints: keep the file optional and gitignored; keep supported fields narrow; make source attribution explicit; do not let local override outrank checked-in repo semantics.
- Agent may decide locally: exact field names, whether reporting lives only in `config` or also in `defaults`, and the narrowest docs/tests needed to prove the slice.
- Escalate when: the slice needs broader behavior changes, vendor-specific routing, or fields that start acting like a hidden user-preference layer.

## Active Milestone

- ID: mixed-agent-local-override-contract
- Status: completed
- Scope: add a narrow local override file contract, parse it conservatively, expose its effective mixed-agent report through the workspace CLI, and align the canonical docs plus gitignore support.
- Ready: ready
- Blocked: none
- optional_deps: GitHub issue `#27`

## Immediate Next Action

- None. Slice completed; promote the next mixed-agent or validation-defaults plan only when the next behavior-changing scope is clear.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `.gitignore`
- `.agentic-workspace/planning/execplans/mixed-agent-local-override-contract-2026-04-13.md`
- `README.md`
- `docs/workspace-config-contract.md`
- `src/agentic_workspace/cli.py`
- `tests/test_workspace_cli.py`

## Invariants

- Repo config remains authoritative for repo semantics.
- Local override remains optional, untracked, and local-only.
- Runtime orchestration remains tool-owned.
- Reporting must attribute source clearly.
- Supported fields stay narrow and capability-shaped.
- Success means cheaper switching with less rediscovery.

## Contract Decisions To Freeze

- Canonical local path: repo-root `.agentic-workspace/config.local.toml`.
- Lifecycle rule: the local file must be gitignored by default and must not be required for normal workspace use.
- V1 local override scope: machine/account/cost posture only, using a short allowlist of capability-shaped fields.
- Reporting rule: `agentic-workspace config --target ./repo --format json` must show which mixed-agent values come from local override versus repo config or product defaults.
- Authority rule: local override may tune posture and preferences for the current environment but must not silently change repo-owned done criteria, ownership, or escalation contracts.

## Open Questions To Close

- Which exact fields are the smallest useful local allowlist for this first local-only contract?
- Should `defaults` expose the supported local override fields directly, or is `config` enough for the first behavior slice?
- What output shape is compact but still explicit enough for source attribution and restart-friendly debugging?

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py -q`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- `.agentic-workspace/config.local.toml` is a supported optional local-only surface and is gitignored in this repo.
- The workspace CLI reports effective mixed-agent local-override values with explicit source attribution.
- The supported local override fields stay narrow and capability/cost shaped.
- Canonical docs describe the shipped local-override contract without overclaiming runtime behavior.

## Execution Summary

- Outcome delivered: shipped a narrow supported `.agentic-workspace/config.local.toml` contract, added source-attributed mixed-agent posture reporting to `agentic-workspace config`, and aligned the config docs and repo gitignore with the new local-only surface.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q`; `uv run ruff check src tests`; `uv run python scripts/check/check_planning_surfaces.py`.
- Follow-on routed to: `ROADMAP.md`.
- Resume from: promote the next behavior-changing slice, likely validation-default refinement or a carefully bounded mixed-agent follow-through that uses the new posture surface without turning it into a scheduler.

## Drift Log

- 2026-04-13: Promoted directly after the reporting-only mixed-agent slice completed and explicit maintainer direction called for continued work on cheaper switching and local capability posture.
- 2026-04-13: Completed by shipping the local override allowlist, effective posture/source reporting, gitignore coverage, and matching config documentation.
