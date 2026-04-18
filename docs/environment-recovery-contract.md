# Environment And Recovery Contract

This page defines the checked-in contract for environment assumptions, interruption handling, and recovery paths.

Use it in two closely related cases:

- when active planning work depends on non-obvious environment state or a compact resume path
- when workspace lifecycle work is blocked by repo-state ambiguity, interrupted bootstrap, or warnings that need an ordered remediation path

This contract is intentionally compact.
It exists to reduce dead-ends and restart cost without turning planning into a full runbook system or duplicating package-local operational docs.

## Purpose

- Keep environment-sensitive work restartable from checked-in state.
- Prefer one canonical recovery path over scattered troubleshooting prose.
- Make both task-local planning recovery and repo-level remediation cheaper than rediscovery.

## Planning-Side Recovery Contract

For an active planning slice, capture only the environment and recovery facts that materially affect safe continuation:

- required preconditions or tool state
- the first safe resume point after interruption
- known failure or retry boundaries
- the command or check that proves the environment is usable
- where to escalate when the active slice cannot recover locally

The goal is not exhaustive troubleshooting.
The goal is one compact answer to "what does this work need in order to resume safely right now?"

## Canonical Shape

Do not add a new dedicated recovery section to every execplan.
Use the existing planning fields deliberately:

- `Immediate Next Action`: the next safe resume step after interruption
- `Blockers`: environment failures, missing prerequisites, or recovery blockers that currently stop progress
- `Invariants`: environment assumptions and safety boundaries that must remain true
- `Validation Commands`: the narrowest command that proves the environment or touched surface is healthy enough to proceed
- `Execution Summary`: after completion, the compact note a later contributor needs instead of re-deriving the recovery story

For direct tasks, the same rule stays simple:
if safe continuation depends on more than the TODO row can carry, promote the task into an execplan instead of inventing ad hoc prose elsewhere.

## When To Promote Recovery Guidance Into Planning

Promote the work into an execplan or strengthen the active plan when any of these become true:

- interruption would leave more than one plausible safe resume path
- a failed command needs explicit retry, rollback, or cleanup guidance
- the active slice depends on non-obvious environment state that is easy to lose between sessions
- module-local docs explain the subsystem generally, but not the current task's recovery boundary
- another contributor would need to infer whether the problem is local environment drift, expected repo customization, or a real contract failure

If module-local docs already fully answer the operational question and the current task does not add a task-specific recovery wrinkle, link or rely on those docs instead of copying them into the plan.

## Ordered Recovery Path

Use this ordered path when normal work is blocked by repo-state ambiguity, interrupted bootstrap, lifecycle warnings, or a local environment that no longer matches the checked-in contract.

1. Inspect the current workspace state:
   - `agentic-workspace status --target ./repo`
   - `agentic-workspace doctor --target ./repo`
2. Reconfirm the default operating contract:
   - `agentic-workspace defaults --format json`
   - `agentic-workspace config --target ./repo --format json`
   - Treat `workspace.optimization_bias` in the config output as the effective repo output posture during ordinary recovery.
3. If the issue is package-contract freshness rather than repo-owned customization, refresh the shipped contract:
   - `uv run agentic-planning-bootstrap upgrade --target .`
   - `uv run agentic-memory-bootstrap upgrade --target .`
4. Re-run the narrowest proving lane for the touched surface:
   - workspace CLI changes -> `uv run pytest tests/test_workspace_cli.py`
   - planning package changes -> `uv run pytest packages/planning/tests/test_installer.py`
   - memory package changes -> `uv run pytest packages/memory/tests/test_installer.py`
   - cross-boundary maintainer work -> `make maintainer-surfaces`
5. If bootstrap or adopt work still requires judgment, follow the checked-in handoff:
   - `llms.txt` for the external-agent entry surface
   - `.agentic-workspace/bootstrap-handoff.md` when bootstrap says review is still needed
   - `.agentic-workspace/bootstrap-handoff.json` when the follow-on agent needs the compact structured handoff boundary directly

## What This Contract Covers

Use this contract for:

- interrupted install, adopt, or upgrade work
- repo-state ambiguity after lifecycle commands
- warnings about missing shared workspace files or managed surfaces
- uncertainty about the correct next proving lane
- restart after a broken or partial maintenance pass
- active execution work whose next safe step depends on task-local recovery context

Do not stretch it into:

- package-specific domain troubleshooting
- broad incident response
- a replacement for package READMEs or maintainer check docs
- a memory note for durable technical facts
- a narrative log of every failed attempt

## Recovery Rules

- Prefer `agentic-workspace` as the public recovery entrypoint.
- Treat `status` and `doctor` as the first inspection lane, not direct file spelunking.
- `doctor` should carry the compact upstream health checks that belong in the workspace layer itself, including contract-integrity drift and committed absolute-path leaks, so recovery does not depend on remembering ad hoc helper scripts first.
- Use `defaults` and `config` when the question is "what is the normal contract here?" rather than "what failed?"
- When recovery needs the effective output posture, inspect `agentic-workspace config --target ./repo --format json` and read `workspace.optimization_bias` directly instead of inferring it from rendered surfaces.
- Distinguish package drift from repo-local warnings:
  - package drift means the shipped payload is stale relative to checked-in package source
  - repo-local warnings may still be expected customization, nested-repo noise, or optional-surface absence
- Re-run only the narrowest validation that can prove the recovery worked.
- If recovery still needs human judgment, route through the checked-in handoff surfaces instead of chat-only interpretation.
- Do not stretch TODO rows into shadow execplans.

## Relationship To Direct Tasks

The direct-task contract remains intentionally small.

If the current work can still restart safely from `Why now`, `Next action`, and `Done when`, keep it direct.
If interruption, environment drift, or partial failure means the TODO row no longer answers "how do I continue safely?", promote the work into an execplan.

That promotion is the planning-side recovery contract.

## Relationship To Module Docs

Planning owns current execution recovery.
Module docs own durable operational guidance.

Use planning to capture:

- the recovery boundary for the active slice
- the exact precondition that matters now
- the escalation point for the current thread

Use module docs or memory to capture:

- stable runbooks
- recurring environment traps
- long-lived setup guidance
- subsystem-specific maintenance procedures

## Relationship To Other Docs

- [`docs/default-path-contract.md`](docs/default-path-contract.md) says which route is primary.
- [`docs/init-lifecycle.md`](docs/init-lifecycle.md) explains the init/adopt state machine and handoff signals.
- [`docs/delegated-judgment-contract.md`](docs/delegated-judgment-contract.md) explains what the agent may decide locally during recovery and when it must escalate.

This doc owns the recovery contract itself: both the compact planning-side shape and the ordered repo-level remediation path.

## Archive Rule

Before archiving a completed execplan, make sure the plan no longer depends on implicit recovery knowledge.

If later contributors would still need to reconstruct the safe resume point, environment assumption, or unresolved recovery blocker from chat or drift prose, the plan is not ready to archive cleanly.
