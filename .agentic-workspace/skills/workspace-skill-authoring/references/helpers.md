# Declare a helper only when computation helps

When an existing deterministic script reduces repeated computation, keep it as an
ordinary file in the repository-owned bundle. Document its inputs, result,
required runtime/version, dependencies, execution limits and any writes before
the step that runs it. Prefer the ordinary Markdown method when a helper adds
setup without useful savings.

The existing registry entry may add `executable` using the shipped
[executable-affordance v1 schema](executable.schema.json). For example:

```json
{"entrypoint":{"kind":"file","path":"tools/skills/change-note/scripts/inspect.py"},"dependencies":["tools/skills/change-note/rules.json"]}
```

Unlike procedure links, these paths are repository-relative. List exact material
files actually required; do not include optional examples or an entire directory.
The combined entrypoint/dependency set is limited to 32 files. A `native` entrypoint
may reference an existing AW command and an optional `required_capability`; it
cannot register a new command or turn a host script into a native operation.

Resolve the same selected route as in [structured skills](structured.md). Inspect
`sources[].procedure.executable`: `entrypoint`, `dependencies` and their revisions
identify the declared material. Missing files give `material_status: unavailable`.
For an external script, runtime status remains unknown and overall executable
status unavailable. This does not mean the declaration is malformed; AW discovery
does not test Python, Node or other external runtimes and does not execute helpers.

Check the required runtime at the host boundary, then use the repository's normal
authorised command execution. AW supplies no extra sandbox or execution permission.
Inspect the result and any actual write before claiming success. The helper may
compute facts; it cannot manufacture another component's owner action, policy,
approval or proof receipt. Use that component's exact current operation for a
dependent effect. Reobserve selected detail when declared material changes.
Stop when the requested computation is usable, or name the unavailable runtime
or dependency and keep the Markdown path available where it still suffices.
