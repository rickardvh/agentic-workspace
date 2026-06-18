# Maturity Model

Last reviewed: 2026-06-18.

This page owns support and adoption-readiness labels. It does not own the
package overview, module map, roadmap, or capability taxonomy.

Route current behavior to [Package overview](package/overview.md) and
[Modules](package/modules.md). Route long-horizon capability framing to
[Agent OS capabilities](agent-os-capabilities.md) and ecosystem sequencing to
[Ecosystem roadmap](ecosystem-roadmap.md).

## Labels

`alpha` means the contract is real and dogfooded, but naming, schema shape, or
guidance may still change noticeably.

`beta` means the contract is broadly usable for early adopters, selective
adoption works, and future change should mostly refine the surface.

## Current Status

| Surface | Current maturity | Meaning here |
| --- | --- | --- |
| `agentic-workspace` root package | beta | public orchestration entrypoint for lifecycle, startup, reports, proof selection, module composition, and release-managed installed surfaces |
| Agentic Planning | beta | active execution state, decomposition, handoff, and honest closeout are usable and should evolve incrementally |
| Agentic Memory | beta | durable repo-memory and routing contracts are usable and should evolve incrementally |
| Agentic Verification | alpha | protocol, proof-route, evidence, and assurance projections are real and dogfooded, but the module is still finding the right level of diagnostic support |
| Generated Python and TypeScript CLIs | alpha | both targets are shipped and should remain supported, but release and parity workflows are still maturing |

Refresh this page when a shipped surface changes maturity, support promises
change, or recent dogfooding materially changes the reason for a label.
