# How AW fits into a project

AW helps a coding agent find project guidance, continue unfinished work and reuse
lessons from earlier tasks. It works alongside the agent's normal editor, shell,
source tree and review process. Start with [Getting started](../agentic-workspace-install.md)
to try it; this page explains the model behind that experience.

## Keep project context where it belongs

Project documentation, code, tests and decisions remain in their existing files.
AW retains additional information only when it helps later work: for example,
where a task stopped, which procedure applies to a change, or what made an earlier
approach fail.

This is *operating context*: information that changes how an agent should approach
a task. It is not a second copy or index of everything in the repository.

## Apply the relevant part

A repository can define rules for particular paths or kinds of work. Skills
explain reusable procedures. The agent selects useful procedure by meaning;
AW's runtime checks current sources and applies their declared constraints.

The resulting information can include a required document, a checking procedure,
an unresolved question or an available action. Unrelated capabilities need not
appear. The agent still decides how to implement the requested change.

## Preserve useful results

[Planning](modules.md#planning) can retain an unfinished task's outcome and next
step. [Memory](modules.md#memory) can retain advice with its assumptions.
[Verification](modules.md#verification) can retain checking procedures and evidence.
These serve different purposes: a lesson does not become policy, and a previous
successful check does not automatically prove changed code.

The CLI and Rust, Python and TypeScript APIs use one Rust implementation for
current queries and controlled updates. The repository's AW skill teaches the
agent when to use them, without imposing a command sequence on every task.

[Configure your project](../customization.md) for rules and procedures;
[Your repository and data](installed-surfaces.md) for saved files and removal;
[Architecture](../architecture.md) for implementation boundaries.
