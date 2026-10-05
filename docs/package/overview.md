# How AW fits into a project

AW helps a coding agent find project guidance, continue unfinished work and reuse
lessons from earlier tasks. It works alongside the agent's normal editor, shell,
source tree and review process. Start with [Getting started](../agentic-workspace-install.md)
to try it; this page explains the model behind that experience.

## Keep project context where it belongs

Project documentation, code, tests and decisions remain in their existing files.
AW saves additional information only when it will help later work: for example,
where a task stopped, which procedure applies to a change, or what made an earlier
approach fail.

AW does not try to build a second copy or index of the repository. It keeps only
the extra working context that is expensive to reconstruct and useful to future
agents.

## Apply only what matters to this task

A repository can define rules for particular paths or kinds of work. Skills
explain reusable procedures. The agent chooses a useful procedure from the task;
AW checks the relevant current sources before presenting their requirements.

The result can include a document to read, a checking procedure, an unresolved
question or an available action. Unrelated capabilities stay out of the way. The
agent still decides how to implement the requested change.

## Save useful results in the right place

[Planning](modules.md#planning) can save an unfinished task's outcome and next
step. [Memory](modules.md#memory) can save advice together with its assumptions.
[Verification](modules.md#verification) can save checking procedures and evidence.
These serve different purposes: a lesson does not become policy, and a previous
successful check does not automatically prove changed code.

The CLI and Rust, Python and TypeScript APIs all use the same Rust implementation
for current queries and controlled updates. The repository's AW skill teaches the
agent when to use those tools without imposing a command sequence on every task.

For Rust applications, the stable calls are `operating::start` and
`operating::invoke`. The [API guide](../architecture/shared-rust-core.md) and
[compatibility policy](../release-and-versioning.md#package-compatibility-boundary)
define the supported calls and current capability discovery contract.

[Configure your project](../customization.md) for rules and procedures;
[Your repository and data](installed-surfaces.md) for saved files and removal;
[Architecture](../architecture.md) for implementation details.
