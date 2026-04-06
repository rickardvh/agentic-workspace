# TODO

Last pruned: 2026-04-06

## Purpose

Active queue for repository work.

## Now

- [module-registry-capability-model-2026-04-06](docs/execplans/module-registry-capability-model-2026-04-06.md) - Turn the explicit first-party module contract into a queryable registry-style model so the workspace layer can enumerate module capabilities and lifecycle support without re-encoding that knowledge across commands.

## Action

- Treat the internal module registry model as the current top priority: build on the explicit first-party module contract without broadening into a public plugin surface.
- Keep the tranche bounded around queryable module metadata, lifecycle capability enumeration, and root orchestration simplification rather than extension hooks.
- Favor replacing hard-coded module lists and repeated orchestration knowledge over adding new lifecycle verbs.
- Keep root planning surfaces compact; archive completed plans instead of letting TODO accumulate residue.
