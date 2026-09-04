# V1 operating contract

The public product has two commands.

- `start` compiles current contributions from relevant source owners.
- `invoke` executes the exact typed invocation selected by that decision.

The decision reducer accepts normalized contributions containing an owner,
revision, facts, blockers, candidate actions, claim bounds, and terminal state.
It does not accept a rendering consumer. Equal source inputs therefore produce
the same semantic answer through the CLI and Python API.

An operation is identified by a stable ID and owns one input schema, effect set,
and handler. The dispatcher validates only the selected operation's values. It
rejects stale revisions, changed action authority, invalid values, widened
effects, and reused idempotency keys with different inputs. A successful result
contains the next decision, so no checkpoint, work-thread, carry, final-response,
or generic continuation model is needed.

No Workspace files are created for direct work. Planning, Memory, Verification,
and external modules contribute only when relevant.
