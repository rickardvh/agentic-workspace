# Architecture

This page is for contributors deciding where a change belongs. To use AW in a
project, start with the [user guide](index.md). To call it from another program,
use the [APIs](architecture/shared-rust-core.md).

AW keeps agent procedure, project rules and saved component state separate so one
does not quietly become a competing copy of another.

## Main components

| Component | Responsibility |
| --- | --- |
| Skills | Reusable procedure for the agent, loaded when useful |
| Repository instructions and configuration | Project rules, preferences and scope |
| Planning, Memory, Verification and other components | Maintain their own task state, lessons, checking procedures or evidence |
| Rust core | Read current sources, combine the applicable rules, validate requests and perform supported operations |
| CLI and language clients | Present the shared Rust behaviour through commands and APIs |
| Agent or human | Interpret the task, choose among legitimate alternatives and do the programming work |

The repository's code, documentation and tests stay in their ordinary locations.
AW does not import them into a central knowledge model. It saves additional
information only when that makes later work cheaper or safer to continue.

## From a query to a change

A client supplies the repository, current task and any relevant paths or returned
request. The responsible AW components read their current sources. The Rust core
combines the facts, restrictions, questions and available actions into one result.

Most queries need only a compact answer. Optional detail stays behind links or
returned references.

A request asks the responsible component to interpret supplied information. That
component may prepare an action, identify a blocker or ask for a specific
judgement. Supplying a plausible operation name does not create permission.

Before changing files or running another effectful operation, AW checks that the
relevant inputs and permissions still match. A returned action identifies its
target and arguments so the caller does not have to reconstruct them.

If a change was confirmed but preparing the next response failed, keep the
confirmed change. If the operation may have happened but the result is unknown,
check what happened before trying it again.

These responsibilities are sometimes summarised as:

```text
Check what applies → Do the work → Update what matters
```

They are not workflow phases that the user must operate manually.

## Instructions and extensions

Ordinary project rules use [scoped instructions](customization.md). The
[instruction schema](reference/instruction-clause-program.md) is an implementation
reference for contributors, not a general-purpose language users are expected to
learn.

[Independent modules](module-capability-contract.md) add distinct capabilities
through the shared Rust interfaces. Repository configuration decides whether a
module is enabled. The Rust core should not need module-specific special cases
merely to recognise an extension.

[External adapters](extension-boundary.md) connect AW to agent hosts. They own
vendor-specific transport, credentials and sessions while reusing AW's existing
operations.

## Saved information

Planning keeps unfinished work, Memory keeps reusable lessons and Verification
keeps checking procedures and evidence. A human correction belongs in the place
that can apply it most reliably; it does not automatically become Memory.

Generated views and temporary request data are not new sources of truth. A fresh
agent should be able to recover relevant work from the saved project records
without having seen the earlier conversation.

Repository-only readers can inspect saved facts, but they cannot establish live
machine state, current test results or permission to change local state.

## Source layout

| Path | Work that belongs here |
| --- | --- |
| `src/core/` | Shared Rust behaviour and component implementations |
| `src/cli/rust/` | Public command parsing and forwarding |
| `src/cli/python/`, `src/cli/typescript/` | Installed language bindings |
| `src/core/contracts/`, `src/core/src/modules/*/contracts/` | Shared and component-specific schemas and contracts |
| `src/tooling/`, `src/adapters/codex/` | Maintainer tooling and provider integration |
| `.agentic-workspace/` | This repository's AW integration, settings and saved records |
| `docs/`, `tools/skills/` | Human documentation and repository procedures |

[System intent](../SYSTEM_INTENT.md) defines product direction; [design principles](design-principles.md)
explain trade-offs. Use the [contributor guide](maintainer/contributor-playbook.md)
for building and validating changes. AW does not provide an OS sandbox; see the
[threat model](security/threat-model.md).
