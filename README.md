# Agentic Workspace

[![PyPI](https://img.shields.io/pypi/v/agentic-workspace)](https://pypi.org/project/agentic-workspace/)
[![npm](https://img.shields.io/npm/v/%40agentic-workspace%2Fworkspace-cli)](https://www.npmjs.com/package/@agentic-workspace/workspace-cli)
[![crates.io](https://img.shields.io/crates/v/agentic-workspace-cli)](https://crates.io/crates/agentic-workspace-cli)

**Persistent, task-relevant project context for coding agents.**

Agentic Workspace (AW) is an open-source developer tool you add to a Git repository to give coding agents persistent, task-relevant project context across sessions.

AW provides skills and command-line tools for finding project guidance, saving unfinished work and lessons, and checking whether earlier verification still applies.

Keep your existing coding agent, editor, source tree, tests and review process. Your project can use any programming language or framework.

[Get started](https://github.com/rickardvh/agentic-workspace#get-started) · [Customise repository behaviour](https://github.com/rickardvh/agentic-workspace/blob/master/docs/customization.md) · [Everyday use](https://github.com/rickardvh/agentic-workspace/blob/master/docs/everyday-use.md) · [Documentation](https://github.com/rickardvh/agentic-workspace/blob/master/docs/index.md) · [Releases](https://github.com/rickardvh/agentic-workspace/releases)

## Why AW?

**Knowledge about a repository belongs with the repository.** Useful project knowledge should survive a change of session, developer or agent provider, rather than remain trapped in private conversations.

**Not everything about a repository is relevant all the time.** Loading all accumulated guidance and state into every session replaces rediscovery with context overload.

Scoped instructions and on-demand skills are useful foundations. Instructions set rules; skills explain reusable procedures. Neither an ever-longer instruction file nor a growing skill catalogue, by itself, keeps track of where a task stopped or whether earlier evidence still applies.

AW builds on both with saved task records, lessons and verification evidence, plus tools for reading and updating them. The aim is to reduce the cost of completing and maintaining work:

| Team benefit | How AW helps |
| --- | --- |
| Less repeated investigation | Find relevant rules, sources and reusable procedures without loading unrelated guidance. |
| Cheaper continuation and handoffs | Preserve intent, accepted progress and remaining work; give the receiving agent the relevant constraints and expected result. |
| Fewer repeated explanations | Save project corrections as scoped instructions and useful lessons as advice for later work. |
| More focused verification | Find relevant checking procedures, reuse evidence when it still applies and identify what remains unverified. |
| Less dependence on one agent provider | Keep shared project context in the repository rather than one provider's conversation history. |

**Small tasks stay small.** A typo fix does not need Planning, Memory, Verification, delegation, or another artefact merely because those capabilities are available.

## How it works

A small entry in `AGENTS.md` points to the repository's `workspace-startup` skill. It teaches the agent when to read project sources, load a specialised procedure or query AW's tools.

The Rust-backed runtime reads applicable rules and saved records, reports relevant requirements and available operations, and checks current sources and permissions before supported updates. The agent still makes implementation decisions and uses its ordinary development tools.

```text
Find the relevant context → Do the work → Update what matters
```

Source code, documentation, tests and decisions stay in their existing homes. AW points agents to those sources and saves useful working context alongside them, rather than copying the repository or the conversation into a second knowledge system.

[Everyday examples](https://github.com/rickardvh/agentic-workspace/blob/master/docs/everyday-use.md) · [Product model](https://github.com/rickardvh/agentic-workspace/blob/master/docs/package/overview.md) · [Architecture](https://github.com/rickardvh/agentic-workspace/blob/master/docs/architecture.md)

## Trust and support

**AW is not a sandbox.** Repository-configured commands run with the caller's filesystem access and credentials. Review the repository and the commands it can run before allowing them to execute. Credentials belong in the agent host or environment's credential facilities, not in checked-in AW files.

AW's controlled operations and checking support do not replace human judgement, independent review, or existing security controls.

Exact package identities, installation commands, runtime versions, operating-system support, and prerelease/stable status live with the selected release and generated references instead of being copied into this landing page.

[Installation and setup](https://github.com/rickardvh/agentic-workspace/blob/master/docs/agentic-workspace-install.md) · [Threat model](https://github.com/rickardvh/agentic-workspace/blob/master/docs/security/threat-model.md) · [Evidence and support](https://github.com/rickardvh/agentic-workspace/blob/master/docs/evidence-and-support.md)

## Get started

Use a **Git working tree** and an agent that can read repository instructions and run commands. The machine must be able to run a supported AW distribution; your project's language and build system need not match it.

1. Install AW through npm, Python/uv, Cargo or a standalone release, either per repository or as a shared tool. Standalone binaries do not require a language toolchain. See the [Getting started guide](https://github.com/rickardvh/agentic-workspace/blob/master/docs/agentic-workspace-install.md) for platform requirements and installation commands.
2. From the Git working-tree root, run `agentic-workspace setup` using that installation and authorise the proposed integration. For a repository-local npm installation, use `npm exec --no -- agentic-workspace setup`.
3. Give your agent an ordinary task, such as correcting a documentation error.

Installation supplies the runtime; setup adds the `.agentic-workspace/` directory and a small `AGENTS.md` pointer. Review and commit the shared integration files, leaving ignored local state alone. Project rules and checking procedures still need to be defined; setup does not infer them.

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
