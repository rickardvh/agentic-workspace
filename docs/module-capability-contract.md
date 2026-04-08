# Module Capability Contract

This page defines the current plugin-ready internal contract for `agentic-workspace` modules.

It is intentionally stronger than ad hoc first-party assumptions, but still not a supported third-party plugin API.

## Contract Shape

Each workspace module descriptor should declare:

- `capabilities`: the durable product capabilities the module owns
- `commands`: the lifecycle hooks the workspace layer may orchestrate
- `command_args`: which lifecycle hooks accept `target`, `dry_run`, or `force`
- `install_signals`: the repo surfaces that indicate the module is materially installed
- `workflow_surfaces`: the repo surfaces that belong to the module's working contract
- `generated_artifacts`: generated outputs whose drift should be reported instead of hand-edited
- `dependencies`: other modules that must also be selected when this module is selected
- `conflicts`: other modules that may not be selected at the same time
- `result_contract`: the schema version and required top-level/action/warning fields the workspace adapter guarantees to preserve

## Current Rule

- The workspace layer may orchestrate only modules that satisfy this contract.
- Once dependency or conflict metadata is declared, the workspace selector must enforce it.
- Capability and result-contract metadata should be queryable from the root registry and `modules` output so maintainers do not need to infer them from source code.

## Not A Public Plugin API

This contract is still first-party only.

It exists so the repo can stabilize the right internal seams before external extension is supported.

See [`docs/extension-boundary.md`](docs/extension-boundary.md) for the readiness gates that still block public third-party module support.
