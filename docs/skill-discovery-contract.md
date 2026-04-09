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

## Current Registry Surfaces

- planning bundled installed skills: `.agentic-workspace/planning/skills/REGISTRY.json`
- memory bundled bootstrap skills in the package source: `packages/memory/skills/REGISTRY.json`
- memory installed managed core skills: `.agentic-workspace/memory/skills/REGISTRY.json`
- repo-owned memory skills: `memory/skills/REGISTRY.json`
- optional repo-owned general skills: `tools/skills/REGISTRY.json`

## Ownership Rule

- package-managed registries are updated by install or upgrade from the owning package
- repo-owned registries are maintained by the repository and should not be overwritten by package upgrades
- repo-owned skills should be clearly distinct from bundled package skills in both registry metadata and discovery output

## Recommendation Surface

- `agentic-workspace skills --target ./repo --format json` lists the explicit registered catalog
- `agentic-workspace skills --target ./repo --task "<task text>" --format json` returns the same catalog plus ranked recommendations and matching reasons
