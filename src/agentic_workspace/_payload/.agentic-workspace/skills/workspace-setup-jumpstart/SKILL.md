---
name: workspace-setup-jumpstart
description: Route newly installed or adopted Agentic Workspace in a lived-in repo through bounded setup and jumpstart discovery before seeding durable surfaces.
---

# Workspace Setup Jumpstart

Use this skill when Agentic Workspace was newly installed or adopted in a lived-in or mature repo and the task is to populate, seed, or orient workspace surfaces after bootstrap.

## Route

1. Run `agentic-workspace start --target . --task "<task>" --format json`.
2. Run `agentic-workspace setup --target . --format json` for bounded post-bootstrap setup guidance.
3. Treat setup as pre-write and pre-seed discovery. Do not bulk-import docs, backlog, or prose.
4. Inspect only surfaces named by setup output, by the task, or by a durable mature-repo jumpstart memory note.
5. Promote only:
   - durable operating knowledge to Memory;
   - bounded follow-up to Planning;
   - evidence-backed friction to repo-friction or improvement intake;
   - low-confidence or generic findings to transient report only.
6. Before writing seed surfaces, check promotion criteria in `docs/setup-findings-contract.md` and the durable candidate rule in `docs/jumpstart-contract.md`.

## Required Seed Surfaces

When the task is to populate durable workspace surfaces after bootstrap, handle these files explicitly:

- `.agentic-workspace/OWNERSHIP.toml`: keep package-managed module roots, managed surfaces, fences, and authority surfaces generic; add host-specific `[[subsystems]]` only from inspected repo structure, test commands, ownership boundaries, or clear user direction. Do not copy subsystem entries from the Agentic Workspace source repo into a host repo.
- `.agentic-workspace/system-intent/intent.toml`: run `agentic-workspace system-intent --target . --sync --format json` first, then refine only reviewable interpreted fields that are supported by named repo intent sources such as `README.md`, `SYSTEM_INTENT.md`, product docs, or explicit user direction. Do not mechanically summarize every source file.
- `.agentic-workspace/system-intent/subsystems.toml`: add scoped durable intent only for subsystem ids already declared in `.agentic-workspace/OWNERSHIP.toml [[subsystems]]`. Leave `subsystems = []` when no host subsystem boundary is clear.

Population rule: host repo values must be derived from the host repo. Package defaults may provide schema shape and managed-surface ownership, but not source-repo product intent, source-repo subsystem ids, source paths, proof commands, or issue references.

## Seed Bias

Prefer compact durable boundaries over broad prose mirrors. First candidates for mature repos are contract-like surfaces that encode repeatable decisions, restart boundaries, task-shape guidance, or proof expectations.

## Stop Conditions

Stop and ask or create bounded Planning state if setup output points at broad repo analysis, non-obvious host policy, or active work rather than durable operating knowledge.

## Output

Report setup mode, strongest candidate surfaces, what will be seeded, promoted, or dismissed, and the proof command.
