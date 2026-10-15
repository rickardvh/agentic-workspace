# Planning, Memory and Verification

Planning, Memory and Verification are available by default and preserve different
kinds of useful work. Use them for a relevant need; they are not steps every task
must pass through. Their runtime behaviour is included in the shared native
product, with their procedures in the repository integration. Users do not install
three separate module runtimes or answer a module-selection questionnaire.

## Default availability

The default policy is **all three available, with task-specific use and setup**.
Omitting `[modules]` already allowed all three native owners; AW retains that
behaviour. The schema and generated configuration reference now describe it
accurately. A null modules value in native output means the selector was omitted,
not that no modules are available. Explicit selections remain distinguishable:

| Repository configuration | Available built-in owners |
| --- | --- |
| No `[modules]` section | Planning, Memory, Verification |
| `enabled = ["planning", "memory", "verification"]` | Planning, Memory, Verification |
| `enabled = ["planning", "memory"]` | Planning and Memory |
| `enabled = []` | Routing and configuration only |

The built-in code and shipped procedures are available without creating plans,
notes or checking declarations. Actual useful behaviour still needs applicable
repository sources, permissions and consumer checks. The installed startup
procedure directs the agent to the relevant setup and domain procedure as the
task warrants; enabling a module is not proof that this follow-through happened.
Automatic relevant consumer follow-through is tracked separately in
[#3885](https://github.com/rickardvh/agentic-workspace/issues/3885).

Keeping all three available avoids making ordinary users choose internal
components before they have a concrete need. A smaller explicit list remains
useful for a repository that deliberately excludes a capability, but omission
must not silently disable an owner previously available. Relevance controls
ordinary reads, output and retained work; availability does not require a plan,
Memory import, proof run or native startup call on every edit.

Fresh adoption and compatible updates preserve the selector exactly. Setup does
not insert a module list, turn an explicit subset into all three, or replace an
explicit empty list. Disabled AW and local safety limits remain authoritative.
This is a correction of the declared default and installed guidance, not a runtime
enablement migration or a new preset. It introduces no supported consumer-owned
migration burden under the [package compatibility policy](../release-and-versioning.md#package-compatibility-boundary).

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
