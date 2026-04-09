# Skill Discovery Contract

This page defines how Agentic Workspace skills should be registered, discovered, and selected.

## Layers

- bundled package skills: package-distributed skills that should be explicitly registered when the package is built or installed
- installed managed skills: shared product-managed skills copied into the target repo by install or upgrade
- repo-owned skills: checked-in local extensions that complement bundled skills without inheriting package ownership

## Registry Rule

Do not rely on filesystem walking as the primary discovery contract.

Instead:

- bundled package skills should ship with an explicit `REGISTRY.json`
- installed managed skills should preserve that registry in the target repo
- repo-owned skills should use a separate repo-owned `REGISTRY.json`
- directory scanning is only a fallback for missing registration and should be treated as incomplete discovery

## Selection Rule

Users should not need to know skill ids.

Instead:

- skill registries should carry explicit activation hints for task matching
- workspace skill recommendation should prefer those explicit hints over directory or filename inference
- recommended skills should explain why they matched
- explicit user-named skill ids remain optional overrides, not the normal operating path

## Consultation Rule

Discovery is not enough on its own. Stable workflow families should also consult the skill layer automatically.

In particular:

- when a task is clearly review-shaped, prefer consulting `agentic-workspace skills --task ...` before generic reasoning
- when a task is clearly roadmap/review-promotion shaped, prefer the planning promotion skills before ad hoc queue edits
- when a task is clearly intake-shaped, prefer the intake skill before inventing tracker-to-planning routing

The product goal is not to force skills onto every task. It is to make stable, repeatable workflow classes lower-interpretation than generic reasoning for the same request.

## Current Registry Surfaces

- planning bundled installed skills: `.agentic-workspace/planning/skills/REGISTRY.json`
- memory bundled bootstrap skills in the package source: `packages/memory/skills/REGISTRY.json`
- memory installed managed core skills: `.agentic-workspace/memory/skills/REGISTRY.json`
- repo-owned memory skills: `memory/skills/REGISTRY.json`
- repo-owned general skills: `tools/skills/REGISTRY.json`

## Ownership Rule

- package-managed registries are updated by install or upgrade from the owning package
- repo-owned registries are maintained by the repository and should not be overwritten by package upgrades
- repo-owned skills should be clearly distinct from bundled package skills in both registry metadata and discovery output
- `memory/skills/` is reserved for repo-owned skills whose primary purpose is operating on checked-in memory or maintaining the memory system
- general repo-owned contract, checking, or workflow skills should live under `tools/skills/`

## Recommendation Surface

- `agentic-workspace skills --target ./repo --format json` lists the explicit registered catalog
- `agentic-workspace skills --target ./repo --task "<task text>" --format json` returns the same catalog plus ranked recommendations and matching reasons
