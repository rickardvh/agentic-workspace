# Payload Drift Detection and Local-only Adoption

## Goal

- Restore high trust in payload integrity through early drift detection.
- Enable "guest mode" usage of Agentic Workspace in unowned repositories through `--local-only` installation.

## Non-Goals

- Redesigning the entire packaging model.
- Broadly rewriting installer internals for both packages in one pass (beyond what's needed for drift/local-only).

## Machine-Readable Contract

```yaml
intent:
  outcome: "Early payload-drift detection in report and functional local-only mode for both packages."
  constraints: "Must not break existing installation or upgrade workflows. Must maintain monorepo mirroring invariants."
  latitude: "Agent may decide the exact format of the drift report finding."
  escalation: "Escalate if payload-root resolution logic needs breaking changes."
execution:
  milestone: "Lane 1 & 2 Implementation"
  status: "not-started"
  next_step: "Implement refined drift detection in planning/installer.py"
  proof: "agentic-workspace report surfaces drift; local-only install creates files in .gemini/"
scope:
  touched:
    - packages/planning/src/repo_planning_bootstrap/installer.py
    - packages/memory/src/repo_memory_bootstrap/installer.py
    - packages/memory/src/repo_memory_bootstrap/_installer_paths.py
    - src/agentic_workspace/cli.py
    - docs/installer-behavior.md
  invariants:
    - payload_root() must resolve correctly in packaged and dev modes.
    - Mirroring must be verified against REQUIRED_PAYLOAD_FILES.
```

## Intent Continuity

- Larger intended outcome: Formalizing Agentic Workspace Memory and Hygiene
- This slice completes the larger intended outcome: no
- Continuation surface: docs/execplans/payload-drift-and-local-adoption.md
- Parent lane: payload-drift-and-installer-knowledge, local-only-adoption-and-external-agent-ergonomics

## Delegated Judgment
- The agent may choose the most efficient way to detect drift (e.g., hash-based vs. full content).
- The agent may decide on the specific wording of warning messages.

## Execution Summary
- **Lane 1 (Payload Drift Detection)**: COMPLETED.
  - Implemented `_detect_payload_drift` in both `planning` and `memory` installers.
  - Integrated drift detection into `agentic-workspace report` and `memory_report`.
  - Verified that missing, differing, or extra payload files are correctly reported.
  - Resolved false positives in tests and non-dev targets by passing `target_root`.
- **Lane 2 (Local-only Adoption)**: PLANNED.

## Required Continuation
- **Required follow-on for the larger intended outcome**: yes
- **Trigger**: Implementation of Lane 2 (Local-only Adoption).
- **Next Owner**: implementer
- **Context**: Payload drift detection is stable. Next step is enabling guest-mode via `--local-only` flag.

## Iterative Follow-Through

- What this slice enabled: Earlier detection of hygiene errors and guest-mode workflows.
- Intentionally deferred: Full automation of mirroring.
- Discovered implications: none
- Proof achieved now: none
- Validation still needed: drift detection verification, local-only install verification.
- Next likely slice: none (this plan covers both lanes)

## Active Milestone

- Status: not-started
- Scope: Lane 1 (Drift) and Lane 2 (Local-only)
- Ready: yes
- Blocked: no

## Immediate Next Action

- Implement refined drift detection in `packages/planning/src/repo_planning_bootstrap/installer.py`.

## Blockers

- None.

## Touched Paths

- packages/planning/src/repo_planning_bootstrap/installer.py
- packages/memory/src/repo_memory_bootstrap/installer.py
- src/agentic_workspace/cli.py
- docs/installer-behavior.md

## Invariants

- `agentic-workspace report` must be the primary surface for discovering drift.
- Local-only mode must never write to tracked repository files (except .gitignore).

## Validation Commands

- `agentic-workspace report`
- `agentic-workspace install --local-only`
- `uv run pytest packages/planning/tests`
- `uv run pytest packages/memory/tests`

## Completion Criteria

- [ ] `agentic-workspace report` surfaces drift when a mirror file is missing or differs from root.
- [ ] `agentic-workspace install --local-only` creates a functional installation in `.gemini/agentic-workspace/`.
- [ ] `docs/installer-behavior.md` accurately describes payload resolution for both packages.
- [ ] All tests pass.

## Drift Log

- 2026-04-19: Initial plan created for Lane 1 and 2.
