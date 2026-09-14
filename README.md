# Agentic Workspace

Agentic Workspace helps AI coding agents work consistently in a repository across sessions, tools, and models.

It gives the repository a small agent-facing layer for instructions, relevant context, reusable procedures, verification expectations, and continuation state. Instead of loading one large static guide for every task, an agent can ask what matters now and get a compact route to the context and actions that apply.

Use it when agents repeatedly rediscover the same repository knowledge, important intent lives only in conversation, different parts of the repo need different procedures or checks, or work needs to survive handoffs and restarts. If ordinary docs, tests, and a short task are already enough, Agentic Workspace should stay unnecessary or minimal.

## What changes for an agent

An AW-enabled repository has a tiny bootstrap pointing to one canonical
[AW operating skill](.agentic-workspace/skills/workspace-startup/SKILL.md).
That skill teaches the agent how to work with current repository instructions,
configuration and owner state. Relevant specialized procedures are loaded only
when useful. Direct work stays direct.

For example, when changing authentication, the agent reads the applicable repo
policy, obtains current constraints or proof requirements when needed, makes the
change, and checks what the responsible owners can establish. A precise tool call
may help:

```bash
agentic-workspace start --target . --task "Update authentication token handling" --format json
```

The tool carries exact requests, actions and currentness. The agent supplies
intent, unresolved judgment and new material; it does not memorize a packet
protocol. A tool succeeding is separate from the requested outcome being complete.
See [everyday use](docs/everyday-use.md) for small practical examples.

An agent with only repository read access uses the same skill and its generated
read profile to reach relevant owner sources. It can recover recorded intent and
context, while runtime availability, local state and fresh proof remain unknown.
This read path grants no permission to mutate or approve work.

## First-party modules

Most of Agentic Workspace's current higher-level functionality is provided by three first-party modules. They are independently selectable rather than mandatory: a repository can use the Workspace routing/control layer on its own or add the modules that solve recurring problems.

- **Memory** preserves repository knowledge that is costly to rediscover, so later agents can recover useful lessons, constraints, and orientation without repeating the same investigation.
- **Planning** preserves active work and execution continuity across sessions and agents: what is being worked on, the intent and boundaries that matter, what remains, and where continuation belongs.
- **Verification** preserves reusable verification procedures, evidence, and known gaps so agents can apply the right checks and keep completion claims aligned with what has actually been established.

Workspace connects these capabilities with task-shaped routing, repository instructions, ownership, and current action and completion boundaries. A module becomes relevant when its capability matters without making unrelated tasks carry its terminology or procedure.

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

The main skill supplies procedure; repository instructions and configuration
supply policy; Planning, Memory and Verification retain their own state and
evidence. Rust-backed tools answer exact current questions and perform admitted
bounded operations. These roles stay separate, without a required resolve/act/
reconcile phase machine for every task.

Repository instructions can also be dynamic rather than purely static: repo-owned configuration, scoped guidance, skills, verification rules, and capability state can change what AW surfaces or requires for a particular task. The deeper architecture for programmable instruction composition is described in [`docs/architecture.md`](docs/architecture.md).

## Interfaces and implementation authority

The ordinary deterministic product authority is the **native Rust CLI/core**. Public operations resolve and execute through that shared native authority rather than through independent language-specific implementations.

The coordinated Python distribution carries the native executable together with package and payload support. Generated TypeScript CLI packages and JSON `start`/`invoke` envelopes are thin first-class projections/adapters over the same Rust-owned operation semantics. They are not peer semantic runtimes, and adapter-specific code should not become a second source of ordinary domain behavior.

See [`docs/package/contracts.md`](docs/package/contracts.md) for the current contract and generated-interface model.

## Getting started

Use the installation guide for current installation and adoption guidance:

[`docs/agentic-workspace-install.md`](docs/agentic-workspace-install.md)

During reconstruction, an explicitly published `preview-vMAJOR.MINOR.PATCH` GitHub prerelease may be used for external testing. Its `agentic-workspace-preview-release-manifest.json` and `distribution-install-readiness.json` identify the exact immutable preview subject and hash-bound root-wheel install command. A preview is unstable and **non-support-bearing**: it does not establish Stable/1.0 status or a general platform-support claim. If no such prerelease has been published, there is no public preview install identity to infer from the reconstruction branch.

The native reconstruction has passed [exact artifact admission](https://github.com/rickardvh/agentic-workspace/issues/2990), with Linux x64 as its evidenced platform. Admission and a canonical branch move do not publish a stable release or change package maturity. The install reference tracks the latest stable release, `v0.51.0`, which predates this native implementation; see the [installation guide](docs/agentic-workspace-install.md) before selecting bytes.

The later support-bearing install path is a stable `vMAJOR.MINOR.PATCH` GitHub Release. Each coordinated stable release publishes `distribution-install-readiness.json`, which identifies the project-controlled root wheel and its SHA-256-bound install command; mutable branches and ordinary registry resolution are not support-bearing identities unless release policy says otherwise.

After adoption, use the canonical skill and the installed CLI's `--help`.
The native tools are `start`, `invoke`, `resources` and `worker`; domain requests
come from their current owners. Historical `init`, `defaults`, `implement`,
`proof` and module subcommands are not an installed native adoption procedure.
The [installation guide](docs/agentic-workspace-install.md) states the current
preview and bootstrap limitations explicitly.

Agentic Workspace keeps its checked-in footprint deliberately small. Selected modules add their own owned state, while implementation packages, generated clients, caches, and local diagnostics keep separate ownership and lifecycle boundaries.

See [`docs/package/installed-surfaces.md`](docs/package/installed-surfaces.md) for the installed-footprint model.

## Scope and trust

Agentic Workspace complements the repository's existing source, documentation, tests, review process, and issue tracker. It does not replace them or turn the repository into a separate knowledge database or task-management system. It guides and constrains how an agent operates without scripting ordinary implementation choices.

**Agentic Workspace is not a sandbox.** Treat the repository and its configured verification or executor commands as trusted before allowing AW to execute them. Admitted shell routes inherit the caller's filesystem and credential authority, and external issue, PR, or service text should be treated as data rather than execution permission.

See [`docs/security/threat-model.md`](docs/security/threat-model.md) for the full trust and supply-chain boundary.

## Learn more

- [`docs/package/overview.md`](docs/package/overview.md) — product model and source ownership.
- [`docs/agentic-workspace-install.md`](docs/agentic-workspace-install.md) — installation and adoption.
- [`docs/package/modules.md`](docs/package/modules.md) — first-party modules and ownership.
- [`docs/architecture.md`](docs/architecture.md) — operating context, dynamic control, programmable instructions, and extension boundaries.
- [`docs/extension-boundary.md`](docs/extension-boundary.md) — module and external-extension architecture.
- [`docs/glossary.md`](docs/glossary.md) — stable public vocabulary.
- [`docs/evidence-and-support.md`](docs/evidence-and-support.md) — deterministic and live evidence plus support limits.
- [`docs/security/threat-model.md`](docs/security/threat-model.md) — trust and supply-chain boundary.
- [`docs/package/contracts.md`](docs/package/contracts.md) — machine-readable contracts and generated references.
- [`docs/index.md`](docs/index.md) — full documentation map.

Exact current values live in the [CLI catalogue](docs/reference/cli-catalogue.md), [installed-surface catalogue](docs/reference/installed-surface-catalogue.md), and [support-bearing install reference](docs/reference/support-bearing-install.md), rather than duplicated conceptual prose.

When maintaining Agentic Workspace itself rather than using it in another repository, follow [`AGENTS.md`](AGENTS.md) and the [`maintainer documentation`](docs/maintainer/index.md).
