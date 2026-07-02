---
name: workspace-setup-jumpstart
description: Guide bounded post-bootstrap setup for newly installed or adopted Agentic Workspace in a lived-in repo after the main AW operating skill routes to setup jumpstart.
---

# Workspace Setup Jumpstart

Use this subskill when Agentic Workspace was newly installed or adopted in a lived-in or mature repo and the task is to populate, seed, or orient workspace surfaces after bootstrap.
This subskill assumes the main AW operating skill or compact router has already selected the AW invocation and routed here.

## Route

1. Run the configured invocation with `setup --target . --format json` for bounded post-bootstrap setup guidance.
2. Treat setup as pre-write and pre-seed discovery. Do not bulk-import docs, backlog, or prose.
3. Inspect only surfaces named by setup output, by the task, or by a durable mature-repo jumpstart memory note.
4. Promote only:
   - durable operating knowledge to Memory;
   - bounded follow-up to Planning;
   - evidence-backed friction to repo-friction or improvement intake;
   - low-confidence or generic findings to transient report only.
5. Before writing seed surfaces, check promotion criteria in `docs/setup-findings-contract.md` and the durable candidate rule in `docs/jumpstart-contract.md`.

## Required Seed Surfaces

When the task is to populate durable workspace surfaces after bootstrap, handle these files explicitly:

- `.agentic-workspace/OWNERSHIP.toml`: keep package-managed module roots, managed surfaces, fences, and authority surfaces generic; add host-specific `[[subsystems]]` only from inspected repo structure, test commands, ownership boundaries, or clear user direction. Do not copy subsystem entries from the Agentic Workspace source repo into a host repo.
- `.agentic-workspace/system-intent/intent.toml`: use the configured invocation with `system-intent --target . --sync --format json` first, then refine only reviewable interpreted fields that are supported by named repo intent sources such as `README.md`, `SYSTEM_INTENT.md`, product docs, or explicit user direction. Do not mechanically summarize every source file.
- `.agentic-workspace/system-intent/subsystems.toml`: add scoped durable intent only for subsystem ids already declared in `.agentic-workspace/OWNERSHIP.toml [[subsystems]]`. Leave `subsystems = []` when no host subsystem boundary is clear.
- `.agentic-workspace/config.toml [assurance]`: use the configured invocation with `defaults --section assurance_onboarding --format json` before seeding assurance. Add proof profiles, requirements, or subsystem profiles only when an inspected host-owned source names the risk, requirement, evidence burden, proof route, or claim boundary. Subsystem profiles must use existing `.agentic-workspace/OWNERSHIP.toml [[subsystems]]` ids.
- `.agentic-workspace/verification/manifest.toml`: use the configured invocation with `defaults --section verification_onboarding --format json` before seeding Verification. Add protocols, scenarios, proof routes, bundles, or known gaps only when the host repo has a repeatable proof need that ordinary test or command selection does not already express.
- `.agentic-workspace/verification/proof-strategy.toml`: seed only enum hints that the host repo explicitly owns. Do not summarize strategy prose or infer policy from filenames.

Population rule: host repo values must be derived from the host repo. Package defaults may provide schema shape and managed-surface ownership, but not source-repo product intent, source-repo subsystem ids, source paths, proof commands, or issue references.

Assurance and Verification population rule: AW surfaces questions and templates; the agent decides whether evidence is strong enough to write anything. Prefer leaving these surfaces absent over creating generic placeholder obligations.

## Seed Bias

Prefer compact durable boundaries over broad prose mirrors. First candidates for mature repos are contract-like surfaces that encode repeatable decisions, restart boundaries, task-shape guidance, or proof expectations.

## Stop Conditions

Stop and ask or create bounded Planning state if setup output points at broad repo analysis, non-obvious host policy, or active work rather than durable operating knowledge.

## Output

Report setup mode, strongest candidate surfaces, what will be seeded, promoted, or dismissed, and the proof command.
