# Installed Surfaces

An installed host repository gets a small set of checked-in surfaces. Their purpose is to make startup, ownership, active work, durable knowledge, and verification discoverable from repository state.

## Root Surfaces

| Surface | Owner | Purpose |
| --- | --- | --- |
| `AGENTS.md` | repo-owned adapter with managed fences | first file an agent can read; routes to compact workspace commands |
| `llms.txt` | generated adapter | compatibility handoff for tools that look for `llms.txt` |
| `.agentic-workspace/` | product-managed enclave | shared workspace configuration, contracts, module roots, and local boundaries |
| `.agentic-workspace/config.toml` | repo-owned config | selected modules, posture, workflow obligations, and repo-specific settings |
| `.agentic-workspace/OWNERSHIP.toml` | repo-owned ledger | managed paths, fences, and authority metadata |
| `.agentic-workspace/WORKFLOW.md` | product-managed workflow adapter | short shared workflow rules for the installed workspace |
| `.agentic-workspace/local/` | local-only ignored area | machine-local overrides, caches, and non-shared runtime aids |

The package keeps `AGENTS.md` thin. Durable rules and structured state live under `.agentic-workspace/` or in repo-owned docs, not in a growing startup manual.

## Planning Surfaces

Planning adds active execution state:

| Surface | Purpose |
| --- | --- |
| `.agentic-workspace/planning/state.toml` | active items, roadmap lanes, and current planning state |
| `.agentic-workspace/planning/execplans/` | bounded execution plans and archives |
| `.agentic-workspace/planning/agent-manifest.json` | module-managed manifest for generated agent aids |
| `.agentic-workspace/planning/schemas/` | planning-specific schema contracts |

Raw planning files are opened only when `summary`, `preflight`, or another compact route points there.

## Memory Surfaces

Memory adds durable anti-rediscovery knowledge:

| Surface | Purpose |
| --- | --- |
| `.agentic-workspace/memory/repo/index.md` | route-indexed memory entrypoint |
| `.agentic-workspace/memory/repo/manifest.toml` | machine-readable memory note metadata |
| `.agentic-workspace/memory/repo/domains/` | subsystem orientation |
| `.agentic-workspace/memory/repo/invariants/` | contracts and authority boundaries |
| `.agentic-workspace/memory/repo/runbooks/` | repeatable operator procedures |
| `.agentic-workspace/memory/repo/decisions/` | longer-lived rationale |
| `.agentic-workspace/memory/skills/` | package-managed memory skills |

Memory should reduce rediscovery cost. It is not a task tracker, execution log, or broad product documentation replacement.

## Ownership Rule

The stable rule is one owner per concern:

- active execution state belongs in Planning;
- durable repo knowledge belongs in Memory or canonical docs;
- package-managed installed contracts live under `.agentic-workspace/`;
- repo-owned startup and documentation stay outside managed areas unless they use explicit managed fences;
- local-only runtime residue stays under `.agentic-workspace/local/`.

For exact ownership and path metadata, use:

```bash
agentic-workspace ownership --target ./repo --format json
```
