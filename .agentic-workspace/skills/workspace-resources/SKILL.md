---
name: workspace-resources
description: Manage task scratch and necessary checkout isolation through one current-policy-aware native resource lifecycle, including terminal cleanup and interrupted recovery.
---

# Task resources

Use this procedure for implementation, review, delegation or maintenance when temporary material or checkout isolation is actually needed. It adds no review, completion or publication authority. Read current repository/local policy from the instruction owner; do not copy that policy into a resource registry.

## Smallest sufficient resource

1. Use the existing checkout for ordinary work. Determine a concrete conflicting-checkout, destructive-validation or transport-requires-isolation need before proposing isolation. Parallel convenience alone is insufficient. Prefer exact Git object reads for read-only inspection of another revision. Never clone merely to evade worktree policy.
2. Put arbitrary task JSON, packet dumps, temporary notes and experiments in one task container below `.agentic-workspace/local/scratch/`. Do not put loose files at the local root or mix temporary material into structured owner directories. Build caches and build outputs stay in their existing build-tool locations; repositories stay outside AW state.
3. Use the configured Rust-backed `resources` operation with `compose: true` in the request. `scratch-create` prepares and carries its exact native action automatically. `worktree-create` returns the current policy/necessity question when judgment is missing. Supply the current task and known changed paths. Native, JSON, Python and TypeScript projections call the same owner.
4. For isolation, read the returned current instruction sources and consequences. Supply the concrete `need` and `reason`, its exact `policy_revision`, and `policy_answer: permits-isolation` only if those sources permit the need, retaining `compose: true`. Do not invent consent or require the user to repeat an already available policy. A changed policy requires fresh judgment. If isolation is not necessary or permitted, continue in the existing checkout.
5. The bounded composition checks the selected skill's exact executable availability, then carries only the returned native `action` through a fresh resource-owner admission. It stops at missing judgment, changed material, blockers or uncertainty; it never loops over actions or runs work commands. Inspect `effect_outcome`, the owner result, and `resource_context`/`build_environment`. Process success is not proof of effect commitment or whole-task completion.

## Callable path and fallback

For scratch, pass `{"operation":"scratch-create","compose":true}` to the
configured `resources --target <repo> --task <task> --input <request.json>` command.
The existing Python/TypeScript `resources(context)` and JSON resource transport
accept the same request. The package skill's selected executable declaration
requires the existing native reader capability `resource-procedure-v1`; missing
material or incompatible runtime returns unavailable detail before resource work.
No Python or shell resource implementation is introduced.

Keep the returned `resource_context` in caller context. To clean up, carry its
target/task/changed fields with a request containing the same exact `path`,
`operation: scratch-remove` (or `worktree-remove`) and `compose: true`. Reentry
uses fresh observations, never an old `expected_revision`. `resource_context` is
ordinary disposable carriage, not a session record or authority grant.

Direct work normally needs no call. If a caller needs an explicit no-resource
result, `{"operation":"direct","compose":true}` performs zero resource-owner
calls and creates no resource state. `audit` remains a read-only report.

If composition is unavailable but the existing native resource operation is
available, omit `compose`: obtain a read-only proposal and execute only its exact
returned `action` after the same policy judgment. Missing native execution itself
requires the no-runtime preservation boundary, not an alternate cleanup script.

## Reproducible build output

Before creating an isolated checkout used for build/test work, request `disposable_outputs` containing only the needed empty tool roots (`target`, `.pytest_cache`, `.venv`). The native owner rejects a root already present in the source tree, creates it empty and records its disposable lifetime in the existing Git registration. Use the returned `build_environment` for commands: Cargo and Python bytecode use the leased target root, and uv uses the leased virtual environment. Pytest's default root cache is covered when `.pytest_cache` is leased. Do not put required/user artifacts in leased tool roots; preserve them under their actual owner. An existing root cannot be retrospectively adopted during teardown. Without a creation lease, even a familiar ignored directory is unknown material and is preserved.

Terminal cleanup removes only these creation-leased reproducible roots before removing the clean worktree. Unknown ignored paths, tracked files added under output roots, and current owner references still block removal. A failed cleanup reobserves the same registration and remaining roots; it does not recreate the checkout or erase unowned output.

## Work and terminal reconciliation

Record the returned exact resource path in the current task context. Keep needed evidence under its responsible durable owner before disposing of temporary copies. Use `scratch-retain` with an explicit reason while interrupted material is needed, and `scratch-release` only after its disposition is settled. Owner references and retained material block scratch cleanup; reconcile through that owner instead of removing references to make cleanup pass.

At successful completion, failure, cancellation or resumed interrupted work, request `scratch-remove` or `worktree-remove` with `compose: true` for the **same exact path**. The procedure prepares and carries the freshly returned action when available. Do this as part of the task; do not wait for a later user cleanup request. Clean disposable resources are removed together with the exact Git registration. Dirty, untracked, ignored, unique-commit or owner-referenced material is preserved with current blockers and an exact recovery path. Report the preserved path and the disposition needed; do not force deletion. Preserve main-checkout HEAD/index and Git configuration.

If execution or response delivery is interrupted, reobserve the same path in a fresh process. Do not retry the old effect or create another checkout merely to recover. Git owns worktree registrations; resource-local custody supports recovery after interrupted unlock. A missing worktree directory can have its exact owned registration removed only after unique-commit checks. Unrelated registrations are preserved. Scratch cleanup is bounded to one recognized task container and retains its marker until its files are removed; unknown or changed bytes stop cleanup.

## Local hygiene

Query `audit` to inspect the shallow local namespace. Structured owner state is classified from the existing ownership ledger; ignored files are not automatically disposable. For unowned residue, identify exact references and its actual owner, preserve required material, and relocate only material established as disposable into the task container. Audit does not sweep unknown files. Do not create a second inventory, session database or broad scanner.

When executable AW is unavailable, read the main skill's same no-runtime boundary. Preserve resources and report the exact lifecycle gap; no-runtime source inspection does not grant cleanup effects.
