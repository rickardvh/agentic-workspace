# Planning, Memory and Verification

Planning, Memory and Verification are available by default and preserve different
kinds of useful work. Use them for a relevant need; they are not steps every task
must pass through. Their runtime behaviour is included in the shared native
product, with their procedures in the repository integration. Users do not install
three separate module runtimes or answer a module-selection questionnaire.

## Default availability

All three components are available when `[modules]` is omitted. A repository can
deliberately select a smaller set:

| Repository configuration | Available components |
| --- | --- |
| No `[modules]` section | Planning, Memory, Verification |
| `enabled = ["planning", "memory", "verification"]` | Planning, Memory, Verification |
| `enabled = ["planning", "memory"]` | Planning and Memory |
| `enabled = []` | Routing and configuration only |

Setup and compatible updates preserve an explicit selection, including an empty
list. See the [configuration reference](../reference/workspace-config.md) for exact
settings and the [compatibility policy](../release-and-versioning.md#package-compatibility-boundary)
for upgrade guarantees.

Availability creates no plans, lessons or checking declarations by itself. The
agent should use a component only when relevant and establish the project-specific
configuration it needs. Disabled AW and local safety limits still apply.

## Planning

Use Planning when a task needs to survive interruption, several sessions or a
handoff. It keeps the intended outcome, constraints, accepted progress, unresolved
questions and next action together.

For example, before stopping a partly implemented feature, ask the agent to save
what is working and what the next session must still do. In the next session,
explicitly select that work to continue. A recorded plan is not automatically the
current task, and completing one part does not complete the whole outcome.

## Memory

Use Memory for lessons worth reconsidering in future work: a non-obvious build
constraint, the reason an approach failed, or useful advice whose assumptions can
be stated. Keep canonical project facts in their existing documents rather than
copying them into notes.

Advice remains advice. A correction intended to govern future behaviour belongs in
project instructions or another authoritative source, not merely a Memory note.
Ask the agent to revise or retire a lesson when its dependencies change.

## Verification

Use Verification to define reusable checking procedures and retain what the
checks established. It can help the agent choose relevant evidence and distinguish
passed checks from remaining uncertainty.

The repository supplies its checking policy. Selecting the capability does not
invent tests or make a successful check prove the entire feature. New code or
changed dependencies may require fresh evidence.

## Use only what helps

Give the agent the actual task. It should identify the relevant capability and
complete necessary authorised setup from repository evidence. Availability,
configuration and current work selection are separate facts; none should cause
unrelated state to be created. A missing unneeded manifest or note is normal.

[Everyday use](../everyday-use.md) shows the interactions.
[Configure your project](../customization.md) covers shared and local choices.
[Your repository and data](installed-surfaces.md) explains what survives updates
or removal.

To add a different reusable domain, read [Add a reusable capability](../module-capability-contract.md).
A project-specific instruction or skill usually does not require a module.
