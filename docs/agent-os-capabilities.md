# Long-term capability ideas

This page records long-term product ideas. It is not the current user guide, a
backlog or a promise to create more packages.

For current behaviour, use [Documentation](index.md) and
[How AW fits into a project](package/overview.md). For current packaging direction,
see [Ecosystem direction](ecosystem-roadmap.md).

## Current product shape

AW currently provides:

- repository setup and task-relevant guidance;
- Memory for reusable lessons;
- Planning for unfinished work;
- Verification for reusable checks and evidence;
- one shared Rust implementation behind the CLI and language APIs.

These are product components, not mandatory workflow stages.

## Capabilities that may remain internal

Several useful behaviours do not need their own product identity:

- choosing the relevant guidance for a task;
- checking which repository files AW manages;
- protecting generated/package-managed files;
- handling interrupted writes;
- reducing merge conflicts in shared AW records;
- reporting what changed and what remains;
- helping an agent hand off unfinished work.

Keep these inside the component that already needs them unless independent reuse
becomes clear.

## Candidates for future reuse

A capability may deserve a separate reusable interface when there is repeated
evidence that repositories need it independently. Examples may include:

- delegation support;
- external work intake;
- richer review tooling;
- deployment or release coordination;
- broader repository search/retrieval.

These are possibilities, not commitments.

## Human direction and agent judgement

The intended product shape is not unrestricted autonomy.

Humans provide goals, priorities and constraints. Agents make ordinary local
implementation choices when the repository rules allow them to, and ask for help
when a required decision genuinely belongs to a human.

A useful repository should make it clear:

- which outcomes are required;
- which project rules constrain the work;
- what the agent may decide locally;
- which checks are required;
- when the agent must stop because necessary information or permission is missing.

## When to extract a capability

Create a separate component only when all of these are true:

1. repeated real work shows that the capability is useful outside its current home;
2. its inputs and outputs are stable enough to document clearly;
3. repositories can adopt it independently;
4. the new component removes more complexity than it adds.

The default is to keep behaviour with the component already responsible for it.

Do not preserve old product taxonomy merely because earlier documentation named
it. Update this page when actual product use changes the long-term direction.
