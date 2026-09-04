# Module API

A module entry point in the `agentic_workspace.modules` group returns an
`agentic_workspace.Module`:

```python
Module(name="example", contribute=contribute, operations=(operation,))
```

`contribute(context)` returns one normalized source contribution or `None` when
irrelevant. Operations are declared with `Operation(operation_id, input_schema,
effects, handler)`. The core has no module-name switch: built-in and out-of-tree
providers are discovered, reduced, registered, and dispatched through the same
functions.

Removing an entry point removes its facts and operations without a core edit.
