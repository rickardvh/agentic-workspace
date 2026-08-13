# Workspace Workflow

This file is a compact recovery pointer, not an independent workflow authority or task-state surface.

## Ordinary route

Use the configured Agentic Workspace invocation:

1. Run `start --target . --task "<task>" --format json`, or `implement --target . --changed <paths> --task "<task>" --format json` when changed paths are known.
2. Follow `next_safe_action`, `action_signals`, `skills`, and the projected `planning_route_decision` before opening raw managed files.
3. Preserve the route's `decision_id`, `input_revision`, `action_identity`, required transition, proof expectation, mutation authority, and blocked claims across startup, implementation, skills, handoff, proof, and closeout.
4. Before completion, reconcile proof, intent, residue, issue/PR closure, and next ownership separately.

Do not use this file for plans, progress, decisions, or handoff state. Durable state belongs in the package-owned Planning, Memory, issue, or repository-configured surfaces selected by the runtime.

## No-CLI recovery

When every configured invocation attempt fails, run the installed capsule renderer:

```text
python .agentic-workspace/fallback/no_cli_startup.py
```

The renderer verifies `.agentic-workspace/fallback/no-cli-policy.json` against its contract digest and reports:

- the invocation attempts and authority/version identity;
- the smallest safe read-only orientation;
- forbidden effects and claims while authority is unavailable;
- the exact restoration action; and
- narrow drill-down pointers.

If the capsule is missing, unreadable, or stale, stop at read-only orientation. Do not infer mutation, external-write, destructive-action, proof-complete, task-complete, or issue-closeable authority from this prose. Restore the configured CLI and rerun `start`; do not reconstruct work shape, Planning transitions, proof gates, or closeout rules manually.

## Boundaries

- Startup and inspection do not adopt a provisional route or authorize managed-state mutation.
- A changed branch, head, worktree, repository, target, current-work identity, or selected owner requires a fresh route decision before action.
- Domain-specific consumers may narrow the compiled decision but cannot widen its effects, claims, mutation authority, or terminal state.
- Raw `.agentic-workspace` files and package manuals are drill-down surfaces only after the runtime or verified recovery capsule points there.

