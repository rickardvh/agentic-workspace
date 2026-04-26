# Local-Only Memory

`.agentic-workspace/local/memory.toml` is the default local-only memory path for repo-scoped, machine-local continuity notes.

The surface is disabled unless `.agentic-workspace/config.local.toml` opts in:

```toml
schema_version = 1

[local_memory]
enabled = true
path = ".agentic-workspace/local/memory.toml"
```

Local-only memory is advisory. It may help another agent on the same machine recover environment-specific, private, experimental, or low-confidence context, but it must not override checked-in Memory, Planning, config, docs, or user instructions.

Do not store secrets, credentials, tokens, or private data that should be managed by a secret store.

Use a compact record shape:

```toml
[[items]]
id = "short-id"
summary = "One useful local fact."
scope = "repo-local"
source = "manual"
confidence = "low"
promotion_candidate = false
```

Promote an item manually into checked-in Memory only when it is durable, shareable, non-private, and useful beyond this machine.
