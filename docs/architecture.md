# Architecture

This page is for contributors deciding where a change belongs. To use AW in a
project, start with the [user guide](index.md). To call it from another program,
use the [APIs](architecture/shared-rust-core.md).

AW separates agent procedure, project rules and retained state so that each can
change without becoming a second source of truth for the others.

## Main components

| Component | Responsibility |
| --- | --- |
| Skills | Reusable procedure for the agent, loaded when useful. |
| Repository instructions and configuration | Project rules, preferences, scope and authorisation. |
| Domain owners | The component responsible for a particular kind of state, evidence or effect, such as Planning or Verification. |
| Rust core | Read current sources, compose applicable constraints, validate requests and execute supported effects. |
| CLI and language clients | Transport and presentation over that core. |
| Agent or human | Decide meaning, choose among legitimate alternatives and perform the programming work. |

The repository's code, documentation and tests stay in their ordinary locations.
AW does not import them into a central knowledge model. Its retained operating
context exists only where it reduces future investigation or makes work safer to
continue.

## From a query to an effect

A client supplies the repository, current task, affected paths and any selected
request. Relevant owners observe their sources. The core combines their facts,
restrictions, questions and available actions into a current response.

Most queries need only a compact result. Optional detail stays behind exact
references. Information that affects the next decision needs its scope and
consequence explained when delivered, not in a later message.

A request asks an owner to interpret supplied material. That owner may prepare an
action, identify a blocker or ask for a bounded judgement. The caller cannot turn
a request into permission by supplying a plausible operation name.

Before an effect, AW rechecks the action's material dependencies and authority.
The returned action binds its target, arguments, effects and currentness.
Lower-authority advice cannot widen a repository restriction. Conflicting or
unknown enforcing requirements remain visible and constrain the affected action
or claim rather than unrelated work.

After execution, effect evidence and continuation are separate. A confirmed write
survives a failure to produce the next response. An uncertain effect requires
recovery, not replay as a new operation. A settled owner is not proof that the
user's larger task is complete.

These responsibilities are sometimes described as *resolve → act → reconcile*.
They are not mandatory workflow phases for the model or the user.

## Instructions and extensions

Ordinary project rules use [scoped instructions](customization.md). Internally,
applicable clauses can surface context, express a preference, require evidence or
an operation, or restrict an effect. This representation executes nothing itself
and grants no blanket permission. The [instruction schema](reference/instruction-clause-program.md)
is an implementation reference, not a general-purpose public programming language.

[Independent modules](module-capability-contract.md) add deterministic domain
behaviour through the Rust owner interface. Their registration describes the
capability; repository configuration separately authorises it. A read-only module
needs no fake state or mutation hook. Shared semantics belong in core, but core
must not learn each module's domain or identity merely to recognise it.

[External adapters](extension-boundary.md) integrate existing operations with agent
hosts. They keep transport, credentials and vendor sessions outside core. Skills
can help use either kind of capability; skill selection does not change authority.

## Persistence and learning

Planning keeps continuation, Memory keeps advisory lessons, and Verification keeps
procedures and evidence. A human correction belongs with the strongest appropriate
source, not automatically in Memory. Useful results may improve later work, but
one success does not create policy and one observation need not create a record.

Generated context and disposable carriers are projections, not new owners. A
fresh consumer should recover relevant current work from retained sources without
having witnessed the conversation. Missing local effect evidence remains an
explicit limitation. Repository-only readers can inspect recorded facts but
cannot establish runtime capability, fresh proof or permission to mutate state.

## Source layout

| Path | Work that belongs here |
| --- | --- |
| `crates/agentic-workspace-core/` | Shared deterministic behaviour and native state/effect owners. |
| `crates/agentic-workspace-cli/` | Public command parsing and forwarding. |
| `src/agentic_workspace/`, `bindings/node/` | Installed language bindings and transport declarations. |
| `src/agentic_workspace/contracts/` | Declarative contracts and schemas, including retained maintenance formats. |
| `packages/`, other Python source | Source-development and maintenance machinery; not a second installed semantic runtime. |
| `.agentic-workspace/` | This repository's own AW integration, policy and retained state. |
| `docs/`, `tools/`, `scripts/` | Human documentation and repository-specific maintenance tools. |

[System intent](../SYSTEM_INTENT.md) owns product direction; [design principles](design-principles.md)
explain tradeoffs. Use the [contributor guide](maintainer/contributor-playbook.md)
for building and validating changes. AW's operation boundaries are not an OS
sandbox; see the [threat model](security/threat-model.md).
