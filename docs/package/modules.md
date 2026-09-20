# Planning, Memory and Verification

These optional capabilities preserve different kinds of useful work. Choose them
for a recurring need, not as steps every task must pass through. Their runtime
behaviour is included in the shared native product; users do not install three
separate module runtimes.

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

## Enable only what helps

Ask the agent to inspect the relevant capability and configure it for a concrete
need. Availability, configuration and current work selection are separate facts;
none should cause unrelated state to be created.

[Everyday use](../everyday-use.md) shows the interactions.
[Configure your project](../customization.md) covers shared and local choices.
[Your repository and data](installed-surfaces.md) explains what survives updates
or removal.

To add a different reusable domain, read [Add a reusable capability](../module-capability-contract.md).
A project-specific instruction or skill usually does not require a module.
