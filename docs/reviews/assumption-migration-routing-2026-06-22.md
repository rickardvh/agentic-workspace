# Assumption Migration Routing

Date: 2026-06-22

Issues: #1672, #1674, #1676

## Result

- Removed the package-owned assumptions inventory as a durable validated surface.
- Moved the stable `defaults-router.text` projection into declared AW-owned view metadata at `src/agentic_workspace/contracts/workspace_output_views.json`.
- Updated Verification match evidence so task markers are host-declared advisory signals and structured path/planning/assurance evidence remains visible separately.
- Added command-authority facts to proof obligations so surfaced proof commands name the structured source that caused AW to recommend them.

## Boundaries

There is intentionally no `assumption_migration` report section and no maintained package-owned assumptions inventory. Package-owned conclusions must be removed or moved directly to the correct authority surface. Review notes may record dogfooding evidence, but ordinary-loop behavior must come from contracts, declared config, planning state, external intent, Memory, or runtime facts.

Current direct migrations are bounded as follows:

- `defaults-router.text`: view labels and field order are declared in `workspace_output_views.json`; the runtime renders that contract and falls back only if the contract cannot be read.
- `proof command authority`: proof obligations report why a command was surfaced, but the agent still owns proof sufficiency.
- `verification task markers`: host-declared manifest markers are advisory `match_signals`; structured path, planning, assurance, and stale evidence are counted separately.

The remaining follow-up issues should close only when their assumptions move into the proper authority homes or are removed. This PR does not close the broader package-owned assumption lane.
