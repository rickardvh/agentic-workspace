# Choose an AW output view

Use this reference when a CLI or API consumer needs more detail than the default
response, or needs to carry exact requests outside the model's context. For a
worked query, answer and invocation, use the [CLI guide](commands.md).

The default response should contain what changes the next decision: applicable
restrictions, questions and exact available actions. Optional inventories and
diagnostics should not obscure that information.

## Choose how much to return

`start` accepts three values for `--projection`; API callers use the same values
in `projection`:

| View | Use it when |
| --- | --- |
| `compact` (default) | The caller needs the current decision and exact selected requests/actions. Optional detail stays behind `detail_refs`. |
| `full` | The caller deliberately needs expanded component details or the current capability contract, for example while debugging an integration. |
| `carried` | A host can keep opaque transport data outside model output. The result separates the model-facing `view` from disposable `carriage`. |

For example, from the repository being inspected, using the installation chosen
in [Getting started](../agentic-workspace-install.md#1-install-aw):

```sh
agentic-workspace start --target . --task "Inspect this repository" --projection full --format json
```

Changing the view does not grant permission, satisfy a requirement or perform an
action. Compact output retains relevant restrictions; a shorter answer is not a
weaker set of checks.

## Read one returned detail

Prefer a specific `detail_refs` reference when only one component's detail is
needed. Submit that exact reference with the response's unchanged `reentry`, or
use the [API reference helper](../architecture/shared-rust-core.md#inputs-and-results).
Do not guess a reference from a component name. Answer a question only with its
requested answer shape; selecting detail is not an instruction to run an effect.

References depend on the original work and relevant sources. If either changes,
resolve the current task again instead of altering an old reference. Losing
`carriage` also requires fresh resolution; it is transport data, not a durable
task record or a transferable permission. Only its `view` belongs in model
context; the host retains and submits the exact `carriage` through the supported
helpers.

## Avoid repeating source prose

A continuing caller can return already-held `delivery_refs` through `--delivered`
(API field `delivered`). This can suppress unchanged source prose after current
source checks. It does not suppress requirements or establish that the consumer
understood or followed the source. Clear caller-held delivery information after
context loss so needed material can be supplied again.

## Maintain the contract

The current projection and delivery rules come from `operating_projections` in
the [source decision contract](../../src/core/contracts/source_decision_contract.json).
Use the [CLI catalogue](../reference/cli-catalogue.md) for flags and the
[API guide](../architecture/shared-rust-core.md) for exact transport helpers.

When changing response construction, preserve required decision fields, exact
actions and source checks while keeping unrelated detail deferred. Existing
[frontier tests](../../tests/test_native_frontier.py) check detail expansion,
source changes and disposable carriage; [carriage tests](../../tests/test_native_operating_carriage.py)
cover answer transport, rejection and delivery limits. Extend the relevant case
only when the changed behaviour needs coverage it does not already provide.
