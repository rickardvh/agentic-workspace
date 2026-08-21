# Agentic Workspace

Agentic Workspace helps AI coding agents work consistently in a repository across sessions, tools, and models.

It gives the repository a small agent-facing layer for instructions, relevant context, reusable procedures, verification expectations, and continuation state. Instead of loading one large static guide for every task, an agent can ask what matters now and get a compact route to the context and actions that apply.

Use it when agents repeatedly rediscover the same repository knowledge, important intent lives only in conversation, different parts of the repo need different procedures or proof, or work needs to survive handoffs and restarts. If ordinary docs, tests, and a short task are already enough, Agentic Workspace should stay unnecessary or minimal.

## What changes for an agent

An AW-enabled repository keeps a small `.agentic-workspace/` enclave plus thin agent entrypoints such as `AGENTS.md`. The agent normally starts from a compact Workspace query instead of scanning that enclave or rereading every instruction source.

For example:

```bash
agentic-workspace start --target . --task "Update authentication token handling" --format json
```

For a task like that, the resolved answer can point the agent to only the things that matter: applicable repository instructions, the current owner or continuation state, a relevant procedure or skill, constraints on what may be changed, verification that matters for the intended claim, and one next safe action. Unrelated module state and deeper documentation stay out of the first response unless they become relevant.

The CLI is an interface to this behavior, not a workflow the agent has to memorize.

## What Agentic Workspace helps with

- **Task-shaped repository guidance** — apply scoped instructions, ownership, policy, and procedures only when they matter to the current work.
- **Continuation across sessions and agents** — preserve useful active context so work can be resumed without reconstructing the task from chat history.
- **Reusable procedures and actions** — route agents to skills and typed operations instead of relying on remembered command sequences.
- **Verification and claim boundaries** — make relevant proof expectations and completion constraints visible before an agent overclaims.
- **Durable anti-rediscovery context** — retain repository knowledge that is expensive to rederive and useful to later agents.
- **Repository-specific control** — let repo-owned configuration and instructions affect agent behavior while keeping the acting agent focused on the resulting decision rather than a large policy model.

## Optional capabilities

Agentic Workspace can be used as a small routing/control layer on its own or with additional modules.

The current first-party modules are:

- **Memory** — preserves durable repository knowledge that is expensive to rediscover.
- **Planning** — preserves active execution continuity, bounded intent, handoff, and continuation state.
- **Verification** — preserves reusable verification protocols, bounded evidence, proof-route hints, and known gaps.

Select only the capabilities that solve a recurring problem in the repository. Installing a capability should not make every task carry its terminology or procedure.

See [`docs/package/modules.md`](docs/package/modules.md) for module roles and ownership.

## How it works

Agentic Workspace treats the repository as the durable home of the context that should govern agent work. That can include system intent, ownership, scoped instructions, current work, learned lessons, proof requirements, and other source-owned facts or procedures.

AW does not need to copy or model the whole repository. Source code, ordinary documentation, tests, and other canonical content remain where they already belong. Workspace selects the small amount of operating context that can change the current decision and routes deeper material only when needed.

The ordinary control loop is:

1. **Resolve** — determine the smallest trustworthy operating contract for the current task and decision.
2. **Act** — follow its supported operation, skill, owner, or explicit human decision.
3. **Reconcile** — admit the result to the correct owner, determine what changed and what may be claimed, then resolve again if work remains.

The result is one compact operating contract rather than several competing answers about what to read, what to do, what is allowed, and whether the work is complete.

Repository instructions can also be dynamic rather than purely static: repo-owned configuration, scoped guidance, skills, verification rules, and capability state can change what AW surfaces or requires for a particular task. The deeper architecture for programmable instruction composition is described in [`docs/architecture.md`](docs/architecture.md); the README intentionally focuses on the user-facing experience rather than its internal rule model.

## Interfaces and implementations

Agentic Workspace is defined around shared repository contracts and operations rather than one agent runtime or implementation language.

Current command implementations target **Python** and **TypeScript** and are generated from the same operation semantics. The same contract boundary is intended to support additional agent and tool integrations without changing the repository model.

For exact current target and contract information, use the generated/reference material under [`docs/package/contracts.md`](docs/package/contracts.md) and the source contract [`src/agentic_workspace/contracts/target_support.json`](src/agentic_workspace/contracts/target_support.json).

## Getting started

Use the installation guide for the current supported installation and adoption paths:

[`docs/agentic-workspace-install.md`](docs/agentic-workspace-install.md)

After adoption, the repository's thin agent instructions normally route the agent through Workspace. When interacting manually, `start` is the ordinary first question; deeper commands such as `implement`, `proof`, `summary`, `skills`, `ownership`, and `report` are used when the current task or returned contract calls for them.

Agentic Workspace keeps its checked-in footprint deliberately small. Selected modules add their own owned state, while implementation packages, generated clients, caches, and local diagnostics keep separate ownership and lifecycle boundaries.

See [`docs/package/installed-surfaces.md`](docs/package/installed-surfaces.md) for the installed-footprint model.

## Scope and trust

Agentic Workspace complements the repository's existing source, documentation, tests, review process, and issue tracker; it does not replace them or attempt to turn the repository into a separate knowledge database or task-management system. It controls the agent's operating envelope without scripting ordinary implementation judgment.

**Agentic Workspace is not a sandbox.** Treat the repository and its configured proof or executor commands as trusted before allowing AW to execute them. Admitted shell routes inherit the caller's filesystem and credential authority, and external issue, PR, or service text should be treated as data rather than execution permission.

See [`docs/security/threat-model.md`](docs/security/threat-model.md) for the full trust and supply-chain boundary.

## Learn more

- [`docs/package/overview.md`](docs/package/overview.md) — product model and ordinary operating loop.
- [`docs/agentic-workspace-install.md`](docs/agentic-workspace-install.md) — installation and adoption.
- [`docs/package/modules.md`](docs/package/modules.md) — optional modules and ownership.
- [`docs/architecture.md`](docs/architecture.md) — operating context, dynamic control, programmable instructions, and extension boundaries.
- [`docs/extension-boundary.md`](docs/extension-boundary.md) — module and external-extension architecture.
- [`docs/security/threat-model.md`](docs/security/threat-model.md) — trust and supply-chain boundary.
- [`docs/package/contracts.md`](docs/package/contracts.md) — machine-readable contracts and generated references.
- [`docs/index.md`](docs/index.md) — full documentation map.

When maintaining Agentic Workspace itself rather than using it in another repository, follow [`AGENTS.md`](AGENTS.md) and the [`maintainer documentation`](docs/maintainer/index.md).