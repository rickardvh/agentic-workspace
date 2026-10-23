# Knowledge routing and source authority

Use this page to choose the source that can guide a task and understand what it
can establish. Exact commands and response fields belong in the
[CLI guide](commands.md), [API guide](../architecture/shared-rust-core.md) and
the contract returned by the installed runtime.

AW helps the agent find relevant context. A generated view, saved lesson or chat
summary does not silently replace the document or decision it describes.

## Choose the source for the question

| Question | Start with | What it can establish |
| --- | --- | --- |
| What rules apply? | Applicable instructions, configuration and governing documents | The declared rule and scope |
| How do I perform a recurring task? | The relevant skill and selected references | Procedure and prerequisites |
| What was requested? | The current user request and relevant issue or PR | Intended outcome and acceptance conditions |
| Where did work stop? | The selected Planning record | Recorded progress, decisions and next step |
| What lesson might help? | Relevant Memory advice and its dependencies | An observation subject to reconsideration |
| What was checked? | Verification evidence and its exact subject | The result and scope of those checks |
| Does an external fact still hold? | Its authoritative publisher | Current information, when retrieved and applicable |

A locator or signature identifies material; it does not prove it true. An agent's
interpretation remains an interpretation. Local preferences cannot relax shared
requirements, and useful advice does not automatically become policy.

## Check relevance before loading detail

Begin with the task, affected paths and applicable repository instructions.
Follow the startup skill and select a specialist procedure when its information
can change the next decision. A matching path or issue mention identifies a
candidate; it does not by itself establish a requirement.

Use a compact response first and follow a returned reference for needed detail.
Keep the original work context with follow-up calls; the
[CLI example](commands.md#answer-a-returned-question) shows the transport.

An API contract may guide implementation; a required test result may constrain a
completion claim. Use the restriction's actual scope rather than treating every
missing fact as a reason to stop all work.
[Knowledge gates](knowledge-gates.md) explains those distinctions.

## Check whether the source still applies

A checked-in revision identifies the bytes examined. It does not establish that a
handwritten explanation agrees with the implementation. Check command descriptions
against the installed executable's help and current capability contract, and
generated references against their named source.

Reconsider evidence when relevant inputs change. A passing test on earlier code,
an old issue comment or advice with obsolete assumptions may explain history
without supporting today's decision. Verify external facts when the task depends
on their current state.

For conflicting sources, identify the statements, revisions, scopes and practical
consequence. Use the responsible source's correction or decision procedure.
Do not silently make a lower-authority interpretation binding. If a needed source
is unavailable, keep that uncertainty explicit and continue independent work.

## Retain meaning in its existing home

Keep code, contracts and decisions in their canonical files. Use Planning for
unfinished work, Memory for reusable advice and Verification for checking
procedures and evidence. Binding corrections belong in instructions,
configuration or the governing document.

Prefer a locator and relevance explanation to a copied manual or issue thread.
Retain enough assumptions to reconsider advice. Save nothing when the code,
tests and PR already make the result recoverable.

The current CLI uses `start` for context and returned questions, and `invoke` for
exact prepared actions. Older command names and packet layouts in dated evidence
describe their original subjects; they are not fallback APIs.
See the [current command catalogue](../reference/cli-catalogue.md).
