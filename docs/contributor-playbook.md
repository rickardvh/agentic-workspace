# Contributor Playbook

## Purpose

Use this playbook to choose the right package, planning surface, and validation lane before making changes in `agentic-workspace`.

Use `docs/maintainer-commands.md` when you need the literal command to run; use this playbook when you need routing, ownership, or validation guidance.

This playbook is primarily for maintainers operating as coding agents. Human contributors can use it too, but it is intentionally optimized for explicit routing, bounded reads, and narrow validation.

Use `docs/design-principles.md` when a change affects product shape, ownership, lifecycle behavior, or the amount of ceremony the repo imposes on normal work.
Use `docs/compatibility-policy.md` when you need to judge whether a surface is stable, mutable, or generated before making the change.
Use `docs/init-lifecycle.md` when you need the canonical root `init` mode matrix or prompt semantics.
Use `docs/orchestrator-workflow-contract.md` when you are delegating a bounded slice and need the agent-agnostic planner/worker contract.
Use `docs/generated-surface-trust.md` when a change touches generated docs, mirrors, or rerender expectations.
Use `docs/proof-surfaces-contract.md` when the missing judgment is which proof lane actually answers the current trust question.
Use `docs/ownership-authority-contract.md` when the missing judgment is who owns a concern or which checked-in surface is authoritative.

## Start Here

Default startup path for an agent maintainer:

1. Read `AGENTS.md`.
2. Read `TODO.md`.
3. If the question is startup order or first-contact routing, ask `agentic-workspace defaults --section startup --format json` before broader prose.
4. If you need the current planning state, ask `agentic-planning-bootstrap summary --format json` before opening raw planning files.
5. If you need the combined workspace state, ask `agentic-workspace report --target ./repo --format json` before reading raw module files.
6. If `TODO.md` points at an active execplan and the compact surfaces are insufficient, read that plan before editing code.
7. If you are handing the active slice to another executor, derive the worker contract from `agentic-planning-bootstrap handoff --format json` rather than drafting a fresh ad hoc prompt.
8. Use `agentic-workspace config --target ./repo --format json` to inspect the effective mixed-agent posture, including the optional local capability/cost override in `agentic-workspace.local.toml`.
9. Read package-local `AGENTS.md` only for the package you will touch.
10. Use this playbook to pick the right ownership surface and narrow validation lane.

Prefer repository-native state over chat-only context. If a follow-up matters after the current turn, record it in planning or memory instead of relying on conversational residue.

If you are maintaining the repo through git commits locally, run `make setup` to sync the shared environment and install hooks for this clone. If the environment is already synced and you only need to restore the hook, run `make install-hooks`. The repo-managed pre-commit Git hook formats staged Ruff-managed files, stages those formatter edits automatically, then runs the shared lint lane and the remaining commit checks. On `master`, the hook also runs the full test lane before allowing the commit. If you intentionally want the stock pre-commit wrapper behavior instead, reinstall it explicitly with `uv run pre-commit install`.
The hook set also runs `uv run python scripts/check/check_no_absolute_paths.py`, so tracked files cannot introduce absolute filesystem paths.

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
- In checked-in human-facing docs, prefer clickable Markdown links for navigation, but keep the target paths repo-relative. Do not introduce absolute filesystem paths into links or prose unless the absolute external path is itself the documented subject.

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
- use `docs/capability-aware-execution.md` when the missing judgment is capability fit rather than ownership: cheap direct path, medium reasoning direct path, stronger planning first, silent shaping into a cheaper slice, delegation-friendly, or stop-and-escalate
- when capability-aware execution suggests a cleaner but broader solution, treat that as a promotion or escalation decision instead of silently replacing the requested outcome; improve local means, not requested ends
- when an execplan completes only part of a larger intended outcome, record both `Intent Continuity` and `Required Continuation` before archive; required follow-on must name a checked-in owner surface and activation trigger instead of surviving only in prose or chat
- do not create an execplan just because a stronger agent is available; use one when the checked-in artifact is likely to save tokens or reduce coordination risk overall
- when the environment supports multiple agents or models, a stronger one may write a compact execution contract for a smaller one, but that handoff is optional and should stay cheaper than the rediscovery it prevents
- when a slice is delegated, use `agentic-planning-bootstrap handoff --format json` as the worker-facing contract and pass it to whichever executor is available internally or externally; the repo does not prescribe the executor brand, API, or model
- if stronger capability keeps seeming necessary for the same class of work, treat that as an improvement-targeting signal for better decomposition, validation, or guidance rather than as a standing instruction to keep raising executor strength
- if the same human correction keeps repeating for the same class of work, treat that as an improvement-targeting signal for better defaults, contracts, proof, ownership, or handoff rather than as normal conversational steering
- treat direct execution as a valid success path, then record only the minimum durable residue that outlives the task

## Validation Lanes

Run the narrowest lane that proves the change.

Use `agentic-workspace defaults --format json` first when you need the structured default answer for which lane is enough, when broader checks are needed, and when the work should escalate beyond the narrow proving path.

- Root workspace CLI changes: `uv run pytest tests/test_workspace_cli.py`, `uv run ruff check src tests`, `uv run ty check src`
- Memory package changes: `make sync-memory` once, then `cd packages/memory && uv run pytest <path>` for a focused repro or `make test-memory` for the parallel full-suite lane; use `cd packages/memory && uv run ruff check .` for lint and escalate to `make check-memory` for the full package lane
- Planning package changes: `make sync-planning` once, then `cd packages/planning && uv run pytest <path>` for a focused repro or `make test-planning` for the parallel full-suite lane; use `cd packages/planning && uv run ruff check .` for lint and escalate to `make check-planning` for the full package lane
- Maintainer-surface, generated-doc, or installed-contract payload changes: `make maintainer-surfaces`
- Planning-surface changes only: `make planning-surfaces`; rerun `make render-agent-docs` when the planning manifest or generated routing docs change
- Declarative contract manifests or schemas for workspace proof/report/selectors: `uv run python scripts/check/check_contract_tooling_surfaces.py`
- Memory note/current-state changes: `uv run python scripts/check/check_memory_freshness.py`
- Absolute-path hygiene across tracked files: `make absolute-paths`

Escalate to `make check-memory`, `make check-planning`, or `make check-all` only when the change crosses package or root orchestration boundaries.

The default suite-oriented `make test`, `make test-workspace`, `make test-memory`, `make test-planning`, and package `make test` lanes run `pytest` with xdist (`-n auto`). Keep direct `uv run pytest <path>` invocations available for tiny focused runs where worker startup would dominate.

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

Use `memory/runbooks/dogfooding-feedback-routing.md` for the capture convention and preferred destinations.
Use `docs/reviews/README.md` `context-cost` mode when the question is which startup or handoff surfaces are actually used, skipped, or too insider-shaped for normal work.

Use `docs/installed-contract-design-checklist.md` when a package change adds or materially reshapes an installed file, generated mirror, or other collaboration-sensitive contract surface.

## Review Expectations

- Preserve package boundaries and independent CLI entrypoints.
- Prefer explicit adapters, manifests, and generated artifacts over private cross-package assumptions.
- Capture meaningful follow-up work in `ROADMAP.md`, `TODO.md`, or an execplan instead of leaving it in chat-only residue.
