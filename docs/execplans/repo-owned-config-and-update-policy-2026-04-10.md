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
- This slice completes the larger intended outcome: no
- Continuation surface: `TODO.md`

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `TODO.md`
- Activation trigger: this contract slice is accepted and implementation is chosen as the next bounded active work.

Required follow-on detail:
implement the approved config surface, effective-config reporting, and policy-aware lifecycle follow-through in one or more bounded execution tranches, with update application routed through `agentic-workspace` rather than direct module maintenance paths.

## Active Milestone

- Status: active
- Scope: make the implementation-blocking contract decisions for config location, v1 schema, update-policy precedence, provenance modes, and wrapper-only update execution.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Record the implementation-ready decisions for config location, allowed v1 fields, update-policy precedence, provenance support, and wrapper-only update execution in one canonical contract note.

## Blockers

- None.

## Touched Paths

- `docs/execplans/repo-owned-config-and-update-policy-2026-04-10.md`
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

- Canonical config location: repo root `agentic-workspace.toml`, not `.agentic-workspace/`.
- V1 config scope: thin selection and policy fields only; no active state, free-form instructions, scheduler semantics, or workflow scripting.
- Effective config reporting: a future `agentic-workspace config --format json` reports resolved repo overrides layered onto product defaults.
- Update application path: normal updates run through `agentic-workspace` even when config carries module-specific version intent.

## Open Questions To Close

- Should v1 allow only workspace-level update policy, or allow bounded module-level overrides under the same wrapper-only lifecycle model?
- If workspace-level and module-level version intents disagree, what is the precedence rule?
- Which provenance modes are first-class in v1: published versions only, or published versions plus bounded git refs?
- If git refs are allowed, are they a normal supported mode or an explicitly advanced path?
- What should `agentic-workspace upgrade` do by default after config pins change: converge immediately to the new intent, or require an explicit acknowledgement/report mode first?
- How should `status` and `doctor` distinguish package drift, source drift, and intentional repo-local pinning?

## Validation Commands

- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run pytest tests/test_workspace_cli.py`
- `make maintainer-surfaces`

## Completion Criteria

- The plan records a bounded v1 config contract with a small allowed field set and explicit exclusions.
- The plan names the canonical config location and ownership model in a way that matches the current workspace boundary rules.
- The plan defines an update-policy model that handles workspace/module intent and provenance without relying on passive scheduler hints.
- The plan makes `agentic-workspace` the default and normally exclusive update application surface even when config can express module-specific version intent.
- The plan closes the implementation-blocking precedence and provenance questions tightly enough that the next tranche can edit CLI/docs/tests without re-litigating contract shape.
- The resulting follow-on implementation work can be split into one or more narrow execution tranches without reopening the product-shape debate.

## Execution Summary

- Outcome delivered: none yet.
- Validation confirmed: none yet.
- Follow-on routed to: `TODO.md`
- Resume from: close the open questions and promote the first implementation tranche from the frozen contract decisions.

## Drift Log

- 2026-04-10: Promoted by explicit maintainer choice after repo-owned customization and update-policy questions converged into one bounded product-shape slice.
- 2026-04-10: Clarified that normal update execution must stay behind the `agentic-workspace` wrapper even if config can express workspace- or module-level version intent.
