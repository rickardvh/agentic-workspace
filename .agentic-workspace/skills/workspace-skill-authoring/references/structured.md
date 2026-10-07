# Select branches with current facts

Use this addition when a method has substantial alternatives and selecting one
resource avoids repeatedly reading them all. Keep the same repository-owned
bundle. In `procedure.md`, write one `agentic-procedure` fenced JSON object using
the shipped [procedure v1 schema](procedure.schema.json):

```agentic-procedure
{"kind":"agentic-workspace/procedure/v1","id":"visibility","question":"Does the observed change alter behaviour visible to a user?","branches":[{"id":"visible","description":"Public behaviour changes","next":"user-note.md"},{"id":"internal","description":"Public behaviour is preserved","next":"internal-note.md"}]}
```

Create the two named Markdown resources in the bundle. `procedure_resource` is
relative to `SKILL.md`; `next` and optional `context` paths are relative to the
procedure file. Use confined relative paths without `..`, absolute paths or
symlinks. The native reader limits each resource to 64 KiB, the question and each
description to 8192 UTF-8 bytes, and branches/context entries to 32 each. Branch
IDs must be unique. Required context files are read with the question; alternative
branch text is read only when selected.

If AW discovery or carried answers help this method, declare it in the existing
repository registry, for example `tools/skills/REGISTRY.json`:

```json
{"schema_version":"skill-registry.v1","skills":[{"id":"change-note","path":"change-note/SKILL.md","semantic_routes":["notes/change"],"procedure_resource":"procedure.md"}]}
```

Merge the entry into an existing registry instead of replacing unrelated entries.
For another repository-owned tree, declare its repository-relative registry in
`registry_sources` of that existing registry. AW reads declared sources, not every
file named `REGISTRY.json`. No core switch or package-managed copy is needed.

Use the configured AW invocation with `start --target . --task "Draft a change note" --projection full`.
From `semantic_routes.requests`, choose the returned
request whose `request_kind` is `semantic-routes/discover/v1`. Set only its
`arguments.parent` to `notes/change`, save that complete request as
`request.json`, and run the same command with `--input request.json`.
Keep the same task and target: the request belongs to that work.

The selected `semantic_routes.discovery.detail.sources[].procedure.resource`
must report `status: current`, the question, branches and source revision.
Missing or malformed resources report `unavailable` with a reason: repair the
owning source and reobserve. To read one branch, add `arguments.resource` to the
same discovery request, using the returned qualified identities and branch path:

```json
{"source_ref":"tools/skills/REGISTRY.json","skill_id":"change-note","resource":"tools/skills/change-note/user-note.md"}
```

Run `start` with that complete request. The resource's `selected.text` and revision
identify the actual resource. An
undeclared path remains unavailable. Retain `source_ref` and `skill_id` when names
collide; [maintenance](maintain.md) explains replacement.

For semantic answers needed across steps, discover this same leaf through the
current `semantic-routes/discover/v1` request returned by `start`, then answer its
`procedure/select/v1` and `procedure/answer/v1` requests through
[exact owner carriage](../../workspace-startup/references/owners.md). Supply only
the requested judgement: `disposition`, a reason in advisory `material`, `branches` when
`answered`, and exact repository file `evidence` references/revisions when the
answer relies on those files. `unknown`, `defer`, `no-match` and `conflict` select no
branch. Preserve the returned request for reuse; a changed procedure or relied-on
file makes the answer stale and requires reconsideration. Lost carriage is not
a recovered answer. Never turn a convenient branch into a fact.

If a step needs Configuration, Planning, Verification or another AW component to
act, link its current supported owner-reference procedure and consume its exact
returned request or action. Do not copy its changing policy, evidence, state or
approval into skill prose or semantic answers. A branch cannot replace that
component's authority.

Optional `activation` metadata helps nominate a method from current observations;
it is unnecessary for direct selection. When used, regenerate the existing index
with `activation-index --target . --input request.json`, supplying
`{"registry":"tools/skills/REGISTRY.json","mode":"write"}`; use `check` to check
parity and `render` to inspect it. Commit generated metadata with its source.
Finish after selected resources resolve and a relevant source change invalidates
the answer that depended on it. Reuse existing route/currentness checks rather
than adding a workflow runtime to the skill.
