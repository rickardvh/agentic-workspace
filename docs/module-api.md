# Module API

A module entry point in the `agentic_workspace.modules` group returns an
`agentic_workspace.Module`:

```python
Module(
    name="example",
    api_version="1.0",
    required_capabilities=("contribution/decisions", "operation/durable-commit"),
    owns=("example-state",),
    contribute=contribute,
    resources=({"id": "guide", "revision": "g1", "locator": "docs/guide.md"},),
    procedures=({"id": "review", "revision": "p1", "locator": "tools/review.md"},),
    operations=(operation,),
)
```

`contribute(context)` returns one normalized source contribution or `None` when
irrelevant. Operations are declared with `Operation(operation_id, input_schema,
effects, handler)`. The core has no module-name switch: built-in and out-of-tree
providers are discovered, reduced, registered, and dispatched through the same
functions.

Contribution dimensions are optional. Read-only modules need no operation;
operation modules need no procedure. Resources and procedures are progressively
routed references with stable owner/revision/locator identity. A procedure is
always `reference-only`: selecting it cannot mutate state, satisfy proof, or
widen claims.

A module may contribute `decisions` for irreducible human/domain judgment. Each
request declares an ID, question, authority, source revision, finite choices or
an open-judgment allowance, and a response operation owned by that module. The
answer is not free-form recovery prose: `invoke` checks its owner, revision,
authority, choice boundary, currentness, and typed response operation.

Admission rejects incompatible API majors, duplicate module identities, and
owned-domain conflicts before a contribution can affect a decision. Supported
additive 1.x capabilities are admitted; unsupported required semantics fail
closed with an upgrade route. Removing an
entry point removes its facts, resources, procedures, and operations without a
core edit. Python entry-point discovery and TypeScript host registration are
explicit platform primitives; both normalize into the generated semantic
contract in `contracts/semantic-ir.json`.

Effectful operations participate in the shared durable commit protocol. An
external handler that cannot reconstruct an interrupted effect must omit a
recovery callback; retry then blocks at that owner instead of repeating the
effect. Managed state paths require acquired ownership and canonical confinement,
including for independent modules.
