# Use the CLI

The `agentic-workspace` command lets an agent or a program inspect repository
context and request controlled changes. For ordinary use through a coding agent,
see [Everyday use](../everyday-use.md); you do not need to run these commands around
every edit.

First [install AW](../agentic-workspace-install.md#1-install-aw). The examples
below assume `agentic-workspace` is available on PATH in the environment running
them. For repository-local npm, replace that prefix with
`npm exec --no -- agentic-workspace`; for a custom installation, use its executable
path. Keep using the same installation for follow-up calls.

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

## Answer a returned question

A *request* asks the responsible component to interpret supplied material.
An *action* is an exact operation it has prepared. A compact question gives a
`reference`, an `answer_shape` and, where supplied, an answer schema.
Submit the requested semantic answer with the response's unchanged `reentry`.
Do not put the displayed question or its `next_step` object into `request`.

The following example applies **only when the current setup question offers**
`assess-setup` for `instructions`. It selects an assessment, not permission to
write files. Other questions require their own returned answer shape.

Save the complete compact response as `response.json` in local task scratch.
Using Python, create the next input without rebuilding its opaque fields:

```python
import json
from pathlib import Path

response = json.loads(Path("response.json").read_text(encoding="utf-8"))
step = response["setup_context"]["next_step"]
answer = {"job": "assess-setup", "concern": "instructions"}
followup = {**response["reentry"], "reference": step["reference"], "answer": answer}
Path("request.json").write_text(json.dumps(followup), encoding="utf-8")
```

Run the following using the same AW installation:

```sh
agentic-workspace start --input request.json --format json > answered.json
```

The input carries the original target, task, changed paths and earlier answers.
Do not add conflicting context flags. Inspect `answered.json`; the assessment
can return another question or a restriction rather than an action. Continue
with that response's current `reentry` and requested answer only when needed.

An exact public request from expanded output can also be submitted with
`--input` and the original context flags. The compact question workflow above
avoids reconstructing that request from its name.

## Perform an authorised change

When a later response offers the intended action and its required authorisation
is established, save that complete response as `ready.json`. Build the invocation
input from its work context and exact action:

```python
import json
from pathlib import Path

ready = json.loads(Path("ready.json").read_text(encoding="utf-8"))
action = ready["decision_packet"].get("primary_action")
if action is None:
    raise SystemExit("No primary action: inspect the current question or restriction.")
context = ready["reentry"]
invocation = {
    "target": context["target"],
    "task": context["task"],
    "changed": context.get("changed", []),
    "invocation": action,
}
Path("action.json").write_text(json.dumps(invocation), encoding="utf-8")
```

```sh
agentic-workspace invoke --input action.json --format json
```

An offered action is not an instruction to execute every available operation.
Do not alter its target or arguments, or copy an earlier `request` into the
invocation envelope. AW checks relevant sources and permissions again.

Inspect `effect_outcome.status` separately from the continuation:

| Status | Next step |
| --- | --- |
| `committed` | Preserve the confirmed effect. A failed continuation does not justify repeating it. |
| `rejected-before-effect` | Resolve the reported rejection; the operation did not perform its effect. |
| `uncertain` | Use the supplied recovery to establish what happened before retrying. |

Keep temporary transport files out of shared project policy. The
[API guide](../architecture/shared-rust-core.md#continue-from-a-returned-question)
shows the corresponding in-memory helper.

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
