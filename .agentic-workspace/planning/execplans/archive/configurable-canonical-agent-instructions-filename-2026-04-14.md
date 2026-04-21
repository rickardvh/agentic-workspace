# Configurable Canonical Agent-Instructions Filename

## Goal

- Let the workspace layer use a supported canonical root startup-entrypoint filename other than `AGENTS.md` when a repo already standardizes on one.
- Keep the behavior conservative enough that selective adoption, bootstrap ambiguity detection, and repo-owned startup preservation still hold.

## Non-Goals

- Support arbitrary startup filenames.
- Redesign package-local `AGENTS.md` routing.
- Turn the workspace layer into a runtime-specific agent vendor shim.

## Intent Continuity

- Larger intended outcome: close the last open GitHub issue by removing the remaining hard-coded root startup-file assumption from workspace lifecycle reporting and bootstrap.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Delegated Judgment

- Requested outcome: add a narrow checked-in contract for the canonical root startup filename, expose it through workspace defaults/config, keep blank and existing repos conservative, and dogfood the result through real bootstrap passes.
- Hard constraints: keep support narrow and capability-shaped; preserve one-home startup discipline; do not rewrite repo-owned startup files blindly in existing repos; keep package-local `AGENTS.md` guidance unchanged.
- Agent may decide locally: the supported filename set, the exact config/reporting fields, and the smallest lifecycle/reporting/doc updates needed to keep the contract trustworthy.
- Escalate when: the slice would require arbitrary filename support, package-level lifecycle redesign, or broad changes to descendant startup guidance.

## Active Milestone

- ID: configurable-canonical-agent-instructions-filename
- Status: completed
- Scope: ship `workspace.agent_instructions_file`, add conservative autodetect of one existing supported startup file, align workspace lifecycle/handoff surfaces, and close GitHub issue `#28`.
- Ready: ready
- Blocked: none
- optional_deps: GitHub issue `#28`

## Immediate Next Action

- None. Slice completed; there are no remaining open GitHub issues.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `README.md`
- `docs/default-path-contract.md`
- `docs/init-lifecycle.md`
- `docs/workspace-config-contract.md`
- `src/agentic_workspace/cli.py`
- `tests/test_workspace_cli.py`

## Invariants

- Supported startup filenames stay narrow and explicit.
- The resolved startup entrypoint must be visible through machine-readable reporting.
- Existing repos with multiple supported startup files should still be treated as high ambiguity.
- Blank/custom installs should not leave a redundant default `AGENTS.md` behind.

## Contract Decisions To Freeze

- The supported root startup-entrypoint filenames are currently `AGENTS.md` and `GEMINI.md`.
- Repo config may set `workspace.agent_instructions_file`; otherwise the workspace may autodetect exactly one existing supported startup file before falling back to `AGENTS.md`.
- The workspace wrapper owns normalization of package-level root-entrypoint assumptions when a non-default startup file is configured.

## Open Questions To Close

- What is the smallest supported startup filename set that still covers real cross-agent adoption friction?
- How should workspace reporting surface the difference between repo-configured, autodetected, product-default, and explicit CLI startup filename selection?

## Validation Commands

- `uv run ruff check src tests`
- `uv run pytest tests/test_workspace_cli.py -q`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-workspace config --target . --format json`
- `uv run agentic-workspace defaults --section startup --format json`
- `uv run agentic-workspace init --target <temp-repo> --agent-instructions-file GEMINI.md --dry-run --format json`
- `uv run agentic-workspace init --target <temp-repo> --agent-instructions-file GEMINI.md --format json`

## Completion Criteria

- The workspace config/defaults surfaces report the effective canonical root startup filename.
- Bootstrap and handoff surfaces use the resolved startup filename instead of hard-coding `AGENTS.md`.
- Blank/custom installs can use `GEMINI.md` without leaving a redundant default `AGENTS.md`.
- Existing repos with multiple supported startup filenames still trigger conservative ambiguity handling.

## Execution Summary

- Outcome delivered: the workspace now supports a narrow configurable root startup-entrypoint contract via `workspace.agent_instructions_file`, conservatively autodetects one existing supported startup file when config omits it, reports the effective filename and source through `agentic-workspace config` and `defaults`, rewrites workspace-level module reports to the configured entrypoint, and removes redundant default `AGENTS.md` during blank/custom installs so real `GEMINI.md` bootstrap passes stay coherent.
- Validation confirmed: `uv run ruff check src tests`; `uv run pytest tests/test_workspace_cli.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace config --target . --format json`; `uv run agentic-workspace defaults --section startup --format json`; real temp-repo dry-run and non-dry-run `GEMINI.md` bootstrap passes.
- Follow-on routed to: `ROADMAP.md`.
- Resume from: no remaining GitHub issue intake; promote only when a new bounded mixed-agent continuity/trust gap is confirmed.

## Drift Log

- 2026-04-14: Promoted after the lazy-discovery measurement tranche left GitHub issue `#28` as the final remaining open issue.
- 2026-04-14: Initial implementation exposed a real package-to-workspace mismatch during dogfooding: the workspace layer switched to `GEMINI.md`, but underlying module install plans still surfaced `AGENTS.md`.
- 2026-04-14: Completed by normalizing workspace lifecycle/handoff reporting to the resolved startup filename, removing redundant default `AGENTS.md` during blank/custom installs, aligning the startup contract docs, and proving the path through real temp-repo `GEMINI.md` installs.
