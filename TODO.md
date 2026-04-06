# TODO

Last pruned: 2026-04-06

## Purpose

Active queue for repository work.

## Now

- [workspace-bootstrap-ux-2026-04-06](docs/execplans/workspace-bootstrap-ux-2026-04-06.md) - Make the root `agentic-workspace` CLI the obvious bootstrap and lifecycle entrypoint with preset/module selection, conservative repo-state detection, machine-readable reports, and repo-specific handoff prompts.

## Action

- Treat workspace bootstrap UX as the current top priority: one obvious `init` entrypoint, conservative adopt behavior for existing repos, and lifecycle verbs that compose modules without absorbing their domain logic.
- Keep the tranche bounded around four outcomes: `init` becomes the default root workflow, module selection is preset- or module-driven, bootstrap emits structured reports plus repo-specific prompts, and later lifecycle verbs stay coherent and light.
- Preserve package boundaries: keep module-specific rules inside the memory and planning packages while the workspace layer owns selection, sequencing, detection, and aggregation.
- Prefer report/prompt generation, validation coverage, and adopter docs over inventing new workspace-owned domain semantics.
- Keep root planning surfaces compact; archive completed plans instead of letting TODO accumulate residue.
