# Agentic Verification

Agentic Verification is the Agentic Workspace module for reusable soft
verification protocols and bounded evidence records. It owns the
`.agentic-workspace/verification/manifest.toml` contract and the projection that
turns configured protocols, scenarios, proof routes, evidence bundles, and known
gaps into agent-facing report data.

Use the root `agentic-workspace` CLI for ordinary host-repo workflow. The
`agentic-verification` CLI is the module-level maintenance and debugging
surface.

Verification owns:

- repeatable verification protocol declarations;
- scenario and proof-route metadata;
- bounded evidence bundle records;
- transcript retention and summary-first policy;
- known verification gaps and residual-risk labels.

Verification does not own Planning state, Assurance requirements, Proof
authority, Closeout claim decisions, Memory, CI, or raw transcript storage.

## Module CLI

```text
agentic-verification report --target ./repo --format json
```

The AW package root exposes the same module projection through:

```text
agentic-workspace report --section verification --format json
agentic-workspace implement --select verification --changed <paths> --format json
agentic-workspace proof --changed <paths> --verbose --format json
```
