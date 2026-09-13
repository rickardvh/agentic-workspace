# Native Tool Map

The canonical `workspace-startup` skill teaches ordinary agent procedure. Use
[everyday use](../everyday-use.md) for examples and the generated
[native CLI catalogue](../reference/cli-catalogue.md) for exact commands and flags.
The catalogue comes from `source_decision_contract.json`'s `native_cli` declaration,
the same declaration used by the executable. Check the selected artifact's
`agentic-workspace --help` for its actual boundary.

## Current tools

| Need | Native tool |
| --- | --- |
| Resolve current state, including known changed paths | `start --target . --task "<task>" --format json`; add repeated `--changed <path>` when known |
| Execute one exact owner-returned action | `invoke --input <action.json>` with the same target/task/changed context |
| Inspect local hygiene or use a current resource operation | `resources --input <request.json>` using its bounded resource contract |
| Project worker entry, expand captured input or assemble a return | `worker --input <request.json>` using the original machine-carried Assignment packet |

Domain requests and optional detail come from current owners through these tools,
not nested or module CLI commands. Supply only the requested new judgment/material.
Use returned references and supported `--projection` values for detail/carriage;
there is no native `--select` or `--verbose` drill-down.

## Authority and availability

A returned request, route or packet seal does not grant mutation, ownership, proof
or completion authority. `invoke` revalidates the exact action. Consume current
continuation after an effect; uncertainty requires owner recovery rather than a
repeat execution. Optional machine-local diagnostics are separate from repository
mutation and do not become domain authority merely because they exist.

Historical `implement`, `summary`, `proof`, `doctor`, `report`, initialization and
module command families are not ordinary native routes. Retained generated CLI
schemas and lifecycle tooling are source-maintenance or historical references,
not hidden native capabilities or an alternative host to bypass rejection.
See [installation and adoption limits](../agentic-workspace-install.md) and the
[reference index](../reference/index.md) for that distinction.
