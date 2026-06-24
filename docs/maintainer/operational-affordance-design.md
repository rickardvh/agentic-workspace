# Operational Affordance Design

## Purpose

This document records a durable product principle for Agentic Workspace:

```text
A new agent should not have to understand the system before it can use it.
The system should carry the agent into the correct next step with minimal cognitive effort.
```

Correct-by-design applies not only to structured files and validation. It applies to operations, processes, workflows, startup, recovery, closeout, proof, lifecycle management, and handoff.

The ideal operating path should feel less like rowing against the stream and more like being carried along by it.

## Core principle

Operational surfaces should be designed as affordances.

An affordance is not just information. It makes the next correct action obvious, cheap, and hard to confuse with adjacent actions.

The product should prefer:

```text
self-routing workflows
one obvious primary next action
resolved commands using current config
small first-contact outputs
progressive disclosure
structured action objects
safe dry-run/apply paths
writer/scaffold helpers
validation as confirmation
```

over:

```text
broad instructions
multiple equivalent doors
raw file archaeology
manual sequencing
hand-authored structured records
validation repair loops
large prose explanations before action
```

## Design target

A capable but unfamiliar agent should be able to start work by following compact affordances without first learning Agentic Workspace concepts such as workspace, planning, memory, profiles, resources, tools, prompts, execplans, residues, or ownership classes.

Those concepts may exist internally, but they should be revealed only when needed.

The ordinary path should be:

```text
orient
-> select one next action
-> act safely
-> validate
-> close or continue
-> route durable residue
```

Each step should produce the affordance for the next step.

## Operational affordance review

Every operational surface should answer these questions:

- What is the obvious next action?
- Is there exactly one primary action?
- Are irrelevant actions hidden, demoted, or placed behind selectors?
- Does the output use resolved repo/local config?
- Does it prevent common mistakes before validation?
- Does it require understanding internal architecture?
- Can a weak or generic agent follow it without reading docs?
- Can a strong agent inspect, override, or bypass safely when needed?
- Does it expose raw files only after compact outputs point there?
- Does it keep historical evidence from looking like live work?

## Warning and Gate Posture

Ordinary warnings and gates should be action-changing or selector-backed. A caution signal belongs in first-line output only when it changes at least one of these:

- what action remains allowed now
- what action or claim is blocked until reconciliation
- what proof burden or closeout boundary changed
- which owner surface or selector resolves the signal
- whether skipping the signal lowers trust, blocks edits, or only blocks final claims

When a caution is only background concern, route it behind a selector, review artifact, or maintainer diagnostic instead of making ordinary agents stop and reread. False-positive-prone signals should prefer typed posture over broad prose. For example, PR/review references should not become unknown issue-scope gates when the task is clearly PR-oriented, and objective-drift checks should classify explicit replacement or removal terms before warning that the retired term disappeared.

## Examples

### Startup

Poor affordance:

```text
Read AGENTS.md, SYSTEM_INTENT.md, state.toml, report docs, and planning docs to understand what to do.
```

Better affordance:

```text
Run the configured start command.
It returns the current situation, one primary next action, and optional deeper resources.
```

### Proof

Poor affordance:

```text
Here are possible proof routes. Decide what to run.
```

Better affordance:

```text
Here is an ordered validation plan with required/optional commands, working directories, and copyable execution form.
```

### Closeout

Poor affordance:

```text
Update state.toml, create/archive a closeout record, route residue, validate schemas, and post a comment.
```

Better affordance:

```text
Run a closeout helper with explicit fields. It writes valid state, renders optional prose, and verifies the result.
```

### Planning state

Poor affordance:

```text
Open raw state and infer whether rows are active, deferred, closed, or historical.
```

Better affordance:

```text
Summary says active, ready, blocked, deferred, and historical separately. Raw state is a follow-up inspection surface only.
```

## Relationship to validation

Validation remains necessary, but it should confirm correct construction rather than teach agents how to construct.

If validation repeatedly catches the same mistake, treat that as an affordance failure. The likely remedy is one of:

- remove the confusing path
- merge or demote a surface
- add an alias or route suggestion
- add a scaffold or writer helper
- add a constrained template
- add an action object or execution plan
- create a local or checked-in reusable aid
- make a lifecycle operation atomic

Adding more validation is not enough if the interface still invites the wrong action.

## Relationship to prose reduction

Operational affordances should reduce the amount of prose an agent must write.

Agents should author structured intent, evidence, decisions, and routing first. Prose should be generated, constrained, optional, or reserved for genuinely explanatory content.

Do not solve prose burden by adding a new prose-heavy meta-surface.

## Relationship to Memory and Planning

Affordance failures are improvement signals.

- If the issue is active or future work, route it to Planning.
- If the issue is durable but not yet canonical understanding, route it to Memory.
- If the issue is a stable rule, promote it to docs, contracts, checks, or code.
- If the issue is merely evidence, keep it in archives or reviews.

Planning archives are not the working memory of the system.

## Anti-patterns

Avoid these patterns:

- presenting raw files before compact commands
- asking agents to choose among several equivalent first commands
- exposing historical evidence as live work
- requiring agents to hand-author schema-heavy records
- making validation errors the main authoring guide
- adding report sections or inventories that do not reduce operating cost
- preserving closed work in first-line state when it is reconstructable
- making local/runtime-specific helpers appear canonical
- requiring a new agent to understand package architecture before acting

## Success signal

A new agent should be able to say:

```text
I did not need to understand the system first.
The system showed me what to do next.
The next step was safe, specific, and easy to follow.
```

A strong agent should be able to say:

```text
The system did not get in my way.
It exposed enough structure to inspect, override, and improve the workflow without broad rereads.
```
