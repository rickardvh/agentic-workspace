# Agent Instructions

<!-- agentic-workspace:workflow:start -->
Read `.agentic-workspace/WORKFLOW.md` for shared workflow rules.
<!-- agentic-workspace:workflow:end -->

Local bootstrap contract for agents working in this monorepo.

## Precedence

Resolve instruction conflicts in this order:

1. Explicit user request.
2. `AGENTS.md`.
3. Package-local `AGENTS.md` under `packages/*/` once imported.
4. Routed memory or canonical repo docs when present.

## Startup Procedure

1. Read `AGENTS.md`.
2. Read `TODO.md`.
3. Read the active feature plan in `docs/execplans/` when the TODO surface points there.
4. Read `ROADMAP.md` only when promoting work.
5. Load package-local docs only for the package being edited.
6. Before touching a shipped package, refresh it to the latest checked-in version through that package's canonical update workflow so local work starts from the current package contract.
7. When a change crosses package source, package payload, and root install boundaries, read `docs/source-payload-operational-install.md` before editing.
8. When making claims about GitHub issue state, verify the live issue set with `gh` instead of relying only on checked-in intake notes.

Do not start coding from chat context alone when the same information exists in checked-in files.
Do not bulk-read all planning surfaces.

## Sources Of Truth

- Active queue: `TODO.md`
- Long-horizon candidate work: `ROADMAP.md`
- Design constraints for future changes: `docs/design-principles.md`

## Product Direction

This repository exists to build agent-first workspace infrastructure: systems that make coding agents more capable, more reliable, and easier to trust in real repositories.
The one-word summary of the product goal is `efficiency`: maximum quality at minimum token cost over time for a single repository.

Dogfooding is a primary development mode here, not just background context.
When normal work in this repo reveals friction, ambiguity, noisy maintenance, or repeated agent missteps in the shipped planning or memory systems, treat that as a product signal that should enter the checked-in feedback loop.
Route that signal into the active execplan, `TODO.md`, `ROADMAP.md`, memory, or canonical docs as appropriate instead of treating chat or ad hoc direct package edits as the default feedback path.

Work in this repo should steer toward these goals:

- Build for agents first, while keeping the result legible and useful to humans.
- Treat development work in this repo as live testing of the shipped packages and workflows.
- Dogfood every major capability here before treating it as mature.
- Continuously evaluate friction, reliability gaps, confusing ownership, and handoff failures during normal work.
- Feed meaningful friction and improvement signals back into the active plan, roadmap, or routed memory instead of leaving them in chat-only residue.
- When internal use reveals repeated friction, prefer fixing the shipped package or contract over adding repo-local workaround guidance.
- Prefer repository-native state over chat-only or tool-local state.
- Give agents durable context, explicit execution state, clear routing, narrow validation, and cheap handoff.
- Optimise for continuity across sessions, tools, models, and contributors.
- Prefer work that lowers token spend by shrinking rediscovery, cross-checking, and avoidable rereads.
- Keep systems modular, portable, and selectively adoptable in other repos.
- Preserve strict boundaries between concerns; do not let planning, memory, routing, checks, or workspace orchestration blur together.
- Treat internal use as a proving ground, not a licence for repo-specific hacks.
- Generalise only after a feature works under real autonomous use here.
- Avoid overfitting to this monorepo when shaping package behavior; prefer solutions that remain broadly useful in other repositories.
- Favour mechanisms that reduce rediscovery, drift, and manual supervision.
- Keep the system quiet in normal use: prefer structure that lowers reading and reasoning cost over workflow ceremony.
- Leave the repository cleaner than you found it within the touched scope, and record broader cleanup as follow-up instead of silently expanding the task.
- Preserve one primary owner per concern so planning, memory, routing, checks, and orchestration do not drift into duplicated authority.
- Treat selective adoption as a product requirement, not a nice-to-have: each module should remain useful alone.
- Keep lifecycle centralized and domain logic package-local so workspace convenience does not erase module responsibility.

The standard for success is not novelty. It is giving agents real operating leverage in a repo: faster restart, safer execution, better continuity, and less wasted context.
When several plausible improvements compete, prefer the one that most directly removes an efficiency tax from normal repo work.

When changing product shape, ownership boundaries, lifecycle behavior, or maintainer workflow, re-check `docs/design-principles.md` and make sure the change still passes those design tests.

## Repo Rules

- Keep package boundaries explicit.
- Preserve independent package versioning and CLI entry points.
- Treat line-ending-only drift in generated `tools/` mirrors as noise unless the canonical manifest or rendered content changed.
- In checked-in human-facing docs, keep links clickable but use repo-relative paths only; do not commit absolute filesystem paths in Markdown links or prose path references unless a non-repo absolute path is the subject of the documentation itself.

## Validation

- Run the narrowest validation that proves a change.
- Prefer package-local checks after package import.
- Add monorepo-wide checks only when cross-package integration changes.
- As a final repo-level test after package work, refresh the root install to the latest checked-in version of both shipped packages: `uv run agentic-planning-bootstrap upgrade --target .` and `uv run agentic-memory-bootstrap upgrade --target .`.
- When verifying that the repo is on the latest shipped package contract, distinguish payload freshness from repo-local advisory warnings: run the package upgrade flow, `verify-payload`, package/root doctor surfaces, and report separately whether remaining warnings are package drift or expected repo-local customisation/noise.

## Dogfooding Rule

- Treat this monorepo as the proving ground for shipped agent workflows.
- If repo-local work exposes a real product deficiency in planning, memory, routing, checks, or lifecycle behavior, capture it in the checked-in planning or memory system so the signal survives the current session.
- Prefer promoting the signal into planned work instead of making unauthorised direct package changes solely because the repo exposed the issue.
- Make direct package or shipped-contract fixes only when they are already in active scope, explicitly requested, or clearly the smallest approved way to complete the current planned work.
- When a repo-specific symptom does not generalise cleanly, record the signal in memory, docs, roadmap, or an execplan instead of forcing a package change.
- When a finding surfaces about this repo, explicitly ask whether it could or should have been found, prevented, or remediated by the shipped product itself.
- If the answer is plausibly yes, record that as part of the checked-in feedback loop and treat the repo-local symptom as a potential package or contract improvement, with the product surface as the preferred remediation target when planning later promotes the work.
