# Verification Routing Note

Verification is the Agentic Workspace module for reusable soft verification
protocols, proof-route hints, bounded evidence records, and known gaps.

Canonical owner: [packages/verification/README.md](../packages/verification/README.md).

Use this top-level page only as a stable public link target from generated
contracts, tests, and historical plans. Do not expand it into a second
Verification manual.

Ordinary surfaces:

```text
agentic-verification report --target . --format json
agentic-workspace report --section verification --format json
agentic-workspace proof --changed <paths> --verbose --format json
agentic-workspace implement --select verification --changed <paths> --format json
```

The module implementation lives in `packages/verification/`. Host-repo protocol
and evidence state lives under `.agentic-workspace/verification/` when enabled.
