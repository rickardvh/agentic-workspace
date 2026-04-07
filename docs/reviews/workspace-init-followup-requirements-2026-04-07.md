# Review: Workspace Init Follow-Up Requirements

## Goal

- Identify the next missing requirements and test cases around the root workspace-layer contract after the shared init layer was added.

## Scope

- Root `agentic-workspace` lifecycle behavior
- Root workspace-layer payload and reporting
- Existing workspace CLI tests
- Packaging and partial-adoption implications

## Non-Goals

- Do not implement the follow-up fixes in this review.
- Do not reopen `TODO.md` or create a new execplan yet.
- Do not reassess planning or memory package internals beyond the root workspace-layer boundary.

## Review Method

- Commands used: `uv run pytest tests/test_workspace_cli.py`, `uv run agentic-workspace init --target <temp repo> --preset full --format json`, `uv run agentic-workspace doctor --target <temp repo> --format json`
- Evidence sources: `src/agentic_workspace/cli.py`, `tests/test_workspace_cli.py`, `docs/init-lifecycle.md`, `docs/integration-contract.md`, and root packaging metadata in `pyproject.toml`

## Findings

### Finding: Partial-adoption requirements are still ambiguous and under-tested

- Summary: The docs say the workspace layer should only appear when coordinating multiple installed modules, but the root CLI currently installs the shared workspace layer for any selected preset, including planning-only or memory-only runs. That is a real contract ambiguity, and there are no tests that force a decision either way.
- Evidence: `docs/integration-contract.md` says "The workspace layer should only appear when coordinating multiple installed modules"; `src/agentic_workspace/cli.py` always applies the workspace report and shared payload during root `init` and `upgrade`; `tests/test_workspace_cli.py` covers only full-preset behavior.
- Risk if unchanged: Future contributors can change the behavior in either direction without breaking tests, and adopters may get a workspace layer that contradicts the documented selective-adoption contract.
- Suggested action: Decide and document one rule explicitly: either the workspace layer is full-preset-only, or it is a root-CLI contract that appears for any root-managed install. Then add real-install tests for `--preset planning`, `--preset memory`, and explicit `--modules` cases.
- Confidence: high
- Source: mixed
- Promotion target: `ROADMAP.md`
- Promotion trigger: Promote when the repo next touches selective-adoption behavior or when another adopter reports confusion about planning-only or memory-only installs.

### Finding: The shipped-package requirement for workspace payload files is not yet protected by packaging tests

- Summary: The new shared workspace-layer payload exists under `src/agentic_workspace/_payload`, but there is no test that builds the root package and proves those files are actually present in the wheel or sdist. Source-tree tests alone will not catch a packaging omission.
- Evidence: `pyproject.toml` packages `src/agentic_workspace`, but there is no root test that inspects a built artifact for `_payload/.agentic-workspace/WORKFLOW.md` and `_payload/.agentic-workspace/OWNERSHIP.toml`; the current tests read directly from the source tree.
- Risk if unchanged: A release can pass local source tests while publishing a root package that cannot install the shared workspace layer from a real distribution artifact.
- Suggested action: Add a root packaging test or maintainer check that builds the wheel/sdist and asserts the workspace payload files are included and readable from the installed package.
- Confidence: high
- Source: static-analysis
- Promotion target: `ROADMAP.md`
- Promotion trigger: Promote when the root package versioning or release path is next touched, or before treating the root package as stable for adopters.

### Finding: Workspace-layer lifecycle semantics still need explicit tests for adopt, dry-run, and uninstall

- Summary: The new workspace layer is tested for clean full init and missing-file warnings, but not for the more failure-prone lifecycle paths: conservative adopt, dry-run non-mutation, and uninstall cleanup.
- Evidence: `tests/test_workspace_cli.py` covers clean install and status/doctor visibility, but it does not assert that dry-run leaves files unchanged, that adopt preserves customized `.agentic-workspace/WORKFLOW.md` or `.agentic-workspace/OWNERSHIP.toml`, or that uninstall removes managed workspace files while handling `AGENTS.md` fences predictably.
- Risk if unchanged: The highest-risk lifecycle regressions remain unguarded: destructive adopt overwrites, dry-run mutation bugs, and uninstall leaving stale workspace-pointer fences or orphaned shared files.
- Suggested action: Add tests for:
- a customized workspace payload under adopt mode that should produce `manual review` rather than overwrite,
- a dry-run init/upgrade/uninstall path that leaves the filesystem unchanged,
- uninstall behavior for managed shared-layer files plus a documented rule for whether workspace fences in `AGENTS.md` are removed or preserved.
- Confidence: high
- Source: static-analysis
- Promotion target: `ROADMAP.md`
- Promotion trigger: Promote when lifecycle work resumes or before expanding the root CLI beyond the current bootstrap contract.

### Finding: Workspace contract visibility is incomplete in module discovery surfaces

- Summary: `status` and `doctor` now report the workspace layer, but `modules` and the registry still only describe planning and memory. That leaves the shared root contract discoverable in one command path and invisible in another.
- Evidence: `_module_registry()` and `modules` output only expose `planning` and `memory`; the workspace layer appears only as an appended pseudo-report in `status`, `doctor`, `init`, `upgrade`, and `uninstall`.
- Risk if unchanged: Contributors may treat the workspace layer as an implementation detail instead of a supported part of the install contract, and future reporting changes can drift again because discovery and health surfaces are not aligned.
- Suggested action: Decide whether the workspace layer should be a first-class registry entry or whether the docs should explicitly say it is report-only and not a selectable module. Then add tests for that chosen contract.
- Confidence: medium
- Source: static-analysis
- Promotion target: canonical docs
- Promotion trigger: Promote when the root CLI discovery surface is next revised or when module selection/reporting semantics are revisited.

## Recommendation

- Promote: The first three findings are worth promotion when the next root workspace lifecycle pass is scheduled.
- Defer: The module-discovery alignment finding can wait unless the root CLI interface is being revised again soon.
- Dismiss: None.

## Validation / Inspection Commands

- `uv run pytest tests/test_workspace_cli.py`
- `uv run agentic-workspace init --target <temp repo> --preset full --format json`
- `uv run agentic-workspace doctor --target <temp repo> --format json`

## Drift Log

- 2026-04-07: Review created after the shared workspace-layer contract landed, to capture remaining requirement and test gaps before the next lifecycle pass.
