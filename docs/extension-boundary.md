# Integrate an agent or tool

Use this guide when you are adding AW calls to an agent host, editor or other
application. The integration transports requests and shows their results; AW
continues to evaluate repository rules and manage its own state.

You do not need an integration to use AW with an agent that can read repository
instructions and run the CLI. Start with [Getting started](agentic-workspace-install.md)
for that path. A project-specific rule or procedure belongs in
[repository configuration](customization.md), not in a new host adapter.

## Choose how to call AW

Use the [Rust, Python or TypeScript API](architecture/shared-rust-core.md) that fits
your application, or invoke the [CLI](package/commands.md) and consume JSON.
CLI, Python and TypeScript integrations use the native executable pair installed
for their platform. Rust applications can call the linked core directly. Keep
model credentials and host session management in your application.

Begin with a context query, not an automatic execution loop. Supply the target
repository, the current task, and known affected paths. Show the returned context
and applicable constraints to the agent; load additional detail only when needed.

## Handle the next step

AW can return information, a request for material, a bounded question, an action,
or a restriction. The agent or user decides among legitimate alternatives. Your
adapter should preserve those distinctions rather than converting every response
into “run the next command.”

A typical interaction is:

1. Call `start` for the work context and present relevant information.
2. When a returned request needs new material or an answer, collect only that
   input and submit the same current request through `start`.
3. When an action is authorized, pass that exact action to `invoke`.
4. Show what happened and use the returned continuation or recovery route.

These are supported interactions, not mandatory phases for every task. An agent
may already have enough information to work directly. Selecting a skill helps it
follow a procedure; it does not authorize a write or satisfy a test requirement.

Keep the original target, task and affected paths with the exchange. Let AW check
whether the request still applies when it is used. Do not manufacture action IDs,
permissions or currentness markers, even when a hand-built object fits a schema.

## Preserve results across interruptions

A change and the query that follows it can succeed or fail separately. Your
adapter must not report a confirmed write as failed merely because continuation
was unavailable. Nor should it treat a timeout as proof that nothing happened.

Retain the exact result or recovery reference needed to determine what happened.
Use the responsible operation's recovery path for uncertain effects. When only
disposable context has been lost, query again with the current work context.
Do not rely on an earlier conversation as the only record of a committed effect.

## Support handoff without forwarding the whole session

For delegated work, use the Assignment packet supplied by AW. The `worker` tool
can present its entry context, expand selected inputs and assemble a return. Your
host supplies its transport and current capability facts; it must not invent a
successful worker launch, independent review or completed integration.

Returned material or a patch still needs admission and any required verification
in the receiving repository. Credentials stay with the host. See the
[delegation transport reference](maintainer/consequential-delegation.md) when
implementing that specific capability.

## Check the integration

Exercise an ordinary query, a request needing an answer, an authorized effect,
rejection after relevant inputs change, and recovery after interruption. Test
transport-specific risks such as lost fields, encoding or unavailable executables
without reimplementing AW's semantic rules in the adapter.

AW is not a sandbox: configured commands use the caller's filesystem and
credential access. Read the [security guide](security/threat-model.md) before
exposing effectful operations to an agent or remote client.

To introduce new deterministic domain behavior rather than transport existing
operations, use the [native module contract](module-capability-contract.md).
