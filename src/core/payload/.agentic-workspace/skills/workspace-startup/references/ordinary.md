## Ordinary use

Use this reference when the next action needs current AW facts. If the task can
be completed from sufficient current sources already available, continue directly.
For example, explaining supplied text needs no startup command; resolving whether
a protected write may proceed needs the current result for that write.

Use native resolution when current owner state can affect the work or a dependent
action or claim. If current static sources suffice without a dynamic dependency,
work directly. Context entry requires that judgment, not an unconditional call.
Reuse a current observation; resolve again when relevant dependencies change or
required current facts are unavailable. Use the configured invocation: local `workspace.cli_invoke`, then shared
`workspace.cli_invoke`, otherwise `agentic-workspace`. Pass the actual task to
`start`; this is the agent's machine interface, not a command the human must run
around each edit. Repository-local npm uses `npm exec --no -- agentic-workspace`.
For a source checkout, follow the existing [source preparation boundary](../../workspace-setup-jumpstart/references/boundaries.md)
before first native use and after changing bundled or Rust sources.
Read the `workspace.cli_invoke` value in `.agentic-workspace/config.local.toml`
or `.agentic-workspace/config.toml` when not already available. The key names a
configuration value, not an executable called `workspace.cli_invoke`. Append
`start --target . --task "<actual task>"` to that invocation; task text is not a
positional argument. A missing PATH command does not make a configured local
executable unavailable.

Plain shell/tool callers use the default compact output. It includes the selected
exact request/action and required material; follow a returned `detail_refs`
reference only for missing useful detail. Do not request full projection merely
to find an owner key. Use [exact owner carriage](owners.md) when a caller can keep
structured transport outside model output; otherwise compact needs no scratch.
Consume a current invocation continuation directly. Changed work or unavailable
continuation requires explicit fresh resolution or the owner's recovery path.

Follow a surfaced setup assessment even when the task is unrelated. It supplies
current installed guidance when repository copies are old or missing. Refresh
changed package bytes through Configuration; assess capabilities only when due.
Unchanged deferred choices need no repeated question. Revisit them only when their
prerequisite changes, dependent work needs them, or the human asks.
Read each consequence's affected action or claim. An unresolved integration
assessment does not by itself block unrelated task work or its completion;
preserve the integration gap separately. A setup dry run checks package bytes,
not semantic assessment, and cannot discharge that assessment.

After setup, do the task directly. Read extra evidence only when it could change
the work or a required claim; see [evidence sufficiency](evidence.md). Use returned
requests and actions for managed changes, following [owner carriage](owners.md).
A successful effect does not prove the whole task complete. Preserve only useful
continuation or knowledge through [reconciliation](reconcile.md).

## Responsibility split

Repository instructions and configuration set policy. Skills supply procedure.
Domain owners hold current state, evidence and effects. Rust is the deterministic
authority; language bindings carry its requests. The agent judges relevance and
does the work. A skill or route never grants mutation, proof or completion rights.

## Current material and needs

Supply a new finding or missing prerequisite in the same `start` context,
separately from `task`. The `material` field tells AW what changed and where the
observation came from; it does not make the finding a policy or prove a claim.
For the CLI, write a context object to a UTF-8 JSON file and pass `start --input`:

```json
{
  "target": ".",
  "task": "The unchanged current task",
  "material": [{
    "id": "test-prerequisite",
    "kind": "need",
    "summary": "The upcoming test requires current service readiness.",
    "source": {"producer": "acting-agent", "reference": "current test requirement", "coverage": "bounded"}
  }]
}
```

Use `observation` for a material fact, correction, tool result or external/module
observation; use `need` before an action whose prerequisite remains unmet. Include
exact source revisions and repository dependency reference/revision pairs when
known. Labels remain assertions, never human authority or proof. Carry returned
work-bound material explicitly on reentry; there is no event store.

Read `activation` for procedures that may help handle this finding. Read the
restrictions in the same result before taking an affected action. When a returned
request asks whether a procedure applies, answer only that unresolved question with
`applicable`, `unknown`, `defer`, `no-match` or justified `no-retention` and a reason.
Keep earlier answers when selecting another method. Use the returned entry to
read the selected procedure, or follow the exact component request directly.
Reading a skill does not complete its task. Verify the changed source and its
effect on the affected action, distinguish
stable knowledge from transient availability, and preserve an explicit gap when
the current owner or required host capability is unavailable.

## Specialised skills and semantic routes

Select a known useful leaf directly, or inspect one relevant route branch. Follow
its returned procedure reference; do not load every skill or rediscover module
topology. Exact paths and owner facts take precedence over lexical hints. A changed
task or route source can require fresh discovery. Missing carriage grants no
authority, and an optional skill cannot waive current owner restrictions.

Repository and package skills use the same mechanism. Keep current policy and
mutable owner state in their own sources, not copied into procedure.
