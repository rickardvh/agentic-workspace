# Shipped Payload Surface Inventory - 2026-04-29

## Scope

Inventory target: package payload surfaces that can be installed into another repository by bootstrap or upgrade commands.

This review was prompted by repo-specific memory notes appearing in a target repository after package upgrade.

## Findings

### Memory Package

Authoritative development payload source:

- `packages/memory/bootstrap/`

Packaged wheel destination:

- `repo_memory_bootstrap/_payload/`

Runtime preview command:

- `uv run agentic-memory-bootstrap list-files --target . --format json`

Shipped repo-memory surfaces after cleanup:

- `AGENTS.template.md`
- `README.md`
- `.agentic-workspace/docs/installer-behavior.md`
- `.agentic-workspace/docs/memory-metadata-contract.md`
- `.agentic-workspace/memory/WORKFLOW.md`
- `.agentic-workspace/memory/SKILLS.md`
- `.agentic-workspace/memory/UPGRADE-SOURCE.toml`
- `.agentic-workspace/memory/VERSION.md`
- `.agentic-workspace/memory/bootstrap/**`
- `.agentic-workspace/memory/skills/**`
- `.agentic-workspace/memory/repo/index.md`
- `.agentic-workspace/memory/repo/manifest.toml`
- `.agentic-workspace/memory/repo/domains/README.md`
- `.agentic-workspace/memory/repo/invariants/README.md`
- `.agentic-workspace/memory/repo/runbooks/README.md`
- `.agentic-workspace/memory/repo/decisions/README.md`
- `.agentic-workspace/memory/repo/templates/*.template.md`
No root-level `optional/`, `scripts/`, or `tools/` directories are part of the memory bootstrap payload.

Cleanup flags resolved in this slice:

- Removed repo-specific package payload notes such as `.agentic-workspace/memory/repo/runbooks/dogfooding-usage-ledger.md`.
- Removed repo-specific package payload domains, decisions, runbooks, mistakes, and repo-local skills.
- Replaced `*-template.md` starter file names with `*.template.md`.
- Removed root-level optional fragments and raw Python scripts from the memory bootstrap payload.
- Removed the duplicate tracked `packages/memory/memory/` tree. That tree was legacy source residue, not the current wheel force-include source, but it duplicated the installed repo-memory layout and made the package boundary ambiguous.

Residual accepted surfaces:

- `index.md` and `manifest.toml` remain bootstrap entry and machine-readable routing seed surfaces.
- Directory `README.md` files remain structural signposts.
- Shared package skills under `.agentic-workspace/memory/skills/**` remain package-managed behavior, not repo-specific memory.

### Planning Package

Authoritative development payload source:

- `packages/planning/bootstrap/`

Packaged wheel destination:

- package `_payload` entries declared by `repo_planning_bootstrap.installer.REQUIRED_PAYLOAD_FILES`

Current boundary check:

- `scripts/check/check_source_payload_operational_install.py` compares expected payload files, bootstrap source files, and packaging force-includes.

Cleanup flags resolved:

- Removed root-level generated `tools/` mirrors from the planning bootstrap source.
- Removed raw Python helper script copies from both root-level `scripts/` and managed `.agentic-workspace/planning/scripts/` bootstrap paths.
- Maintainer render/check scripts remain package/root source code, not shipped bootstrap payload.

### Workspace Package

Shipped surfaces are primarily generated adapters, contracts, and common CLI/package files under:

- `src/agentic_workspace/contracts/**`
- generated adapter outputs such as `AGENTS.md`, `llms.txt`, and `tools/**`

Cleanup flag:

- Out of scope for this slice; existing visible-surface compression work owns adapter size and authority.

## Guardrail

The source/payload/root-install checker now treats memory bootstrap extras under `.agentic-workspace/memory/repo/**` as intentional only when they are structural or templated:

- directory `README.md`
- `AGENTS.md` / `AGENTS.template.md`
- `*.template.md`
- `*.schema.json`
- explicitly managed package metadata

The checker also fails package bootstrap helper directories that would reintroduce root-level `optional/`, `scripts/`, or `tools/` payloads.

Executable code is not allowed anywhere under package bootstrap payload roots. The CLI/package source owns executable behavior; checked-in payload files must remain declarative structural docs, templates, schemas, metadata, and compatibility guidance.

Repo-specific note, runbook, decision, domain, mistake, or repo-local skill payloads should now fail the boundary inventory instead of being silently classified as intentional.
