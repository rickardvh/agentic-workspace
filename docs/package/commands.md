# Use the CLI

The `agentic-workspace` command lets an agent or a program inspect repository
context and request controlled changes. For ordinary use through a coding agent,
see [Everyday use](../everyday-use.md); you do not need to run these commands around
every edit.

## Inspect the repository

Run this from the repository where the work will happen:

```bash
agentic-workspace start --target . --task "Inspect this repository" --format json
```

The result describes applicable context, restrictions and available requests.
It does not perform the programming task. An unadopted repository can offer a
request to add AW; follow [Getting started](../agentic-workspace-install.md) for
that first-use path.

For a concrete change, supply its actual task and known affected paths. Paths are
relative to the target repository; replace the example with a path in your project:

```bash
agentic-workspace start --target . --task "Change the users API" \
  --changed src/api/users.rs --format json
```

Repeat `--changed` for additional paths. Start with the default compact result.
Use a returned reference for specific detail; `--projection full` is useful when
you deliberately need the expanded response, for example while debugging an
integration. Neither option changes permission to act.

## Submit a request, then perform an authorised change

A *request* asks the component responsible for a concern to interpret supplied
material. An *action* is the exact operation that component has prepared. They
are different inputs.

Save the returned request in `request.json`, filling only the fields it asks you
to supply. Submit it using the same target, task and changed paths:

```bash
agentic-workspace start --target . --task "Change the users API" \
  --changed src/api/users.rs --input request.json --format json
```

The response may ask a question, identify a restriction or offer an action.
After the required authorisation, save the exact returned action in `action.json`:

```bash
agentic-workspace invoke --target . --task "Change the users API" \
  --changed src/api/users.rs --input action.json --format json
```

Do not construct an action from its operation name or replace its target and
arguments. AW checks its dependencies again when it executes. Store temporary
transport files in an appropriate local scratch location, not as shared project
policy.

Inspect the effect result before continuing. If a write succeeded but the next
query failed, recover or refresh the query; do not repeat the write. An uncertain
effect needs the returned recovery path, not a blind retry.

## Other tools

| Command | Use |
| --- | --- |
| `resources` | Inspect or manage task resources using a current resource request. |
| `worker` | Read an assigned work packet, expand its inputs or assemble its return. |

These tools consume the requests provided by the corresponding resource or
assignment operation. They are not necessary for an ordinary context query.

Run `agentic-workspace --help` and the relevant command's `--help` for options.
The generated [CLI catalogue](../reference/cli-catalogue.md) is the complete
source reference. Older command names in historical reports are not fallbacks for
a rejected current request.
