# Skills Catalogue

This directory contains the product's bundled skills.

These skills are part of the package distribution and should be available to runtimes that support packaged skill discovery without a second installation step.

`REGISTRY.json` is the explicit bundled-skill registry for this package. Treat it as the machine-readable source of truth for bundled planning skill discovery and task-matching hints.

If a bundled skill is not already visible, prefer the installed `agentic-planning-bootstrap` command or the repo's checked-in `.agentic-planning/UPGRADE-SOURCE.toml` as the source of truth for any remote `uvx` or `pipx` runner spec.

For maintainers of this repository, `skills/` is the canonical source of truth. Any bundled copy inside an installed package is only a runtime copy for packaging or install-path testing and may be stale until the package is reinstalled.

## Available skills

- `bootstrap-upgrade`
  - upgrade planning bootstrap files for an already bootstrapped repository safely
- `planning-autopilot`
  - execute one bounded planning milestone at a time from the checked-in planning surfaces
- `planning-orchestrator-workflow`
  - run planner-to-worker delegated execution from checked-in planning using the local mixed-agent posture and a derived handoff contract
- `planning-intake-upstream-task`
  - turn an externally tracked issue or task into checked-in planning while keeping the upstream tracker as an intake source only
- `planning-promote-review-findings`
  - turn selected reviewed findings into roadmap or active-planning candidates without collapsing capture and promotion
- `planning-review-pass`
  - run a bounded review pass and capture compact findings under `.agentic-workspace/planning/reviews/`
- `planning-reporting`
  - report active planning state, proof expectations, and next-action guidance from the canonical summary JSON

These bundled skills cover payload refresh, bounded planning execution, delegated planning workflow, review capture, review-to-plan promotion, and upstream-task intake.
