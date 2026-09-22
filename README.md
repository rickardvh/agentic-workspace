# Agentic Workspace

[![PyPI](https://img.shields.io/pypi/v/agentic-workspace)](https://pypi.org/project/agentic-workspace/)
[![npm](https://img.shields.io/npm/v/%40agentic-workspace%2Fworkspace-cli)](https://www.npmjs.com/package/@agentic-workspace/workspace-cli)
[![crates.io](https://img.shields.io/crates/v/agentic-workspace-cli)](https://crates.io/crates/agentic-workspace-cli)

**Persistent operating context and dynamic control for coding agents.**

Agentic Workspace (AW) helps coding agents enter a repository with the right guidance, continue unfinished work across sessions, and preserve useful lessons without turning every task into a workflow.

It builds on repository instructions and skills with persistent, source-owned context and a small Rust-backed tool surface for exact current information and bounded operations. Keep your existing agent, editor, source tree, tests, and review process; AW connects them to the operating context that matters for the task at hand.

[Customise repository behaviour](https://github.com/rickardvh/agentic-workspace/blob/master/docs/customization.md) · [Get started](https://github.com/rickardvh/agentic-workspace#get-started) · [Everyday use](https://github.com/rickardvh/agentic-workspace/blob/master/docs/everyday-use.md) · [Documentation](https://github.com/rickardvh/agentic-workspace/blob/master/docs/index.md) · [Releases](https://github.com/rickardvh/agentic-workspace/releases)

## Why AW?

A repository instruction file can explain how to work in a project. By itself, it cannot tell a new session where a multi-step task stopped, which retained lesson is relevant now, whether earlier verification still supports a claim, or which deeper procedure is worth loading for this change.

As work spans sessions and agents, that context has to come from somewhere. Without a deliberate home, it tends to disappear into chat, duplicate into prose, or be reconstructed from source, issues, and history.

AW keeps only the operating context whose availability can materially change agent behaviour, then makes the relevant part cheap to reach:

| Need | What AW provides |
| --- | --- |
| Find the right guidance | Task-relevant instructions, source references, and reusable skills. |
| Continue interrupted work | Retained outcomes, constraints, accepted progress, blockers, and next actions. |
| Know what to verify | Relevant checking procedures, recorded evidence, and visible gaps. |
| Hand work to another agent | Bounded assignments with explicit context, constraints, and return expectations. |
| Avoid repeated rediscovery | Useful lessons and corrections retained with the appropriate owner. |

The goal is less repeated explanation, searching, handoff reconstruction, and repair—not a larger prompt or a new workflow to manage.

**Small tasks stay small.** A typo fix does not need Planning, Memory, Verification, delegation, or another artefact merely because those capabilities are available.

## What using it looks like

AW can help an agent find relevant project guidance and preserve unfinished work
between sessions. The agent still reads the source, reasons about the design and
implements changes with its ordinary tools.

For example, imagine an API change that spans two sessions in a repository with
API guidance and verification procedures configured:

> Add pagination to the users API without breaking existing clients.

The agent can use AW to find the relevant contract, load a useful implementation
procedure and identify the checks expected for this change.

If work stops partway through, Planning can preserve the intended outcome, accepted progress, unresolved questions, and next action.

In a later session:

> Continue the pagination work.

The next agent can recover that continuation rather than reconstructing the previous conversation. Changed assumptions and missing evidence remain things to check; a recorded result is not automatically fresh proof.

The same principle applies to a handoff: preserve enough for the receiving agent to do bounded work without copying the entire parent session. Returned work still needs appropriate integration and verification.

[See everyday examples →](https://github.com/rickardvh/agentic-workspace/blob/master/docs/everyday-use.md)

## How it works

**Skills teach procedure. Repository instructions and configuration set policy. Domain owners hold current state and evidence. Tools provide exact current information and controlled operations. The agent supplies judgement.**

A small repository entry point leads the agent to AW's canonical `workspace-startup` skill. That skill explains how to reach relevant sources, ask the runtime for current facts when they matter, and load specialised procedures only when useful.

The underlying model is deliberately small:

```text
Find the relevant context → Do the work → Update what matters
```

Internally, AW resolves a compact operating contract, exposes supported actions, and reconciles their consequences afterward. That machinery is a substrate for the agent, not a phase machine the user has to operate around every task.

Source code, documentation, tests, decisions, and other canonical repository material remain in their existing homes. AW routes to those sources rather than importing the repository into a second knowledge system.

[Product model](https://github.com/rickardvh/agentic-workspace/blob/master/docs/package/overview.md) · [Architecture](https://github.com/rickardvh/agentic-workspace/blob/master/docs/architecture.md)

## Trust and support

**AW is not a sandbox.** Repository-configured commands run with the caller's filesystem and credential authority. Review the repository and its execution routes before allowing them to run. Credentials belong in the host or environment's credential facilities, not checked-in AW state.

AW's operation boundaries and verification support do not replace human judgement, independent review, or existing security controls.

Exact package identities, installation commands, runtime versions, operating-system support, and prerelease/stable status are deliberately kept in release-bound or generated owners instead of copied into this landing page.

[Installation and adoption](https://github.com/rickardvh/agentic-workspace/blob/master/docs/agentic-workspace-install.md) · [Threat model](https://github.com/rickardvh/agentic-workspace/blob/master/docs/security/threat-model.md) · [Evidence and support](https://github.com/rickardvh/agentic-workspace/blob/master/docs/evidence-and-support.md)

## Get started

1. Install AW for this repository with a pinned version, or deliberately share
   one installation across repositories. Choose npm, Python/uv, Cargo or a
   standalone release archive in the
   [Getting started guide](https://github.com/rickardvh/agentic-workspace/blob/master/docs/agentic-workspace-install.md).
2. From your Git working-tree root, run `setup` with that installation's
   invocation and authorise the proposed integration.
3. Give your agent an ordinary task, such as correcting a documentation error.

Installation supplies the runtime; setup adds the AW enclave and an AGENTS.md
pointer. Your agent then follows that pointer without a manual command sequence
around each task. Keep using the chosen installation's invocation so repositories
with different pinned versions remain independent.

## Your repository, your rules

AW is designed to fit around the project rather than reorganise it.

A simplified host repository looks like this:

```text
your-repository/
├── AGENTS.md              # Small managed entry point inside a repo-owned file
├── src/, docs/, tests/    # Existing project contents
└── .agentic-workspace/    # Package integration plus optional owner state
```

The current public adoption footprint is Configuration-owned and deliberately small. Package-managed skills, ownership/read-profile metadata, provenance, and adoption identity stay distinct from repo-owned configuration, module-owned state, local data, and promoted output.

You can express a repository-wide correction in ordinary language:

> For this repository, read the API contract before changing public response fields.

Or make the scope explicitly local:

> Only on this machine, use this executable path when invoking AW.

The agent can route the change to the appropriate instruction or configuration owner and verify whether it was retained. A promise in chat is not a saved rule, and a local preference should not silently become shared repository policy.

Reusable methods belong in skills. Binding rules belong in instructions or configuration. Current work and evidence stay with the capabilities responsible for them.

The same Configuration-owned footprint is used for adoption, refresh, and removal. De-adoption removes only authenticated package-owned integration, preserves repo-owned configuration and domain state, and refuses to erase edited or unowned content merely because it sits under an AW path.

[Configuration reference](https://github.com/rickardvh/agentic-workspace/blob/master/docs/reference/workspace-config.md) · [Repository footprint](https://github.com/rickardvh/agentic-workspace/blob/master/docs/reference/installed-surface-catalogue.md)

## Add structure where it helps

AW includes optional first-party capabilities for recurring coordination costs:

**Planning** preserves execution continuity: intended outcome, constraints, progress, blockers, and next action.

**Memory** retains useful observations and lessons that would otherwise be expensive to rediscover. Advice can be reconsidered when its dependencies change; a note is not automatically policy.

**Verification** makes checking procedures, evidence, and known gaps reusable. Passing a check supports the claim it actually tests, not every claim about the finished work.

These are peer capabilities, not mandatory workflow stages. Repositories can use what repays its cost and leave unrelated capabilities out of the current task's context.

Repository-specific rules and procedures do not require a new module. Modules are for independently owned domain capabilities, including read-only facts; persistence is optional.

[Modules and extensions →](https://github.com/rickardvh/agentic-workspace/blob/master/docs/package/modules.md)

## Works with agents rather than replacing them

Agentic Workspace is not an autonomous coding agent. It gives the agent already working in the repository better operating context and safer repository-native control.

An agent with runtime access can query current owner state and use supported operations. A repository-only reviewer can follow the same canonical skill and generated read profile to recover relevant recorded intent, constraints, progress, and advice, while live machine state, fresh proof, and effect permission remain unknown.

The ordinary deterministic product semantics live in a shared Rust core. Native, Python, TypeScript, and JSON-facing surfaces project or bind that authority rather than defining separate workflow behaviour. The host project's implementation language does not need to match AW's runtime implementation.

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
