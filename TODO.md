# TODO

Last pruned: 2026-04-06

## Purpose

Active queue for repository work.

## Now

- [first-party-module-contract-2026-04-06](docs/execplans/first-party-module-contract-2026-04-06.md) - Formalize the shared first-party module contract so the workspace layer can orchestrate planning and memory through the same explicit metadata and adapter boundaries instead of accreted module-specific knowledge.

## Action

- Treat first-party module contract as the current top priority: turn the existing planning and memory orchestration shape into an explicit shared internal module contract.
- Keep the tranche bounded around first-party module metadata, adapter behavior, and ownership boundaries rather than registry or plugin design.
- Favor removing root-layer special cases and duplicate module knowledge over adding new lifecycle verbs.
- Keep root planning surfaces compact; archive completed plans instead of letting TODO accumulate residue.
