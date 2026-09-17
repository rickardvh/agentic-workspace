# Contributor Playbook

## Purpose

Use this playbook to choose the right package, planning surface, and validation lane before making changes in `agentic-workspace`.

Use `docs/maintainer/maintainer-commands.md` when you need the literal command to run; use this playbook when you need routing, ownership, or validation guidance.

This playbook is primarily for maintainers operating as coding agents. Human contributors can use it too, but it is intentionally optimized for explicit routing, bounded reads, and narrow validation.

Resolve this concern through the canonical startup skill and the current owner request returned by `start`. The [native CLI catalogue](/docs/reference/cli-catalogue.md) defines executable commands.

## Documentation Role Map

- `README.md`: public entrypoint and ordinary user path.
- `AGENTS.md`: repo-owned startup adapter for agents.
- `docs/maintainer/contributor-playbook.md`: maintainer routing, ownership, and validation guide.
- `docs/maintainer/maintainer-commands.md`: literal command index.
- `docs/design-principles.md`: product doctrine and tradeoff guidance.
- `docs/maintainer/dogfooding-feedback.md`: friction admission and routing policy.
- `.agentic-workspace/docs/*`: product-managed installed contracts.
- `packages/*/README.md`: package-specific install, ownership, and development reference.
- `docs/reviews/*`: evidence and history, not ordinary startup input.

## Start Here

Treat `start`, `summary`, `report`, `defaults`, and `preflight` as context-router views over the same workspace state:

- `start`: ordinary entry
- `summary`: current planning, active work, and handoff state
- `report`: workspace routing, diagnostics, warnings, and section selectors
- `defaults`: policy, contract, setup, proof, and startup answers
- `preflight`: takeover and recovery bundle

Default startup path for an agent maintainer:

Resolve this concern through the canonical startup skill and the current owner request returned by `start`. The [native CLI catalogue](/docs/reference/cli-catalogue.md) defines executable commands.

Prefer repository-native state over chat-only context. If a follow-up matters after the current turn, record it in planning or memory instead of relying on conversational residue.

If you are maintaining the repo through git commits locally, run `make setup` to sync the shared environment and install hooks for this clone. If the environment is already synced and you only need to restore the hook, run `make install-hooks`. The repo-managed pre-commit Git hook allocates one collision-safe validation run, synchronizes dependencies once, formats and stages Ruff-managed files, then runs the setup-free lint and typecheck lanes. The stock pre-commit wrapper routes through the same composition when installed explicitly with `uv run pre-commit install`.
The hook set also runs `uv run python scripts/check/check_no_absolute_paths.py`, so tracked files cannot introduce absolute filesystem paths.

## Ownership Map

- Root workspace: shared lifecycle orchestration, root planning surfaces, memory notes, root validation entrypoints, and the thin `agentic-workspace` CLI.
- `packages/memory/`: reusable `agentic-memory` source, packaged payload, package skills, and memory-specific tests.
- `packages/planning/`: reusable `agentic-planning` source, packaged payload, planning helpers, and planning-specific tests.
- `packages/verification/`: reusable `agentic-verification` source, packaged payload, manifest/report primitives, and verification-specific tests.
- `command-generation`: released, hash-pinned maintainer dependency for generated CLI package rendering and proof. Agentic Workspace consumes it through `scripts/generate/workspace_command_generation.py` and `scripts/check/check_generated_command_packages.py`; workspace command facts remain in `src/agentic_workspace/contracts/`, and runtime behavior remains in hand-written workspace/package code unless a generated target explicitly owns the projection.

## Pick The Right Surface

- Use root planning surfaces for active work, roadmap candidates, and execplans.
- Use memory notes for durable repo knowledge, decisions, and recurring failure modes.
- Treat `.agentic-workspace/memory/repo/current/` as optional routing calibration and legacy migration residue: durable facts belong in memory/docs, active state belongs in planning/status, and transient context belongs in local-only scratch.
- Use `.agentic-workspace/docs/extraction-and-discovery-contract.md` when one change spans package source, packaged payload, and the root installed surfaces.
- Leave touched surfaces cleaner than you found them, and route broader cleanup as follow-up instead of treating it as invisible task residue.
- Use `.agentic-workspace/docs/compatibility-policy.md` for surface-stability questions before deciding whether a doc, manifest, or managed mirror is safe to change directly.
- Use `.agentic-workspace/docs/lifecycle-and-config-contract.md` before changing or explaining root lifecycle behavior or configuration so the semantics stay canonical.
- Use `.agentic-workspace/docs/generated-surface-trust.md` for canonical-source and freshness questions before editing mirrors or routing docs.
- Edit package code only when the change belongs to that package's shipped behavior or tests.
- Keep the root CLI and language bindings thin; current deterministic domain semantics and effects belong to the Rust core. Package-local Python tools remain source-maintenance mechanisms.
- Treat `.agentic-workspace/` module trees as product-managed surfaces; change them through the owning package or managed source rather than as freehand repo docs.
- Treat `tools/` agent docs as generated mirrors; change `.agentic-workspace/planning/agent-manifest.json` and rerender instead of editing them directly.
- Author current CLI commands and options in `source_decision_contract.json` and the native implementation. Retained command-generation metadata and process conformance fixtures are classified `source-maintenance-only`; they do not define installed/public commands. Keep Python `cli.py` a native launcher.
- Treat command/code generation, autopilot/self-improvement loops, package extraction, and heavy maintenance pressure as source-checkout-only maintainer tooling. Review artifacts and external tracker adapters are the reusable host-repo diagnostics that may remain behind `workspace.advanced_features`.
- In checked-in human-facing docs, prefer clickable Markdown links for navigation, but keep the target paths repo-relative. Do not introduce absolute filesystem paths into links or prose unless the absolute external path is itself the documented subject.

Operation IR has a four-level ladder:

- Primitive: a minimal deterministic implementation unit owned by command generation when it is portable, or by a named package/runtime extension when it is domain-specific.
- Fragment: an operation-local reusable sequence of primitive steps. Use this for repeated step shapes inside an operation before adding another primitive.
- Operation: the behavior contract for one command-facing action, including effects, inputs, guards, proof, and the IR plan.
- Command: the adapter projection that exposes an operation to a target CLI or package surface.

Prefer the lowest level that expresses the behavior clearly. Do not hide ordinary composition inside a broad primitive, and do not promote a fragment into a shared primitive until repeated use and proof show that the abstraction is stable across operations or targets.

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

Resolve this concern through the canonical startup skill and the current owner request returned by `start`. The [native CLI catalogue](/docs/reference/cli-catalogue.md) defines executable commands.

## Validation Lanes

Run the narrowest lane that proves the change.

Resolve this concern through the canonical startup skill and the current owner request returned by `start`. The [native CLI catalogue](/docs/reference/cli-catalogue.md) defines executable commands.

Resolve this concern through the canonical startup skill and the current owner request returned by `start`. The [native CLI catalogue](/docs/reference/cli-catalogue.md) defines executable commands.

Escalate to `make check-memory`, `make check-planning`, or `make check-all` only when the change crosses package or root orchestration boundaries.

The default suite-oriented `make test`, `make test-workspace`, `make test-memory`, `make test-planning`, and package `make test` lanes run `pytest` serial by default. Opt into xdist only when local capacity is known, for example with `PYTEST_PARALLEL_ARGS='-n 4'`; keep direct `uv run pytest <path>` invocations available for tiny focused runs where worker startup would dominate.

Final repo sync after package work:

- After module package changes, refresh the affected root repo install as a final compatibility test. Use `uv run agentic-planning upgrade --target .` for Planning, `uv run agentic-memory upgrade --target .` for Memory, and the Verification report/proof lane for Verification until it has a separate payload-upgrade command.

## Common Routes

Resolve this concern through the canonical startup skill and the current owner request returned by `start`. The [native CLI catalogue](/docs/reference/cli-catalogue.md) defines executable commands.

Generated guidance lives under `tools/`, but the source of truth for that guidance is `.agentic-workspace/planning/agent-manifest.json`. When routing docs drift, update the managed manifest and rerender instead of editing generated files directly.

## Dogfooding Feedback Capture

When internal use reveals friction, classify it before routing it onward.

- Package defect
- Boundary issue
- Install-flow issue
- Docs or routing issue
- Monorepo-only friction

Use `docs/maintainer/dogfooding-feedback.md` for the durable admission and routing policy.
Use `.agentic-workspace/memory/repo/runbooks/dogfooding-feedback-routing.md` for the capture convention and preferred destinations.
Use `.agentic-workspace/planning/reviews/README.md` `context-cost` mode when the question is which startup or handoff surfaces are actually used, skipped, or too insider-shaped for normal work.

Use `docs/maintainer/installed-contract-design-checklist.md` when a package change adds or materially reshapes an installed file, generated mirror, or other collaboration-sensitive contract surface.

## Review Expectations

- Preserve package boundaries and module CLI entrypoints for package-local maintenance/debugging, while keeping Workspace as the ordinary host-repo orchestrator.
- Prefer explicit adapters, manifests, and generated artifacts over private cross-package assumptions.
- Capture meaningful follow-up work through the planning helpers or the narrowest current planning surface instead of leaving it in chat-only residue.
- For any changed operational surface, use the [operational affordance design guidance](operational-affordance-design.md): make the current action, legitimate choice, bounded question or recovery constructible; keep required restrictions visible and optional detail selective; and confirm unfamiliar agents can proceed while knowledgeable agents can use sufficient sources and tools directly.
