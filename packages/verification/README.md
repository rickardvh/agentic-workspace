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

In the open Workspace participation model, Verification contributes proof-step
resources, report data, protocols, bounded evidence records, proof-route hints,
known gaps, schemas, and owned roots. It is a first-party example of module
participation in the proof step; it should not become the generic proof
authority or a required slot for every repo.

Verification contributes task posture only when assurance requirements, changed
paths, proof selection, or known-gap reporting activate verification protocols;
it may add review rubrics and authority boundaries, but completion permission
stays with the owning workflow.

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
