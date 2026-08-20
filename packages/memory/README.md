# Agentic Memory

Agentic Memory is the Agentic Workspace module for durable anti-rediscovery repository knowledge: compact facts that are expensive to reconstruct and useful across agents, sessions, contributors, or branches.

It is one peer capability in the generic `resolve -> act -> reconcile` loop. Memory is not AW's persistence layer, a repository knowledge database, active execution state, broad canonical documentation, or a required part of ordinary work.

Use the root `agentic-workspace` CLI for normal host-repo lifecycle and routing. The `agentic-memory` CLI is the explicit module maintenance/debugging surface.

Support-bearing installs use the exact root-wheel command projected from a versioned release's `distribution-install-readiness.json`; mutable branches and source-checkout commands are not supported install identities. See the root [installation guide](../../docs/agentic-workspace-install.md).

## Domain boundary

Memory owns routed durable lessons, subsystem orientation, invariants, recurring traps, and runbooks under its declared repository root. A note should exist only when reading it is cheaper than rediscovering the fact from canonical source/docs/tests.

Memory does not own:

- active task sequencing, milestones, or backlog;
- proof, completion, or mutation authority;
- raw session or execution logs;
- duplicated canonical product/source documentation;
- general ingestion, indexing, embeddings, RAG, or a knowledge graph.

Richer retrieval can be another module without changing Memory's boundary or the Workspace loop.

## Ordinary participation

- **Resolve:** route only a relevant durable note or Memory-owned procedure when it can change the current decision.
- **Act:** expose bounded capture, routing, and hygiene operations.
- **Reconcile:** retain genuinely future-relevant anti-rediscovery residue or explicitly retain nothing.

When Memory is irrelevant, it should be absent from first-line context. One fact should have one durable primary owner; Memory should compress and point instead of copying canonical docs.

The ordinary host route is:

```bash
agentic-workspace start --target . --task "<task>" --format json
```

Follow a Memory selector, skill, or operation only when that current contract routes there. Use the generated [current CLI catalogue](../../docs/reference/cli-catalogue.md) for exact flags.

## Installed shape

The stable module root is `.agentic-workspace/memory/`. Its repo-owned note tree conventionally separates:

- `repo/index.md` and `repo/manifest.toml` for routing and metadata;
- `repo/domains/` for orientation;
- `repo/invariants/` for durable boundaries;
- `repo/runbooks/` for repeatable procedures;
- `repo/decisions/` for longer-lived rationale;
- `skills/` for package-managed Memory procedures.

Exact host footprint and ownership come from the generated [installed-surface catalogue](../../docs/reference/installed-surface-catalogue.md), not a hand-maintained payload table here.

## Deeper maintenance

- `AGENTS.md` in this package owns contributor routing.
- `bootstrap/README.md` explains bootstrap payload development.
- `skills/README.md` owns packaged Memory skill discovery.
- Source-checkout tests and checks live under `packages/memory/tests` and `packages/memory/scripts`.

Public maturity: **alpha**, matching coordinated package metadata. Strong capability evidence does not independently promote the distribution support contract.
