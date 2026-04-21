# Repo-Owned Config And Update Policy

## Goal

- Freeze the v1 contract decisions for repo-owned config and provenance-aware update policy so implementation can proceed without reopening product-shape questions.
- Keep version intent repo-owned when needed, but make `agentic-workspace` the only normal lifecycle surface for applying updates across workspace and modules.

## Non-Goals

- Implement the full config parser, CLI commands, migration logic, or upgrade resolution in this slice.
- Turn repo config into a second workflow engine or duplicate product-managed contracts.
- Move module-owned lifecycle or version logic into the workspace layer without a clear shared contract.
- Add time-based automation or scheduled update checks as part of the core lifecycle model.
- Normalize direct module-by-module update workflows for regular adopters.

## Intent Continuity

- Larger intended outcome: make lifecycle management almost trivial for adopters while preserving thin orchestration, repo-owned customization, and future extensibility.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Active Milestone

- Status: completed
- Scope: freeze and implement the v1 config contract for repo-owned lifecycle defaults plus wrapper-owned update execution.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None. Slice completed and archived after the config surface, wrapper sync behavior, docs, and validation landed.

## Blockers

- None.

## Touched Paths

- `.agentic-workspace/planning/execplans/repo-owned-config-and-update-policy-2026-04-10.md`
- `TODO.md`
- `docs/`

## Invariants

- Repo-owned customization stays outside `.agentic-workspace/`; product-managed state stays inside managed surfaces.
- The workspace layer remains a thin lifecycle orchestrator and must not absorb module-owned domain policy by convenience.
- Missing config fields mean product defaults; repo config narrows or selects supported behavior but does not bypass ownership or safety rules.
- `agentic-workspace defaults` remains the machine-readable front-door contract; any future `config` surface reports resolved repo overrides layered onto that contract rather than replacing it.
- Update policy must express explicit provenance and version intent before any time-based freshness or automation semantics are considered.
- Regular update application routes through `agentic-workspace`.
- Module-specific pins do not create separate public upgrade entrypoints.

## Contract Decisions To Freeze

- Canonical config location: repo root `.agentic-workspace/config.toml`, not `.agentic-workspace/`.
- V1 config scope: `workspace.default_preset` plus per-module update-source policy only; no active state, free-form instructions, scheduler semantics, or workflow scripting.
- Effective config reporting: `agentic-workspace config --target ./repo --format json` reports resolved repo overrides layered onto product defaults.
- Update provenance modes in v1: module-specific `git` or `local` source metadata, matching the current package upgrade-source contract.
- Update application path: normal updates run through `agentic-workspace`, which keeps module `UPGRADE-SOURCE.toml` metadata aligned with repo-owned intent.

## Open Questions To Close

- None. The implementation landed with module-specific update policy only, `git`/`local` provenance only, and wrapper-owned metadata sync/reporting.

## Validation Commands

- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run pytest tests/test_workspace_cli.py`
- `make maintainer-surfaces`

## Completion Criteria

- Completed: the repo now has a bounded v1 config contract with explicit allowed fields and exclusions.
- Completed: the canonical config location and ownership model now match the workspace boundary rules.
- Completed: the update-policy model now uses module-specific `git`/`local` provenance without scheduler semantics.
- Completed: `agentic-workspace` remains the default and normally exclusive update application surface even when config expresses module-specific version intent.
- Completed: the implementation landed in CLI, docs, tests, and repo dogfooding without reopening the product-shape debate.

## Execution Summary

- Outcome delivered: shipped repo-root `.agentic-workspace/config.toml`, `agentic-workspace config`, config-driven default preset selection, wrapper-owned module update-source sync/reporting, canonical docs, and repo dogfooding of the new contract.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py`; `uv run pytest packages/planning/tests/test_check_planning_surfaces.py`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-planning-bootstrap upgrade --target .`; `make maintainer-surfaces`.
- Follow-on routed to: none.
- Resume from: no further action in this plan.

## Drift Log

- 2026-04-10: Promoted by explicit maintainer choice after repo-owned customization and update-policy questions converged into one bounded product-shape slice.
- 2026-04-10: Clarified that normal update execution must stay behind the `agentic-workspace` wrapper even if config can express workspace- or module-level version intent.
- 2026-04-10: Completed by landing the v1 config contract, wrapper sync/reporting behavior, docs, tests, and repo-owned config dogfooding.
