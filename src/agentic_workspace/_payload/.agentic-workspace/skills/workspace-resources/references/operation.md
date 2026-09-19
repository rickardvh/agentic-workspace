# Propose and carry an exact resource operation

Use the exact current resource proposal request:

```agentic-owner-reference
{"kind":"request","owner":"workspace-resources","id":"resources/propose/v1"}
```

Supply fresh intent in its `arguments.request`, such as
`{"operation":"scratch-create"}`, through the shared startup request carriage.
This observes and proposes only. Resolve the resulting exact action identity,
for example `workspace.resources.scratch-create`, then invoke only its current
returned reference/envelope. Selection never executes; proposals reject an
`expected_revision` supplied as an attempt to execute during start.

The configured `resources --target <repo> --task <task> --input <request.json>`
primitive and Python/TypeScript/JSON resources entrypoints remain directly useful
without a skill. They use the same native owner and fresh intent shape.
For isolation, supply the concrete `need`, `reason`, returned `policy_revision`
and `policy_answer: permits-isolation` only when current instructions permit it.
Missing judgment, stale policy or protection yields rather than executing.

On the direct primitive path, when the owner returns an `action`, carry that
exact object to the same resources primitive. It already contains target, task, changed paths, selected resource and
current revision; do not rebuild it or choose an arbitrary action from other work.
The native owner reobserves policy, path identity, retention and custody before
effects. Inspect `effect_outcome` and the returned path/build environment.

Unresolved route-scoped protection returns exact `route_requests`. Answer only
the requested semantic applicability and carry it as `route_request`. A selected
skill name or policy hash is not scope admission. A current negative is settled;
missing or stale scope is not. Declared path and route scope remain conjunctive.

Retain target/task/changed/path and current route carriage in disposable caller
context. These are reentry inputs, not authority or a durable skill cursor.
