# Review: Bootstrap Tooling Follow-Up Requirements

## Goal

- Identify the next missing requirements and test cases for the bootstrapping tools as a product family: root workspace orchestration plus the planning and memory bootstraps.

## Scope

- Root `agentic-workspace` lifecycle and packaging
- `agentic-planning-bootstrap` lifecycle and payload guarantees
- `agentic-memory-bootstrap` lifecycle and payload guarantees
- Cross-tool migration, upgrade, and composition behavior

## Non-Goals

- Do not implement the follow-up fixes in this review.
- Do not promote work into `TODO.md` or an execplan yet.
- Do not reopen already-closed findings unless they materially affect bootstrap-tooling requirements.

## Review Method

- Commands used: `uv run pytest tests/test_workspace_cli.py`, `uv run pytest packages/planning/tests`, `uv run pytest packages/memory/tests`
- Evidence sources: `src/agentic_workspace/cli.py`, `tests/test_workspace_cli.py`, `packages/planning/tests/test_installer.py`, `packages/memory/tests/test_installer.py`, `docs/init-lifecycle.md`, `docs/integration-contract.md`, `packages/planning/README.md`, `packages/memory/README.md`, `pyproject.toml`

## Findings

### Finding: Packaging fidelity is still under-specified across all three shipped tools

- Summary: The current tests mostly exercise source-tree installs. They do not prove that the actual built artifacts for `agentic-workspace`, `agentic-planning-bootstrap`, and `agentic-memory-bootstrap` contain the required payloads, bundled skills, and helper files needed by real adopters.
- Evidence: Root tests read `src/agentic_workspace/_payload` directly; planning and memory tests call installer functions against local payload roots; there is no root-level build-and-inspect test for wheel or sdist contents.
- Risk if unchanged: A release can pass local source tests while publishing an artifact with missing payload files, missing bundled skills, or broken package data paths. That failure mode would only show up after an adopter tries a real install.
- Suggested action: Add artifact-level packaging tests for all three packages. At minimum:
- build wheel and sdist for root, planning, and memory,
- inspect the built archives or install them into a clean temp environment,
- assert required payload files, bundled skills, and helper scripts are present and readable from the installed package.
- Confidence: high
- Source: static-analysis
- Promotion target: `ROADMAP.md`
- Promotion trigger: Promote before the next package release or when package-data layout changes again.

### Finding: Lifecycle-matrix coverage is strong in places but still incomplete for high-risk paths

- Summary: Each tool has some lifecycle coverage, but the matrix is uneven. Clean install is relatively well covered; the more failure-prone paths are not consistently locked down across root, planning, and memory.
- Evidence: The root CLI now has real-init coverage, but not a broad matrix for dry-run non-mutation, selective adoption, or uninstall fence cleanup. Planning has good install/adopt/upgrade/uninstall coverage, but not explicit artifact-backed lifecycle verification. Memory has broad installer tests, but the lifecycle matrix is larger and more policy-heavy, which makes regression gaps more expensive.
- Risk if unchanged: The highest-cost regressions tend to land in adopt, upgrade, uninstall, and dry-run semantics rather than clean install. Those are exactly the paths that adopters hit when the repo is already real and already customized.
- Suggested action: Define one shared lifecycle matrix that every bootstrap tool should satisfy:
- clean install creates all required managed surfaces,
- dry-run mutates nothing,
- adopt preserves repo-owned or customized surfaces and reports review items correctly,
- upgrade refreshes managed surfaces but preserves repo-owned ones,
- uninstall removes only safe owned surfaces and handles managed fences predictably,
- rerunning install or upgrade is idempotent.
- Confidence: high
- Source: mixed
- Promotion target: `ROADMAP.md`
- Promotion trigger: Promote when the next lifecycle pass touches install/adopt/upgrade/uninstall semantics in any package.

### Finding: Migration and legacy-adopter compatibility need first-class product tests, not just one-off reproduction

- Summary: The radiatorvvs-calculator issue exposed a migration failure from older standalone installs into the newer combined toolchain. That class of problem should be a maintained test fixture, not just a historical investigation.
- Evidence: The recent investigation reproduced a real adopter repo that had legacy `agentic-memory` residue, removed the old install, and then landed in an incomplete combined state. There is no shared migration-fixture suite at the root proving that the tools can detect, adopt, upgrade, or warn correctly across older generations.
- Risk if unchanged: Legacy adopters remain the most likely path to "looks healthy but isn’t" outcomes. Regressions here are easy to miss because greenfield install tests stay green.
- Suggested action: Add migration fixtures representing at least:
- an older standalone memory install,
- a planning-only repo later upgraded to full,
- a memory-only repo later upgraded to full,
- a partially managed repo with stale generated surfaces and customized root files.
- Confidence: high
- Source: friction-confirmed
- Promotion target: `ROADMAP.md`
- Promotion trigger: Promote before the next bootstrap release intended for outside adopters, or when another legacy adopter issue appears.

### Finding: Selective-adoption requirements are still inconsistent across docs and implementation

- Summary: The product family says selective adoption is a requirement, but the root workspace layer currently blurs that rule. The docs and implementation have not yet converged on whether the workspace layer is full-stack-only or part of any root-managed install.
- Evidence: Planning and memory READMEs both say they should work alone without requiring the full stack or workspace layer. `docs/integration-contract.md` says the workspace layer should only appear when coordinating multiple installed modules. The root CLI currently installs the workspace shared layer for any selected preset through the root orchestrator.
- Risk if unchanged: Contributors can unintentionally erode selective adoption while still thinking they are honoring it, because the actual contract is not yet expressed as a testable rule.
- Suggested action: Write one explicit requirement for each entrypoint:
- package-local planning CLI behavior in a planning-only repo,
- package-local memory CLI behavior in a memory-only repo,
- root workspace CLI behavior for planning-only, memory-only, and full presets.
- Confidence: high
- Source: mixed
- Promotion target: `ROADMAP.md`
- Promotion trigger: Promote when the root CLI or any selective-adoption docs are next revised.

### Finding: Cross-tool reporting and discovery surfaces are not yet aligned

- Summary: The tool family is getting better at reporting install state, but the contract is still fragmented. Some surfaces expose only modules, some expose module plus workspace, and the meaning of `healthy`, `manual review`, `customised`, `missing`, and `warning` still varies by tool.
- Evidence: The root CLI appends a workspace pseudo-report in lifecycle commands but not in `modules`; planning and memory use their own result/action vocabularies; memory has a richer safety/category model than planning or root; recent dogfooding already required tightening report semantics around localized seed notes versus real manual review.
- Risk if unchanged: Adopters and future maintainers will keep re-deriving what the reports mean, and the product family will drift toward tool-specific conventions instead of one coherent bootstrap contract.
- Suggested action: Define a shared reporting contract for the bootstrap family:
- common action classes and severity semantics,
- explicit health derivation rules,
- clear distinction between safe customisation, real drift, and hard failure,
- a rule for whether the workspace layer is discoverable as a first-class install surface.
- Confidence: medium
- Source: mixed
- Promotion target: canonical docs
- Promotion trigger: Promote when result-shape work or cross-tool reporting changes again.

### Finding: Product-level smoke tests should verify the installed workflow from an adopter perspective

- Summary: Most current tests verify installer internals or repo-local effects. There is still little coverage for the actual adopter experience of invoking the shipped CLI entrypoints from a clean environment and then using the resulting repo as intended.
- Evidence: Existing tests mostly call installer functions directly; the root CLI tests exercise the local monorepo environment; there is no maintained smoke suite that installs the packaged tools into a clean temp repo and then runs the expected user-facing command sequence end to end.
- Risk if unchanged: The package can drift toward "internally correct" while still breaking the actual bootstrapping experience that users and agents depend on.
- Suggested action: Add a lightweight smoke lane that:
- installs each shipped CLI from the built artifact into a clean temp environment,
- runs `install` or `init`,
- runs `doctor` and `status`,
- verifies the resulting repo has the expected startup and upgrade entrypoints.
- Confidence: medium
- Source: static-analysis
- Promotion target: `ROADMAP.md`
- Promotion trigger: Promote when release readiness or adopter-facing reliability becomes the next maintenance focus.

## Recommendation

- Promote: Findings 1 through 4 are the highest-value follow-up lane for bootstrap-tooling hardening.
- Defer: Findings 5 and 6 are worth doing, but they can follow once packaging, migration, and lifecycle guarantees are tighter.
- Dismiss: None.

## Validation / Inspection Commands

- `uv run pytest tests/test_workspace_cli.py`
- `uv run pytest packages/planning/tests`
- `uv run pytest packages/memory/tests`

## Drift Log

- 2026-04-07: Review created after the shared workspace-layer fix, broadened to the whole bootstrap-tooling family after clarifying that the requirement question is not root-only.
