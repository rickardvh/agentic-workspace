# Module Capability Contract

Agentic Workspace modules are peer capability contributors to the existing operating decision. A module describes its domain; Workspace owns `resolve -> act -> reconcile`.

The versioned public contract is `agentic-workspace/module-capability/v2`, registered through the Python entry-point group `agentic_workspace.modules`. An entry point returns either the contract object directly or `{ "contract": ..., "operations": ... }`.

## Author-facing shape

A module declares five things:

1. `name`, `description`, and `compatibility`: stable identity plus the reader epoch and required generic capabilities.
2. `ownership`: module-owned roots and effect classes, plus explicit authority the module cannot acquire.
3. `relevance`: bounded task terms and path prefixes that decide whether the contribution belongs in the current contract.
4. `facts`: optional typed, source-owned, revision/currentness-bound values that existing instruction clauses may reference. Modules define values, not predicate or effect operators.
5. `capabilities`: optional `resources`, `skills`, and typed `operations`. Omit dimensions the module does not use.
6. `result_semantics`: the result schema, guaranteed fields, effect fields, and warning fields the kernel may reconcile.

Dependencies, conflicts, and selection rank are optional. Unknown additive metadata is allowed. Unknown required capabilities and newer reader epochs fail closed.

```python
def module_provider():
    return {
        "contract": {
            "schema_version": "agentic-workspace/module-capability/v2",
            "name": "signals",
            "description": "Read bounded build signals.",
            "compatibility": {
                "reader_epoch": 1,
                "required_capabilities": ["module-resources-v1", "module-facts-v1"],
            },
            "ownership": {
                "roots": [],
                "effect_classes": [],
                "authority_exclusions": [
                    "cannot grant mutation, proof, or completion authority"
                ],
            },
            "relevance": {
                "task_terms": ["build signal"],
                "path_prefixes": ["build/signals/"],
            },
            "facts": [
                {
                    "id": "signals.build-risk",
                    "type": "string",
                    "value": "elevated",
                    "source": {
                        "owner": "signals",
                        "revision": "signal-r1",
                        "current": True,
                    },
                }
            ],
            "capabilities": {
                "resources": [
                    {
                        "id": "signals.latest",
                        "ref": "signals://latest",
                        "read_only": True,
                    }
                ]
            },
            "result_semantics": {
                "schema_version": "signals/result/v1",
                "guaranteed_fields": ["status"],
                "effect_fields": [],
                "warning_fields": ["warnings"],
            },
        }
    }
```

```toml
[project.entry-points."agentic_workspace.modules"]
signals = "signals_module:module_provider"
```

This read-only module declares no operations, workflow phases, posture fragments, closeout hooks, or lifecycle callbacks. The kernel supplies quiet lifecycle defaults.

## Admission and composition

Workspace validates identity and compatibility before using a contribution. Selected modules with malformed contracts, unsupported required capabilities, missing dependencies, explicit conflicts, overlapping owned roots, or colliding effect classes fail with the competing owners and a repository-configuration recovery owner.

Only enabled, installed, compatible, and relevant modules contribute to the current operating decision. Irrelevant modules and their facts remain absent from first-line context. A contribution may provide facts or route resources, skills, or operations, but its authority remains bounded by `ownership.authority_exclusions`.

Fact ids and types are stable contract declarations. Each value names the module owner plus a non-empty revision and explicit currentness bit. Workspace admits these values directly into the existing instruction IR; it does not persist them in a central fact store. A repo-owned bounded clause may consume a current fact, while stale revisions evaluate as unknown. The ordinary start and implement compilers merge that existing source-owned program with relevant module facts before compiling the operating decision.

A contract with one or more facts must include `module-facts-v1` in `compatibility.required_capabilities`. This makes readers that do not support facts reject the module instead of accepting it while silently ignoring source-owned facts.

When a module operation includes `facts`, the list is the module owner's reconciled current snapshot: values may refresh declared ids and types, and an empty list removes the facts from the next contribution. Before accepting that result, Workspace reloads the module's public contract provider and requires its facts to match the reported snapshot. The previously discovered contract remains immutable; a fresh discovery therefore observes the new revision, stale marker, or removal without relying on process-local Workspace mutation. An operation result that omits `facts` leaves the module owner's current snapshot unchanged.

Typed operations are invoked through the generic module-operation boundary. Results must contain their guaranteed fields and may report only declared effect classes. Module-local success cannot set unrelated mutation, proof, parent-intent, or completion authority.

Removing a module means deselecting its capability contract. Repo-owned promoted outputs remain under their existing owners; no cached module contribution remains authoritative after a fresh resolution.

## Internal compatibility metadata

The root package still carries broader first-party lifecycle and distribution metadata in `module_registry.json`. That metadata is an internal compatibility surface, not the public authoring API. Planning, Memory, and Verification publish the same capability-first contract used by external modules where their semantics overlap.
