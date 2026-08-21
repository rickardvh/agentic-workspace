# Agentic Workspace

Agentic Workspace helps AI coding agents work consistently in a repository across sessions, tools, and models.

It gives the repository a small agent-facing layer for instructions, relevant context, reusable procedures, verification expectations, and continuation state. Instead of loading one large static guide for every task, an agent can ask what matters now and get a compact route to the context and actions that apply.

Use it when agents repeatedly rediscover the same repository knowledge, important intent lives only in conversation, different parts of the repo need different procedures or checks, or work needs to survive handoffs and restarts. If ordinary docs, tests, and a short task are already enough, Agentic Workspace should stay unnecessary or minimal.

## What changes for an agent

An AW-enabled repository keeps a small `.agentic-workspace/` enclave plus thin agent entrypoints such as `AGENTS.md`. The agent normally starts from a compact Workspace query instead of scanning that enclave or rereading every instruction source.

For example:

```bash
agentic-workspace start --target . --task "Update authentication token handling" --format json
```

For a task like that, the answer can point the agent to only the things that matter: applicable repository instructions, any current work or continuation state, a relevant procedure, constraints on what may be changed, checks that matter before the work can be considered complete, and one next safe action. Unrelated module state and deeper documentation stay out of the first response unless they become relevant.

Command-line interfaces are one way to access this behavior, not a workflow the agent has to memorize.

## First-party modules

Most of Agentic Workspace's current higher-level functionality is provided by three first-party modules. They are independently selectable rather than mandatory: a repository can use the Workspace routing/control layer on its own or add the modules that solve recurring problems.

- **Memory** preserves repository knowledge that is costly to rediscover, so later agents can recover useful lessons, constraints, and orientation without repeating the same investigation.
- **Planning** preserves active work and execution continuity across sessions and agents: what is being worked on, the intent and boundaries that matter, what remains, and where continuation belongs.
- **Verification** preserves reusable verification procedures, evidence, and known gaps so agents can apply the right checks and keep completion claims aligned with what has actually been established.

Workspace connects these capabilities with task-shaped routing, repository instructions, ownership, and the current action and completion boundaries. A module should become visible when its capability matters without making unrelated tasks carry its terminology or procedure.

See [`docs/package/modules.md`](docs/package/modules.md) for module roles and ownership.

## What Workspace provides

The Workspace layer provides the common operating path around those capabilities:

- **Task-shaped repository guidance** — apply scoped instructions, ownership, policy, and procedures only when they matter to the current work.
- **Compact routing** — start from one current answer instead of reconciling several instruction and state surfaces manually.
- **Reusable procedures and actions** — route agents to maintained skills and supported operations instead of relying on remembered command sequences.
- **Repository-specific control** — let repo-owned configuration and instructions affect agent behavior while keeping the acting agent focused on what applies now.
- **Progressive detail** — keep unrelated module state, diagnostics, and deeper procedures out of first contact until the task needs them.

## How it works

Agentic Workspace treats the repository as the durable home of the context that should govern agent work. That can include system intent, ownership, scoped instructions, current work, learned lessons, verification requirements, and other source-owned facts or procedures.

AW does not need to copy or model the whole repository. Source code, ordinary documentation, tests, and other canonical content remain where they already belong. Workspace selects the small amount of operating context that can change the current decision and routes deeper material only when needed.

The ordinary control loop is:

1. **Resolve** — determine the smallest trustworthy guidance for the current task and decision.
2. **Act** — follow the supported operation, procedure, owner, or explicit human decision it points to.
3. **Reconcile** — record the result with the correct owner, determine what changed and what may now be considered complete, then resolve again if work remains.

Internally, AW composes that into one current operating contract rather than leaving the agent to reconcile several competing answers about what to read, what to do, what is allowed, and whether the work is complete.

Repository instructions can also be dynamic rather than purely static: repo-owned configuration, scoped guidance, skills, verification rules, and capability state can change what AW surfaces or requires for a particular task. The deeper architecture for programmable instruction composition is described in [`docs/architecture.md`](docs/architecture.md).

## Interfaces and implementations

Agentic Workspace is defined around shared repository contracts and operations rather than one agent runtime or implementation language.

Current CLI implementations target **Python** and **TypeScript** and share the same operation semantics. The same contract boundary can support additional agent and tool integrations without changing the repository model.

See [`docs/package/contracts.md`](docs/package/contracts.md) for the current contract and generated-interface model.

## Getting started

Use the installation guide for current installation and adoption guidance:

[`docs/agentic-workspace-install.md`](docs/agentic-workspace-install.md)

After adoption, the repository's thin agent instructions normally route the agent through Workspace. When interacting manually, `start` is the ordinary first question; deeper commands such as `implement`, `proof`, `summary`, `skills`, `ownership`, and `report` are used when the current task or returned guidance calls for them.

Agentic Workspace keeps its checked-in footprint deliberately small. Selected modules add their own owned state, while implementation packages, generated clients, caches, and local diagnostics keep separate ownership and lifecycle boundaries.

See [`docs/package/installed-surfaces.md`](docs/package/installed-surfaces.md) for the installed-footprint model.

## Scope and trust

Agentic Workspace complements the repository's existing source, documentation, tests, review process, and issue tracker. It does not replace them or turn the repository into a separate knowledge database or task-management system. It guides and constrains how an agent operates without scripting ordinary implementation choices.

**Agentic Workspace is not a sandbox.** Treat the repository and its configured verification or executor commands as trusted before allowing AW to execute them. Admitted shell routes inherit the caller's filesystem and credential authority, and external issue, PR, or service text should be treated as data rather than execution permission.

See [`docs/security/threat-model.md`](docs/security/threat-model.md) for the full trust and supply-chain boundary.

## Learn more

- [`docs/package/overview.md`](docs/package/overview.md) — product model and ordinary operating loop.
- [`docs/agentic-workspace-install.md`](docs/agentic-workspace-install.md) — installation and adoption.
- [`docs/package/modules.md`](docs/package/modules.md) — first-party modules and ownership.
- [`docs/architecture.md`](docs/architecture.md) — operating context, dynamic control, programmable instructions, and extension boundaries.
- [`docs/extension-boundary.md`](docs/extension-boundary.md) — module and external-extension architecture.
- [`docs/security/threat-model.md`](docs/security/threat-model.md) — trust and supply-chain boundary.
- [`docs/package/contracts.md`](docs/package/contracts.md) — machine-readable contracts and generated references.
- [`docs/index.md`](docs/index.md) — full documentation map.

When maintaining Agentic Workspace itself rather than using it in another repository, follow [`AGENTS.md`](AGENTS.md) and the [`maintainer documentation`](docs/maintainer/index.md).
