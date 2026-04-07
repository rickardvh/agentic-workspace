# Contributor Playbook

## Purpose

Use this playbook to choose the right package, planning surface, and validation lane before making changes in `agentic-workspace`.

Use `docs/maintainer-commands.md` when you need the literal command to run; use this playbook when you need routing, ownership, or validation guidance.

This playbook is primarily for maintainers operating as coding agents. Human contributors can use it too, but it is intentionally optimized for explicit routing, bounded reads, and narrow validation.

Use `docs/design-principles.md` when a change affects product shape, ownership, lifecycle behavior, or the amount of ceremony the repo imposes on normal work.
Use `docs/compatibility-policy.md` when you need to judge whether a surface is stable, mutable, or generated before making the change.
Use `docs/init-lifecycle.md` when you need the canonical root `init` mode matrix or prompt semantics.
Use `docs/generated-surface-trust.md` when a change touches generated docs, mirrors, or rerender expectations.

## Agent Maintainer Path

Default startup path for an agent maintainer:

1. Read `AGENTS.md`.
2. Read `TODO.md`.
3. Read one active execplan only when `TODO.md` points to it.
4. Read package-local `AGENTS.md` only for the package you will edit.
5. Use this playbook to pick the right ownership surface and narrow validation lane.

Prefer repository-native state over chat-only context. If a follow-up matters after the current turn, record it in planning or memory instead of relying on conversational residue.

If you are maintaining the repo through git commits locally, install hooks with `uv run pre-commit install`. The current pre-commit hooks run the shared `make format` and `make lint` lanes: apply automatic formatting fixes locally, then enforce lint before commit. If formatting rewrites files, restage them and rerun the commit. Keep full test execution in CI instead of the pre-commit path.

## Start Here

1. Read `AGENTS.md`.
2. Read `TODO.md`.
3. If `TODO.md` points at an active execplan, read that plan before editing code.
4. Load package-local docs only for the package you will touch.

## Ownership Map

- Root workspace: shared lifecycle orchestration, root planning surfaces, shared memory notes, root validation entrypoints, and the thin `agentic-workspace` CLI.
- `packages/memory/`: reusable `agentic-memory-bootstrap` source, packaged payload, package skills, and memory-specific tests.
- `packages/planning/`: reusable `agentic-planning-bootstrap` source, packaged payload, planning helpers, and planning-specific tests.

## Pick The Right Surface

- Use root planning surfaces for active work, roadmap candidates, and execplans.
- Use root memory notes for durable repo knowledge, decisions, and recurring failure modes.
- Treat `memory/current/` as weak-authority current context: concise re-orientation only, not the durable home for facts.
- Use `docs/source-payload-operational-install.md` when one change spans package source, packaged payload, and the root installed surfaces.
- Leave touched surfaces cleaner than you found them, and route broader cleanup as follow-up instead of treating it as invisible task residue.
- Use `docs/compatibility-policy.md` for surface-stability questions before deciding whether a doc, manifest, or managed mirror is safe to change directly.
- Use `docs/init-lifecycle.md` before changing or explaining root `init` behavior so the mode semantics stay canonical.
- Use `docs/generated-surface-trust.md` for canonical-source and freshness questions before editing mirrors or routing docs.
- Edit package code only when the change belongs to that package's shipped behavior or tests.
- Keep the root `agentic-workspace` CLI thin; push module-specific lifecycle logic back into the module packages.
- Treat `.agentic-workspace/` module trees as product-managed surfaces; change them through the owning package or managed source rather than as freehand repo docs.
- Treat `tools/` agent docs as generated mirrors; change `.agentic-workspace/planning/agent-manifest.json` and rerender instead of editing them directly.

As a maintainer rule of thumb:

- if the fact should survive the current task, it probably belongs in memory or canonical docs
- if the fact changes what is active now or what must happen next, it probably belongs in planning
- if the behavior is package-specific, keep it in that package rather than teaching the workspace layer too much

Design guardrails:

- prefer repo-native state over chat residue when the fact materially affects restart cost or safe execution
- reduce reading and reasoning cost rather than adding broad new workflow surfaces
- preserve one clear owner per concern instead of duplicating authority across docs, memory, planning, checks, or orchestration
- keep simple work simple; add ceremony only when complexity, ambiguity, or collaboration risk justifies it
- keep the workspace layer thin and explicit rather than absorbing package-local domain logic
- favor portable, selective-adoption behavior over monorepo-local cleverness

For execution scaling specifically:

- keep work direct in `TODO.md` when one coherent pass can finish it and the row can stay at `ID`, `Status`, `Surface`, `Why now`, `Next action`, and `Done when`
- promote to an execplan when the work gains milestone sequencing, blocker handling, non-obvious validation scope, rollback or migration detail, enough ambiguity that restart would require more than the TODO row, or enough context pressure that a smaller or less capable agent would otherwise have to rediscover the task
- do not create an execplan just because a stronger agent is available; use one when the checked-in artifact is likely to save tokens or reduce coordination risk overall
- when the environment supports multiple agents or models, a stronger one may write a compact execution contract for a smaller one, but that handoff is optional and should stay cheaper than the rediscovery it prevents
- treat direct execution as a valid success path, then record only the minimum durable residue that outlives the task

## Validation Lanes

Run the narrowest lane that proves the change.

- Root workspace CLI changes: `uv run pytest tests/test_workspace_cli.py`, `uv run ruff check src tests`, `uv run ty check src`
- Memory package changes: `make sync-memory` once, then `cd packages/memory && uv run pytest` or `cd packages/memory && uv run ruff check .`; escalate to `make check-memory` for the full package lane
- Planning package changes: `make sync-planning` once, then `cd packages/planning && uv run pytest` or `cd packages/planning && uv run ruff check .`; escalate to `make check-planning` for the full package lane
- Maintainer-surface, generated-doc, or installed-contract payload changes: `make maintainer-surfaces`
- Planning-surface changes only: `make planning-surfaces`; rerun `make render-agent-docs` when the planning manifest or generated routing docs change
- Memory note/current-state changes: `uv run python scripts/check/check_memory_freshness.py`

Escalate to `make check-memory`, `make check-planning`, or `make check-all` only when the change crosses package or root orchestration boundaries.

Final repo sync after package work:

- After memory or planning package changes, refresh the root repo install to the latest checked-in version of both packages as a final compatibility test: `uv run agentic-planning-bootstrap upgrade --target .` and `uv run agentic-memory-bootstrap upgrade --target .`

## Common Routes

- Lifecycle orchestration or root CLI: start at `src/agentic_workspace/` and `README.md`.
- Memory bootstrap behavior: start at `packages/memory/AGENTS.md`, then `packages/memory/README.md` and `packages/memory/src/`.
- Planning bootstrap behavior: start at `packages/planning/AGENTS.md`, then `packages/planning/README.md` and `packages/planning/src/`.
- Planning contract or archive behavior: start at `TODO.md`, the active execplan, and `packages/planning/src/repo_planning_bootstrap/installer.py`.

Generated guidance lives under `tools/`, but the source of truth for that guidance is `.agentic-workspace/planning/agent-manifest.json`. When routing docs drift, update the managed manifest and rerender instead of editing generated files directly.

## Dogfooding Feedback Capture

When internal use reveals friction, classify it before routing it onward.

- Package defect
- Boundary issue
- Install-flow issue
- Docs or routing issue
- Monorepo-only friction

Use `docs/dogfooding-feedback.md` for the capture convention and preferred destinations.

Use `docs/installed-contract-design-checklist.md` when a package change adds or materially reshapes an installed file, generated mirror, or other collaboration-sensitive contract surface.

## Review Expectations

- Preserve package boundaries and independent CLI entrypoints.
- Prefer explicit adapters, manifests, and generated artifacts over private cross-package assumptions.
- Capture meaningful follow-up work in `ROADMAP.md`, `TODO.md`, or an execplan instead of leaving it in chat-only residue.
