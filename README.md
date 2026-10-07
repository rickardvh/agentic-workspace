# Agentic Workspace

[![PyPI](https://img.shields.io/pypi/v/agentic-workspace)](https://pypi.org/project/agentic-workspace/)
[![npm](https://img.shields.io/npm/v/%40agentic-workspace%2Fworkspace-cli)](https://www.npmjs.com/package/@agentic-workspace/workspace-cli)
[![crates.io](https://img.shields.io/crates/v/agentic-workspace-cli)](https://crates.io/crates/agentic-workspace-cli)

**Persistent, task-relevant project context for coding agents.**

Agentic Workspace (AW) is an open-source developer tool you add to a Git repository to help coding agents carry useful project context across sessions.

It helps agents continue unfinished work, find applicable repository guidance, reuse procedures and lessons, and understand relevant verification state without loading everything into every task. The repository can use any programming language or framework.

Keep your existing agent, editor, source tree, tests, and review process. AW adds a small repository-owned layer around them.

[Customise repository behaviour](https://github.com/rickardvh/agentic-workspace/blob/master/docs/customization.md) · [Get started](https://github.com/rickardvh/agentic-workspace#get-started) · [Everyday use](https://github.com/rickardvh/agentic-workspace/blob/master/docs/everyday-use.md) · [Documentation](https://github.com/rickardvh/agentic-workspace/blob/master/docs/index.md) · [Releases](https://github.com/rickardvh/agentic-workspace/releases)

## Why AW?

Two ideas underpin AW:

**Knowledge about a repository belongs with the repository.** Useful project knowledge should not disappear with one agent conversation, machine or provider.

**Not everything about a repository is relevant all the time.** Loading all accumulated guidance and state into every session simply replaces rediscovery with context overload.

Repository instructions are a good home for durable rules, but continually adding every useful fact makes every agent consume an ever-growing body of guidance. Repository skills are a good home for reusable procedures, but not for changing work state, contingent lessons or verification evidence.

AW keeps those concerns separate, preserves the context that can change future work, and makes the relevant part cheap to reach:

| Need | What AW provides |
| --- | --- |
| Find the right guidance | Task-relevant instructions, source references, and reusable skills. |
| Continue interrupted work | Retained outcomes, constraints, accepted progress, blockers, and next actions. |
| Know what to verify | Relevant checking procedures, recorded evidence, and visible gaps. |
| Hand work to another agent | Clearly limited assignments with the context, constraints, and expected result spelled out. |
| Avoid repeated rediscovery | Useful lessons and corrections saved where later work will actually use them. |

The result should be less repeated investigation, fewer explanations from maintainers, cheaper handoffs, less unnecessary checking and fewer avoidable repair loops—not a larger prompt or another workflow to manage.

**Small tasks stay small.** A typo fix does not need Planning, Memory, Verification, delegation, or another artefact merely because those capabilities are available.

## What using it looks like

AW can help an agent find relevant project guidance and preserve useful working
context between sessions. The agent still reads the source, reasons about the
design and implements changes with its ordinary tools.

For work that spans sessions, Planning can preserve the intended outcome, accepted progress, unresolved questions, and next action. A later session can recover that state instead of reconstructing the previous conversation.

The same principle applies to lessons, verification and handoffs: preserve what will materially help later work, while checking that retained information still applies. Changed assumptions and missing evidence still need checking; an earlier successful result does not automatically apply to changed code.

[See everyday examples →](https://github.com/rickardvh/agentic-workspace/blob/master/docs/everyday-use.md)

## How it works

**Skills teach procedure. Repository instructions and configuration set policy. The relevant AW components keep their own current state and evidence. Tools provide current information and controlled operations. The agent supplies judgement.**

A small repository entry point leads the agent to the repository's `workspace-startup` skill. That skill explains how to reach relevant sources, ask the runtime for current facts when they matter, and load specialised procedures only when useful.

The underlying model is deliberately small:

```text
Find the relevant context → Do the work → Update what matters
```

Internally, AW works out which rules and saved facts apply, shows the actions that are currently available, and records relevant results afterward. The user does not have to operate a separate phase machine around every task.

Source code, documentation, tests, decisions, and other project material remain in their existing homes. AW points agents to those sources rather than copying the repository into a second knowledge system.

[Product model](https://github.com/rickardvh/agentic-workspace/blob/master/docs/package/overview.md) · [Architecture](https://github.com/rickardvh/agentic-workspace/blob/master/docs/architecture.md)

## Trust and support

**AW is not a sandbox.** Repository-configured commands run with the caller's filesystem access and credentials. Review the repository and the commands it can run before allowing them to execute. Credentials belong in the agent host or environment's credential facilities, not in checked-in AW files.

AW's controlled operations and checking support do not replace human judgement, independent review, or existing security controls.

Exact package identities, installation commands, runtime versions, operating-system support, and prerelease/stable status live with the selected release and generated references instead of being copied into this landing page.

[Installation and setup](https://github.com/rickardvh/agentic-workspace/blob/master/docs/agentic-workspace-install.md) · [Threat model](https://github.com/rickardvh/agentic-workspace/blob/master/docs/security/threat-model.md) · [Evidence and support](https://github.com/rickardvh/agentic-workspace/blob/master/docs/evidence-and-support.md)

## Get started

1. Install AW using any supported distribution, either as a dev dependency in your repo (recommended) or as a globally accessible tool on your computer. See
   [Getting started guide](https://github.com/rickardvh/agentic-workspace/blob/master/docs/agentic-workspace-install.md).
2. From your repo root, run `agentic-workspace setup` using that installation and
   authorise the proposed integration.
3. Give your agent an ordinary task, such as correcting a documentation error.

Installation supplies the runtime; setup adds the `.agentic-workspace/` directory and an `AGENTS.md`
pointer. Your agent follows that pointer during ordinary work.

## Your repository, your rules

AW is designed to fit around the project rather than reorganise it.

A simplified repository using AW looks like this:

```text
your-repository/
├── AGENTS.md              # Small AW-managed entry point inside your project file
├── src/, docs/, tests/    # Existing project contents
└── .agentic-workspace/    # AW integration plus optional saved component state
```

AW setup deliberately adds only a small set of files. Package-managed skills and setup metadata stay separate from your project's configuration, component records, machine-local data, and any output deliberately written back into the repository.

You can express a repository-wide correction in ordinary language:

> For this repository, read the API contract before changing public response fields.

Or make the scope explicitly local:

> Only on this machine, use this executable path when invoking AW.

The agent can save the change in the appropriate instruction or configuration file and verify that it was retained. A promise in chat is not a saved rule, and a local preference should not silently become shared repository policy.

Reusable methods belong in skills. Binding rules belong in instructions or configuration. Current work and evidence stay with the components that maintain them.

Setup, refresh, and removal use the same declared file set. Removing AW deletes only integration files that AW can verify it owns, preserves project configuration and saved component records, and refuses to erase edited or unrelated content merely because it sits under an AW path.

[Configuration reference](https://github.com/rickardvh/agentic-workspace/blob/master/docs/reference/workspace-config.md) · [Repository files](https://github.com/rickardvh/agentic-workspace/blob/master/docs/reference/installed-surface-catalogue.md)

## Add structure where it helps

AW includes optional first-party capabilities for recurring coordination costs:

**Planning** preserves unfinished work: intended outcome, constraints, progress, blockers, and next action.

**Memory** retains useful observations and lessons that would otherwise be expensive to rediscover. Advice can be reconsidered when its dependencies change; a note is not automatically policy.

**Verification** makes checking procedures, evidence, and known gaps reusable. Passing a check supports the claim it actually tests, not every claim about the finished work.

These are optional components, not mandatory workflow stages. Repositories can use what repays its cost and leave unrelated capabilities out of the current task's context.

Repository-specific rules and procedures do not require a new module. Modules are for distinct capabilities with their own responsibilities, including read-only facts; saving state is optional.

[Modules and extensions →](https://github.com/rickardvh/agentic-workspace/blob/master/docs/package/modules.md)

## Works with agents rather than replacing them

Agentic Workspace is not an autonomous coding agent. It gives the agent already working in the repository better project context and controlled ways to read or update AW-managed information.

An agent with runtime access can query the current records maintained by AW components and use supported operations. A repository-only reviewer can follow the same startup skill and generated read profile to recover recorded goals, constraints, progress, and advice, while live machine state, current test results, and permission to make changes remain unknown.

The product's shared behaviour lives in one Rust core. Native, Python, TypeScript, and JSON interfaces call that same implementation instead of defining separate workflow behaviour. The host project's implementation language does not need to match AW's runtime implementation.

Host integrations still differ. Provider independence does not mean every agent host discovers skills identically or every model follows repository guidance perfectly; current support and evidence remain release- and environment-bound.

[Evidence and support →](https://github.com/rickardvh/agentic-workspace/blob/master/docs/evidence-and-support.md)

## Learn more

**Use AW:** [Installation and adoption](https://github.com/rickardvh/agentic-workspace/blob/master/docs/agentic-workspace-install.md) · [Everyday use](https://github.com/rickardvh/agentic-workspace/blob/master/docs/everyday-use.md) · [Configuration](https://github.com/rickardvh/agentic-workspace/blob/master/docs/reference/workspace-config.md)

**Understand AW:** [Product overview](https://github.com/rickardvh/agentic-workspace/blob/master/docs/package/overview.md) · [Architecture](https://github.com/rickardvh/agentic-workspace/blob/master/docs/architecture.md) · [Design principles](https://github.com/rickardvh/agentic-workspace/blob/master/docs/design-principles.md) · [Modules](https://github.com/rickardvh/agentic-workspace/blob/master/docs/package/modules.md)

**Look up details:** [CLI reference](https://github.com/rickardvh/agentic-workspace/blob/master/docs/reference/cli-catalogue.md) · [Installed surfaces](https://github.com/rickardvh/agentic-workspace/blob/master/docs/reference/installed-surface-catalogue.md) · [Full documentation](https://github.com/rickardvh/agentic-workspace/blob/master/docs/index.md)

## Contributing

For changes to Agentic Workspace itself, start with the [contributor playbook](https://github.com/rickardvh/agentic-workspace/blob/master/docs/maintainer/contributor-playbook.md). Use the repository's [issue templates](https://github.com/rickardvh/agentic-workspace/issues/new/choose) to report a problem or propose a change.

Contributions should make useful work easier to complete, continue, or verify while keeping unnecessary context, framework surface, and repository residue low.

## Licence

[MIT](https://github.com/rickardvh/agentic-workspace/blob/master/LICENSE).
