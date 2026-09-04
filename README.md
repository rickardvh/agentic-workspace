# Agentic Workspace

Agentic Workspace helps AI coding agents work consistently in a repository across sessions, tools, and models.

It gives the repository a small agent-facing continuity and execution layer for instructions, relevant context, reusable procedures, durable planning and memory, verification expectations, and delegation. Instead of loading one large static guide for every task or reconstructing important state from chat history, an agent can ask what matters now and get a compact route to the context and actions that apply.

Use it when agents repeatedly rediscover the same repository knowledge, important intent lives only in conversation, different parts of the repo need different procedures or checks, work needs to survive handoffs and restarts, or the right next step depends on current repository state. If ordinary docs, tests, and a short task are already enough, Agentic Workspace should stay unnecessary or minimal.

## What changes for an agent

An AW-enabled repository can keep scoped repository guidance alongside a small `.agentic-workspace/` enclave for package- or module-owned state. The agent normally starts from one compact Workspace query instead of scanning every instruction, state file, and procedure up front.

For example:

```console
pip install agentic-workspace
agentic-workspace start --target . --task "Update authentication token handling"
```

For a task like that, the answer can surface only the things that matter: applicable repository guidance, relevant remembered context, current planned work, a reusable procedure, verification that matters for the intended claim, delegation when another target is a better fit, and one exact supported action or bounded human decision. Unrelated capabilities and deeper detail stay out of the first response unless they become relevant.

When the decision is actionable, execute its returned `primary_action` unchanged:

```console
agentic-workspace invoke --target . --invocation '<primary_action JSON>'
```

The result carries the next current decision. The CLI is an interface to this behavior, not a workflow the agent has to memorize.

## What Agentic Workspace helps with

- **Task-shaped repository guidance** — apply scoped instructions, constraints, procedures, and repository-owned choices only when they matter to the current work.
- **Continuation across sessions and agents** — preserve useful active work so a later agent can continue without reconstructing the task from chat history.
- **Reusable procedures and supported actions** — route agents to maintained procedures and typed operations instead of relying on remembered command sequences.
- **Verification and completion** — make relevant proof expectations and completion boundaries visible before an agent says the work is done.
- **Durable anti-rediscovery context** — retain repository knowledge that is expensive to rederive and useful to later work without making every task load it.
- **Delegation and handoff** — select an eligible better-fit target when appropriate, bind the assignment, and bring returned work back through the parent's normal verification and completion path.
- **Repository-specific control** — let repo-owned guidance and configuration affect agent behavior while keeping machine- or provider-specific choices local.
- **Quiet direct work** — capabilities that do not matter to the current task contribute nothing and add no mandatory ceremony.

## Built-in capabilities

Agentic Workspace keeps domain capabilities separate from the core operating loop. The built-in package currently includes:

- **Repository controls** — scoped repository guidance, procedures, bounded choices, and claim restrictions.
- **Memory** — durable advisory knowledge that is expensive to rediscover and selectively relevant later.
- **Planning** — proportional durable custody for work that needs interruption, dependency, handoff, or fresh-session continuation.
- **Verification** — repository-owned proof strategy, evidence, and claim boundaries.
- **Assignment and delegation** — best-fit target selection, binding handoff, bounded return, and integration with Planning and Verification.

Installing or enabling a capability should not make every task carry its terminology or state. Independent modules can contribute capabilities through the same module contract without requiring core workflow changes.

See [source-owner batteries](docs/source-owner-batteries.md), [assignment and delegation](docs/assignment-and-delegation.md), and the [module API](docs/module-api.md).

## How it works

Agentic Workspace treats the repository as the durable home of the context that should govern agent work. Source code, ordinary documentation, tests, review history, and other canonical content remain where they already belong; AW does not try to copy or model the whole repository.

For each task, Workspace resolves only the relevant source owners and produces one current operating answer. That answer may be an exact typed action, a bounded human/domain decision, an exact blocker with a recovery route, a direct-work answer, or a terminal answer. Effects go through supported operations, then the owning sources are reconciled and the next answer is derived from current state.

This gives agents one place to ask what matters now without turning AW into a workflow engine or replacing ordinary implementation judgment.

## Interfaces and implementations

The Python package includes the `agentic-workspace` CLI and programmatic Workspace APIs:

```console
pip install agentic-workspace
```

A generated TypeScript/JavaScript package exposes the same semantic contract for host and adapter integrations:

```console
npm install @rickardvh/agentic-workspace
```

Python, TypeScript, and the JSON CLI project the same underlying decision and operation semantics. External integrations consume those boundaries; Agentic Workspace does not require a provider registry, credential host, or adapter marketplace.

See the [operating contract](docs/v1-contract.md), [generated two-language contract](docs/generated-contract.md), and [compatibility policy](docs/compatibility-policy.md) for exact interface details.

## Getting started

After installation, try `start` against a real repository task. Direct work should remain direct; when repository guidance, Memory, Planning, Verification, or delegation matters, Workspace will surface the relevant context or action without requiring you to know the internal module topology first.

Repository-specific guidance can be scoped through `AGENTS.md`, while shared and local configuration remain separate according to authority and portability. Exact configuration and module formats belong in their reference documentation rather than being duplicated in the README.

## Scope and trust

Agentic Workspace complements a repository's existing source, documentation, tests, review process, and issue tracker. It does not replace them, turn the repository into a separate knowledge database, or script ordinary implementation choices.

**Agentic Workspace is not a sandbox.** Treat the repository, configured commands, and installed modules as trusted before allowing them to execute with your filesystem or credential authority. External issue, PR, and service content should be treated as data rather than execution permission.

See [SECURITY.md](SECURITY.md) for the current trust boundary.

## Learn more

- [Source-owner batteries](docs/source-owner-batteries.md) — repository controls, Memory, Planning, Verification, and reuse.
- [Assignment and delegation](docs/assignment-and-delegation.md) — target selection, handoff, return, and integration semantics.
- [Module API](docs/module-api.md) — capability-first extension contract.
- [Operating contract](docs/v1-contract.md) — exact `start`/`invoke` decision and operation model.
- [Generated two-language contract](docs/generated-contract.md) — Python/TypeScript semantic parity and host boundary.
- [Compatibility policy](docs/compatibility-policy.md) — supported contract evolution and compatibility behavior.
- [SYSTEM_INTENT.md](SYSTEM_INTENT.md) — durable product intent and architectural boundaries.

When maintaining Agentic Workspace itself rather than using it in another repository, follow [AGENTS.md](AGENTS.md) and the maintainer material under `tools/`.
