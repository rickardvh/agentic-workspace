# Skill System Review

## Goal

- Review whether the current skill system is strong enough in discovery, naming, routing, and arsenal coverage to behave like a real operating layer for agents rather than a secondary expert-only feature.

## Scope

- Skill discovery contract and registries.
- Bundled planning and memory skill catalogs.
- Repo-owned skills.
- Workspace task-to-skill recommendation behavior.

## Non-Goals

- Do not implement skill changes in this review.
- Do not activate new work in `TODO.md` from the review alone.
- Do not review external runtime skill systems outside this repository.

## Review Mode

- Mode: `contract-integrity`
- Review question: Does the current skill system make the right skills discoverable, name them clearly, route to them reliably, and provide the right day-to-day arsenal for normal repo work?
- Default finding cap: 3 findings
- Inputs inspected first: `docs/skill-discovery-contract.md`, `packages/planning/skills/REGISTRY.json`, `packages/memory/skills/REGISTRY.json`, `.agentic-workspace/memory/skills/REGISTRY.json`, `memory/skills/REGISTRY.json`, `src/agentic_workspace/cli.py`

## Review Method

- Commands used:
  - `uv run agentic-workspace skills --target . --task "perform a review of the planning package" --format json`
- Evidence sources:
  - bundled and installed skill registries
  - skill README/catalog docs
  - actual recommendation output
  - current repo-owned skill placement

## Findings

### Finding: Planning skill catalog docs overclaim bootstrap skills that do not exist

- Summary: The planning skills README still describes `bootstrap-adoption` and `bootstrap-uninstall` as bundled planning skills, but the actual planning skill directory and registry only ship `bootstrap-upgrade` plus the planning-specific execution and review skills.
- Evidence: `packages/planning/skills/README.md` lists `bootstrap-adoption` and `bootstrap-uninstall`, while `packages/planning/skills/REGISTRY.json` and the `packages/planning/skills/` directory contain only `bootstrap-upgrade`, `planning-autopilot`, `planning-intake-upstream-task`, `planning-promote-review-findings`, and `planning-review-pass`.
- Risk if unchanged: Agents or maintainers may trust the catalog and go looking for nonexistent bundled skills, which weakens trust in the registry-backed discovery contract.
- Suggested action: Tighten planning skill catalog docs to match the registry exactly, and decide explicitly whether planning should ship adoption/uninstall skills or stop implying that it does.
- Confidence: high
- Source: static-analysis
- Promotion target: `ROADMAP.md`
- Promotion trigger: Promote when the skill-catalog contract is next touched or when another maintainer pass still finds README-to-registry drift after the current registry-backed discovery work.
- Post-remediation note shape: delete

### Finding: Skill discovery is productively queryable, but automatic routing still depends on the agent deciding to consult it

- Summary: The skill system can now recommend the correct review skill for a natural review-shaped request, but the operating contract still does not make that consultation automatic enough, so the same task can succeed or fail depending on whether the agent independently chooses to query the skill layer.
- Evidence: `agentic-workspace skills --target . --task "perform a review of the planning package" --format json` ranks `planning-review-pass` first with valid reasons, but ordinary repo work still produced a miss where the agent answered as if no review skill should be used until the deficiency was called out explicitly.
- Risk if unchanged: Skills remain a latent expert surface rather than the normal low-interpretation workflow layer the product wants, especially for cheaper or more literal agents.
- Suggested action: Treat automatic skill consultation for review-shaped and similarly stable task classes as a first-class follow-up, likely by making startup/routing guidance prefer a skill recommendation check before generic reasoning when the request matches a known skill family.
- Confidence: high
- Source: friction-confirmed
- Promotion target: `ROADMAP.md`
- Promotion trigger: Promote when another ordinary review-shaped request still misses the bundled review skill, or by explicit maintainer choice if the product goal is to make skills the default operating path rather than an optional aid.
- Post-remediation note shape: shrink

### Finding: The current arsenal is useful but unevenly placed, and repo-owned general checks are hiding under memory-owned skill space

- Summary: The bundled arsenal is already strong for planning execution/review and for memory capture/hygiene/router workflows, but the repo-owned follow-on skills for foundation stability, ownership ledger checks, and path consolidation are not really memory-specific even though they currently live under `memory/skills/`.
- Evidence: `memory/skills/REGISTRY.json` contains repo-owned skills such as `foundation-stability-check`, `ownership-ledger-check`, and `path-consolidation-check`, each of which targets workspace or package-boundary contract checks rather than memory-note work. The skill discovery contract already allows optional repo-owned general skills under `tools/skills/REGISTRY.json`, but this repo has no such general registry yet.
- Risk if unchanged: Arsenal growth may continue, but ownership and naming will become muddier; agents will have more skills without a clearer model for when a skill is a memory skill versus a general workspace skill.
- Suggested action: Review whether repo-owned general contract/checking skills should move into a general repo-owned skill home such as `tools/skills/`, leaving `memory/skills/` for truly memory-shaped workflows.
- Confidence: medium
- Source: mixed
- Promotion target: `ROADMAP.md`
- Promotion trigger: Promote when the repo adds another general-purpose repo-owned skill that does not naturally belong to memory, or when repeated routing misses show current placement is confusing agents.
- Post-remediation note shape: retain

## Recommendation

- Promote: none automatically
- Defer: all three findings pending explicit maintainer choice or repeated friction
- Dismiss: the idea that skills should cover every workflow regardless of stability or repeatability

## Validation / Inspection Commands

- `uv run agentic-workspace skills --target . --task "perform a review of the planning package" --format json`

## Drift Log

- 2026-04-09: Review created after dogfooding exposed another review-skill routing miss and raised a broader question about the skill system's discovery, naming, and arsenal quality.
