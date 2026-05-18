# Installed Module Map

Use this file as the compact abstraction ladder for an installed Agentic Workspace repo. It is a router, not a manual.

## Workspace

Workspace owns cross-module orchestration:

- startup adapters and compact first-contact commands
- lifecycle install, upgrade, status, doctor, and uninstall routing
- config, local overrides, ownership, proof routing, and combined reports
- module composition and installed-surface boundaries

Start with compact commands before reading raw files:

```bash
agentic-workspace start --target . --format json
agentic-workspace preflight --target . --format json
agentic-workspace summary --target . --format json
agentic-workspace report --target . --format json
```

## Planning

Planning owns active execution state:

- `.agentic-workspace/planning/state.toml`
- `.agentic-workspace/planning/execplans/*.plan.json`
- decomposition records for epic-shaped work
- active proof expectations, handoff, closeout, and continuation routing

Use Planning when work needs to survive a session, branch, handoff, or non-obvious validation path. Completed execplans should be distilled and removed from active Planning by default; only future-relevant residue should move to Memory, docs, checks, contracts, config, Planning, or an issue.

Preferred command:

```bash
agentic-planning summary --target . --format json
```

Compatibility alias:

```bash
agentic-planning summary --target . --format json
```

## Memory

Memory owns durable anti-rediscovery knowledge:

- invariants and authority boundaries
- subsystem orientation that is expensive to rederive
- recurring traps and operator runbooks
- routing hints that help agents read less

Use Memory when future work should not rediscover a stable fact, constraint, or procedure. Do not store active task state, backlog, milestone history, or broad product documentation in Memory.

Preferred command:

```bash
agentic-memory report --target . --format json
```

Compatibility alias:

```bash
agentic-memory report --target . --format json
```

## Generated References

Generated reference docs explain exact fields and structured outputs. Use them after the conceptual owner is clear:

- `docs/reference/workspace-config.md`
- `docs/reference/startup-context.md`
- `docs/reference/workspace-report.md`
- `docs/reference/cli-commands.md`

Do not start broad work by reading generated references end to end.
