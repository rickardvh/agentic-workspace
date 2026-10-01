# Agentic Workspace design principles

Agentic Workspace should make repository work cheaper to continue, verify and
hand off while keeping its own machinery out of the way.

For the current product model, start with [How AW fits into a project](package/overview.md)
and [System Intent](../SYSTEM_INTENT.md).

## 1. Keep only information that changes future work

Save a fact, procedure, task record or lesson when having it later will change a
decision or prevent expensive rediscovery. Do not save chat, logs, plans, reviews
or repository facts merely because they exist.

Source code, project documentation, tests and history stay where they already
belong. AW should point to those sources rather than copy them into another
knowledge system.

## 2. Show only what matters now

First contact should contain only information that can affect the current task.
Load deeper procedures or references when the task actually needs them.

Prefer a short answer that names the relevant source, restriction and next action
over a broad reading list or a manual for every installed capability.

## 3. Leave responsibility with the component that owns the work

Planning maintains unfinished task records. Memory keeps useful lessons.
Verification maintains checking procedures and evidence. Repository files remain
the source for project policy and documentation.

AW may combine information from those places for the current task, but it should
not create a second competing copy of their meaning.

## 4. Make the next step usable

When AW says more work is needed, it should point to something the agent can
actually do: a supported operation, a command, a skill, a specific source to
read, a clearly stated choice or a recovery procedure.

Do not return an abstract status such as “reconcile”, “escalate” or “resolve the
owner” without saying what to inspect or do next.

## 5. Ask humans only for decisions that really require them

Do not ask the user to repeat facts available from the repository or to approve
routine work merely because AW manages the file involved.

A human decision is appropriate when the task is explicitly assigned to a human
or when Verification says human judgement is required. Otherwise, use the
repository's current rules and let the agent continue within them.

## 6. Keep one ordinary working loop

The ordinary model is simple:

```text
Check what applies → Do the work → Update what matters
```

Startup, implementation, checking, handoff and finishing are situations within
that loop, not separate frameworks the user must operate.

If an action may already have happened but its result is unknown, check what
happened before trying it again.

## 7. Small work should stay small

A typo fix should not create a plan, memory entry, verification record, handoff or
other artefact merely because those capabilities are installed.

Components that are irrelevant to the current task should stay quiet.

## 8. Help the agent; do not script ordinary implementation

AW should be strict about project rules, permissions, saved state and what test
results actually establish. It should not micromanage routine coding decisions.

Prefer a small number of clear rules and supported actions over scheduler-like
workflow machinery.

## 9. Optimise the whole cost of finishing correctly

Consider rereading, rediscovery, clarification, retries, extra checks, handoff
reconstruction, repair and user round-trips—not only token count or command count.

Do not save agent effort by creating more human ceremony. Stop optional discovery
when more information is unlikely to change the next decision.

## 10. Fix the source of recurring problems

Repeated confusion, stale information, wrong checks or repeated user correction
should lead to a fix in the component or document responsible for that behaviour.

Do not compensate for a deterministic defect by adding warnings in unrelated
places.

## 11. Keep extensions narrow

A reusable capability may justify a module with its own data and operations.
Ordinary repository-specific guidance belongs in instructions, configuration,
skills or project documentation.

Do not turn AW into a generic plugin runtime, event bus, credential store or
workflow engine.

External integrations should translate another host into AW's existing public
operations; they should not redefine AW behaviour.

## 12. Keep AW removable

Package-managed files should stay under `.agentic-workspace/` as far as practical.
Files outside it should exist only because a host requires that exact location.

Removing AW should remove only files that AW can verify it manages and preserve
project-owned configuration, plans, lessons, evidence and unrelated content.

## 13. Prefer files that collaborate well

Normal Git use should not make AW brittle. Avoid giant frequently edited state
files. Keep task-specific records separate when that reduces merge conflicts, and
remove or archive completed information when it no longer helps future work.

Generated files should come from one clear source and should not compete with it
for meaning.

## 14. Compatibility layers need a reason to exist

Do not keep old and new designs in parallel indefinitely. A compatibility layer
should protect a named consumer during a real transition and have a clear removal
path.

## 15. Documentation should be simpler than the implementation

Start with the reader's task. Use ordinary language for what to do and what
happens. Put detailed API fields, maintainer procedure and historical evidence
behind links for readers who need them.

Exact commands, field names and file paths stay exact. Internal repository jargon
does not become public vocabulary merely because the implementation uses it.

## 16. Evidence should match the claim

Run the smallest check that can expose the relevant failure. Reuse current
evidence when it still applies. Broaden to another platform, provider or package
surface only for a specific remaining risk.

Passing a command supports only what that command actually tested. A saved result
does not automatically apply after its inputs change.

## Questions for a proposed change

A change is moving in the right direction when:

- it makes important context cheaper to recover;
- it gives the agent a clear next action;
- it removes duplication or unnecessary machinery;
- direct work can ignore it when irrelevant;
- responsibility for each record or rule remains clear;
- it reduces the total cost of finishing correctly;
- it would still make sense in another repository.

A change deserves scrutiny when it mainly:

- adds another framework or vocabulary layer;
- stores history with no clear future use;
- copies information already maintained elsewhere;
- introduces a new visible concept without replacing an old one;
- makes generated documentation or state compete with its source;
- adds ceremony to compensate for a simpler defect.

## Related maintainer guidance

Use [Contributor playbook](maintainer/contributor-playbook.md) for repository
maintenance, [Testing strategy](maintainer/testing-strategy.md) for choosing
evidence, and [Documentation style guide](documentation-style-guide.md) for
human-facing writing.
