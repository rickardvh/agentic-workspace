# Integrate an agent or tool

Use this guide when adding AW calls to an agent host, editor or other application.
The integration sends requests and displays results; AW itself continues to apply
repository rules and manage AW-owned records.

You do not need a custom integration when an agent can read repository
instructions and run the CLI. Start with [Getting started](agentic-workspace-install.md)
for that path.

## Call AW through a supported interface

Use the [Rust, Python or TypeScript API](architecture/shared-rust-core.md), or call
the [CLI](package/commands.md) and consume JSON. Keep model credentials, provider
sessions and other host-specific state in the host application.

The stable Rust embedding calls are `operating::start` and `operating::invoke`;
other public core modules are outside that promise. Inspect `start`'s current
capability contract for request schemas and operation declarations, then carry
the exact returned requests/actions. The [compatibility policy](release-and-versioning.md#package-compatibility-boundary)
defines this boundary; package versions alone do not establish operation compatibility.

Start by asking AW what applies to the current task. Supply the target repository,
the task and any known changed paths. Present relevant returned information to the
agent; load optional detail only when needed.

## Preserve the kind of result AW returned

AW may return:

- information;
- a request for more input;
- a specific question;
- an available action;
- a restriction.

Do not collapse all of these into “run the next command”.

A typical interaction is:

1. call `start` for the task;
2. when AW asks for information or an answer, supply only that requested input;
3. when AW returns an action that is allowed, pass that exact action to `invoke`;
4. show the result and follow any returned recovery or next-step information.

These are supported interactions, not mandatory phases for every task. An agent
may already have enough information to work directly.

Keep the original target, task and changed paths with follow-up calls. Let AW
check whether a returned request still applies. Do not manufacture action IDs,
permissions or source hashes merely because a hand-written object matches a
schema.

## Handle interruptions safely

A repository change and the response that follows it can fail independently.

If AW confirmed that a change happened, keep that result even when a later
response fails. If a timeout or interruption leaves the outcome unknown, use the
returned recovery information or inspect the current state before trying the
operation again.

Do not rely on chat history as the only record of a confirmed external change.

## Delegated work

For delegated work, use the Assignment information AW returns. The `worker`
tool can provide the receiving agent's task context and assemble its result. The
host remains responsible for actually starting the worker and reporting its real
capabilities.

A returned patch or review still needs normal integration and verification in the
receiving repository. It does not automatically count as independent approval.

## Test the integration

Exercise at least:

- an ordinary query;
- a request that needs an answer;
- a permitted repository change;
- rejection after relevant inputs change;
- recovery after an interrupted operation.

Add integration tests only for failures the transport can cause itself, such as
lost fields, encoding errors or unavailable executables. Do not duplicate AW's
shared behavioural tests in every adapter.

AW is not a sandbox. Configured commands run with the caller's filesystem and
credential access. Read the [security guide](security/threat-model.md) before
allowing an agent or remote client to trigger repository changes.

To add reusable behaviour rather than a host integration, use the
[module interface](module-capability-contract.md).
