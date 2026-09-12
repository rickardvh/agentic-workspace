---
name: workspace-resources
description: Manage task scratch and necessary checkout isolation through one current-policy-aware native resource lifecycle, including terminal cleanup and interrupted recovery.
---

# Task resources

Use this procedure for implementation, review, delegation or maintenance when temporary material or checkout isolation is actually needed. It adds no review, completion or publication authority. Read current repository/local policy from the instruction owner; do not copy that policy into a resource registry.

## Smallest sufficient resource

1. Use the existing checkout for ordinary work. Determine a concrete conflicting-checkout, destructive-validation or transport-requires-isolation need before proposing isolation. Parallel convenience alone is insufficient. Prefer exact Git object reads for read-only inspection of another revision. Never clone merely to evade worktree policy.
2. Put arbitrary task JSON, packet dumps, temporary notes and experiments in one task container below `.agentic-workspace/local/scratch/`. Do not put loose files at the local root or mix temporary material into structured owner directories. Build caches and build outputs stay in their existing build-tool locations; repositories stay outside AW state.
3. Use the configured Rust-backed `resources` operation. Query `scratch-create` for a task container or `worktree-create` for necessary isolation. These are read-only proposals. Supply the current task and known changed paths. Native, JSON, Python and TypeScript projections call the same owner.
4. For isolation, read the proposal's current instruction sources and consequences. Supply the concrete `need` and `reason`, its exact `policy_revision`, and `policy_answer: permits-isolation` only if those sources permit the need. Do not invent consent or require the user to repeat an already available policy. A changed policy requires fresh judgment. If isolation is not necessary or permitted, continue in the existing checkout.
5. Execute only the returned exact `action` through `resources`. It is bound to current source/policy/resource identity and confined to the declared operation/path. Missing binaries or a rejected current proposal are explicit gaps, not permission for an alternate cleanup script. An effect result is separate from continuation or whole-task completion.

## Work and terminal reconciliation

Record the returned exact resource path in the current task context. Keep needed evidence under its responsible durable owner before disposing of temporary copies. Use `scratch-retain` with an explicit reason while interrupted material is needed, and `scratch-release` only after its disposition is settled. Owner references and retained material block scratch cleanup; reconcile through that owner instead of removing references to make cleanup pass.

At successful completion, failure, cancellation or resumed interrupted work, query `scratch-remove` or `worktree-remove` for the **same exact path**, then execute its freshly returned action when available. Do this as part of the task; do not wait for a later user cleanup request. Clean disposable resources are removed together with the exact Git registration. Dirty, untracked, ignored, unique-commit or owner-referenced material is preserved with current blockers and an exact recovery path. Report the preserved path and the disposition needed; do not force deletion. Preserve main-checkout HEAD/index and Git configuration.

If execution or response delivery is interrupted, reobserve the same path in a fresh process. Do not retry the old effect or create another checkout merely to recover. Git owns worktree registrations; resource-local custody supports recovery after interrupted unlock. A missing worktree directory can have its exact owned registration removed only after unique-commit checks. Unrelated registrations are preserved. Scratch cleanup is bounded to one recognized task container and retains its marker until its files are removed; unknown or changed bytes stop cleanup.

## Local hygiene

Query `audit` to inspect the shallow local namespace. Structured owner state is classified from the existing ownership ledger; ignored files are not automatically disposable. For unowned residue, identify exact references and its actual owner, preserve required material, and relocate only material established as disposable into the task container. Audit does not sweep unknown files. Do not create a second inventory, session database or broad scanner.

When executable AW is unavailable, read the main skill's same no-runtime boundary. Preserve resources and report the exact lifecycle gap; no-runtime source inspection does not grant cleanup effects.
