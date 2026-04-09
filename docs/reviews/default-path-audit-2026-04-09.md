# Default-Path Audit

## Goal

- Check whether the normal startup, install, and operating path is now unmistakable enough that agents and maintainers no longer have to choose between several equally plausible front-door routes.

## Scope

- Root front-door docs.
- Package chooser docs.
- Workspace machine-readable default-route surface.

## Non-Goals

- Broad package-internal maintainer workflow review.
- New lifecycle features or routing behavior.

## Review Mode

- Mode: `context-cost`
- Review question: Do the front-door surfaces now make the default path cheaper to follow than the advanced alternatives?
- Default finding cap: 2 findings
- Inputs inspected first: `README.md`, `docs/which-package.md`, `docs/default-path-contract.md`, `src/agentic_workspace/cli.py`

## Review Method

- Commands used:
  - `uv run pytest tests/test_workspace_cli.py`
  - `uv run python scripts/check/check_planning_surfaces.py`
- Evidence sources:
  - root README default path
  - chooser doc
  - structured defaults output

## Findings

### Finding: Front door previously made the normal route look heavier than it was

- Summary: The old front-door shape asked first-time readers to absorb product taxonomy, package nuance, advanced paths, and maintainer routing before the default install and operating path had become visually dominant.
- Evidence: The new root README now leads with one preset-based install command, one default lifecycle entrypoint, and one compact next-command lane, while advanced and package-local paths are explicitly demoted into a later section.
- Risk if unchanged: Higher startup reading cost and more route-selection overhead than the product contract requires.
- Suggested action: Keep the default path compressed in `README.md` and `docs/which-package.md`, and point route questions to the machine-readable defaults surface instead of adding more front-door prose.
- Confidence: high
- Source: mixed
- Promotion target: canonical docs
- Promotion trigger: Implemented in this tranche.
- Post-remediation note shape: delete

### Finding: Default-path questions needed a queryable contract, not another explanatory doc

- Summary: Repeated route questions such as how to start, which lifecycle verb to use, and how to validate safely were still answerable only by reading several docs, even though the answers are stable enough to expose structurally.
- Evidence: `agentic-workspace defaults --format json` now emits startup, lifecycle, skill-discovery, validation, and combined-install defaults from one machine-readable surface, and `docs/default-path-contract.md` points readers there.
- Risk if unchanged: Smaller or cheaper agents would continue paying prose-reading cost for recurring questions with stable answers.
- Suggested action: Treat the CLI defaults output as the primary structured answer for recurring route questions and keep prose as explanation and boundary guidance.
- Confidence: high
- Source: friction-confirmed
- Promotion target: canonical docs
- Promotion trigger: Implemented in this tranche.
- Post-remediation note shape: delete

## Recommendation

- Promote: none
- Defer: none
- Dismiss: any further front-door reshaping until repeated friction shows the new default path is still too dense

## Validation / Inspection Commands

- `uv run pytest tests/test_workspace_cli.py`
- `uv run python scripts/check/check_planning_surfaces.py`

## Drift Log

- 2026-04-09: Review created and resolved by the front-door defaults tranche.
