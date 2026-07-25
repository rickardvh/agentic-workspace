# Skills Catalogue

This directory contains the product's bundled skills.

These skills are part of the package distribution and should be available to runtimes that support packaged skill discovery without a second installation step.

`REGISTRY.json` is the explicit bundled-skill registry for this package. Treat it as the machine-readable source of truth for bundled planning skill discovery and task-matching hints.

If a bundled skill is not already visible, prefer the root `agentic-workspace` command and its `planning` subcommands for host-repo work.

For maintainers of this repository, `skills/` is the canonical source of truth. Any bundled copy inside an installed package is only a runtime copy for packaging or install-path testing and may be stale until the package is reinstalled.

## Available skills

- `planning-manual-delegation`
  - delegate through canonical assignment export and import without trusting worker claims
- `planning-returned-result`
  - admit or route a returned delegated result through authoritative assignment operations
- `bootstrap-upgrade`
  - upgrade planning bootstrap files for an already bootstrapped repository safely
- `planning-autopilot`
  - execute bounded planning slices from checked-in planning surfaces until the active objective reaches an authorized terminal outcome
- `planning-orchestrator-workflow`
  - primary procedure for an assigned orchestrator to dispatch, track, and admit bounded delegated work
- `planning-intake-upstream-task`
  - turn an externally tracked issue or task into checked-in planning while keeping the upstream tracker as an intake source only
- `planning-decompose`
  - decompose epic or lane shaped work into bounded schema-backed planning records before execplans
- `planning-new-plan-tighten`
  - create or tighten a schema-backed execplan scaffold before coding
- `planning-assurance-delegation`
  - narrow pre-decision assessment reference for risk, proof cost, ambiguity, and capability fit
- `planning-high-assurance-lifecycle`
  - preserve intent, decomposition, assurance, delegation, proof, and closeout for broad or high-assurance planning work
- `planning-intent-verification`
  - verify original, interpreted, parent, and negative intent before decomposition, validation, or completion claims
- `planning-closeout-trust`
  - close out planned work with proof, intent satisfaction, trust, and residue distillation
- `planning-promote-review-findings`
  - turn selected reviewed findings into roadmap or active-planning candidates without collapsing capture and promotion
- `planning-review-pass`
  - run a bounded review pass and capture compact findings under `.agentic-workspace/planning/reviews/`
- `planning-reporting`
  - report active planning state, proof expectations, and next-action guidance from the canonical summary JSON

These bundled skills cover payload refresh, bounded planning execution, high-assurance lifecycle preservation, intent verification, work decomposition, execplan tightening, pre-decision assurance assessment, the primary assigned-orchestrator workflow, closeout trust, review capture, review-to-plan promotion, and upstream-task intake.
