# Cold-start procedure

Read the repository's instructions, then the configured workspace-startup skill. Keep direct work direct; do not load domain state simply because it exists.

When current owner facts or effects matter, use:

```sh
agentic-workspace start --target . --task "<task>" --format json
```

Add repeated `--changed` arguments for known paths. Follow exact returned detail references or requests with the same work context. Use `invoke` only for an exact owner-returned action. No other command family is needed for startup recovery.

If native execution is unavailable, follow the startup skill's repository-readable boundary. Recorded state does not establish live capabilities or effect admission.
