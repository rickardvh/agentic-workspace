---
paths:
  - AGENTS.md
  - '**/AGENTS.md'
  - .agentic-workspace/WORKFLOW.md
  - .agentic-workspace/instructions/*.md
  - .agentic-workspace/local/instructions/*.md
  - .agentic-workspace/skills/*.md
  - .agentic-workspace/skills/REGISTRY.json
  - .agentic-workspace/planning/skills/*.md
  - .agentic-workspace/planning/skills/REGISTRY.json
  - .agentic-workspace/memory/skills/*.md
  - .agentic-workspace/memory/skills/REGISTRY.json
  - .agentic-workspace/verification/skills/*.md
  - .agentic-workspace/verification/skills/REGISTRY.json
  - .agentic-workspace/fallback/*.md
  - tools/skills/*.md
  - tools/skills/REGISTRY.json
  - prompts/**
  - '**/prompts/**'
  - src/core/payload/**.md
  - src/core/payload/**/REGISTRY.json
  - src/core/src/native_adoption.rs
  - src/tooling/generate/generate_agent_interface.py
  - src/tooling/contracts/schemas/skill_spec.schema.json
---

# Agent-facing writing guide

Use this guide when writing or reviewing text an agent must act on: instructions,
skills, procedure choices, prompts, tool explanations and handoffs. Assume a
capable reader who has not seen the author's chat or design discussion. Explain
what the reader needs for this task, not the whole Agentic Workspace (AW)
architecture.

This is the canonical writing guide for this repository's agent-facing material.
The path scope supplies it for the usual source locations. For agent-directed
text embedded elsewhere, follow the same guide when that text is the subject of
the change. It does not govern unrelated implementation code or require an AW
command merely to read or apply it. Human-facing documentation also follows the
[documentation style guide](../../docs/documentation-style-guide.md).

## Start from the reader's situation

Open with the job, when the text is useful and the result it helps produce.
Name any prerequisite the reader cannot discover from the supplied context.
Do not assume an earlier skill, chat turn or internal design document was read
unless it is an explicit, accessible prerequisite.

A step must make four things clear: **when it applies, what to inspect, what to
do, and when to stop**. These are questions to answer, not mandatory headings.
A policy states the rule and its scope; a skill teaches how to carry out a task.
Do not turn every recommendation into policy or every rule into a workflow.

## Attach terms to something the reader can identify

Name the concrete file, returned field, operation or situation before introducing
its technical name. Keep necessary identifiers exact. Explain specialised words
at first use where they change the action; do not require a glossary detour.
Avoid abstract noun chains and phrases such as “handle the consequence” when the
reader has not been shown which consequence or what handling it involves.

Instead of “retain through the responsible owner”, write, for example:

> If a later session will need the agreed next step, update the existing Planning
> record for this task through its returned update request. Confirm the saved
> result before saying it was retained. Do not create a second plan when the
> existing record already contains the information.

Here “Planning” names the component maintaining the task record, rather than an
unexplained instruction to find an “owner”. Link the exact update procedure at
that step; do not reproduce its request schema in every skill.

## Give an action, its result and its failure boundary

Use active verbs with named objects. “Reconcile”, “validate” or “preserve” alone
is not a usable step. Identify the source or returned request to use, the input
the reader supplies, and the observation that confirms success.

Show one ordinary example when it removes ambiguity. Distinguish literal commands
from placeholders and illustrative prose. Check commands and field names against
the current public interface. Never invent an executable example to make a guide
look complete; link the supported procedure when exact syntax belongs there.

Put the relevant failure instruction beside the action. For example:

> If a write may have completed but its reply was lost, do not repeat the write.
> Use the returned recovery path or inspect the current result before deciding
> what remains to do.

End a procedure when its stated result is established. If a required fact cannot
be obtained, name the missing fact and the affected action that remains blocked.
Do not replace a specific recovery path with “escalate appropriately”.

## Make requirements conditional and tools selective

Use **must** for a requirement and **may** for an option. State the condition and
affected action next to the requirement. Preserve policy scope in both metadata
and prose; a path-limited instruction cannot express an unconditional rule for
all repository work merely by saying “always”.

Following an AW skill is not the same as running the CLI. Explain what missing or
changed information makes a tool call necessary. Reuse sufficient current facts
and results. A new turn, session or context loss is not, by itself, a reason to
repeat commands whose results do not matter to the task.

For example, explaining supplied text needs no fresh runtime observation when
nothing in the answer depends on live state. Before an action that may depend on
an unresolved permission, prerequisite or completion requirement, obtain the
missing current facts. **Unknown applicability is not proof of irrelevance.**
Resolve material uncertainty without blocking unrelated authorised work.

Do not strengthen a rule to make an experiment pass. A test should establish the
needed behaviour, not reward command execution for its own sake.

## Reveal detail where it becomes useful

Keep the entry focused on choosing and starting the task. Put substantial
alternatives, field catalogues and exceptional recovery details behind descriptive
links. Include the small amount of context needed to choose a link correctly.
A reference must not say only “see the owner” or send the reader around a cycle.

Describe branches by situations the reader can recognise. Prefer “The write may
have finished, but no result was returned” to “Uncertain effect custody”. Keep
registry summaries and activation descriptions sufficient for selection; they
must not become another copy of the full procedure.

Do not remove context merely to reduce word count. Conversely, do not preserve
repeated caveats, implementation history or every possible example. Delete or
merge a branch when it adds no useful decision. A fresh reader must not need the
whole bundle to understand its first step.

## Keep procedure separate from authority and current state

Skills and their references describe current supported workflows. Compatibility
with retired representations belongs to the runtime component that owns the data;
do not add format migration or legacy workflow branches to skills.

Explain how to use a current rule, request or result; do not copy changing policy,
permission, task state or proof into the skill. Preserve exact identifiers and
returned actions instead of teaching callers to reconstruct them.

Put warnings where a reader could make the relevant mistake. Explain the boundary
once at that point rather than repeating a general disclaimer in every paragraph.
A clearer sentence cannot grant permission, turn a partial result into completion,
or replace the repository's independent-review rules.

Change generated text at its source and regenerate it through the existing path.
Do not maintain separate source and installed versions of the same guidance.
Preserve API spelling and data contracts even when rewriting nearby explanations.

## Explain evidence and costs before presenting numbers

Reports and handoffs are instructions to their next reader too. State the task,
what was compared, what succeeded or failed, and what decision the evidence
supports. Then give measurements with labels, units and a clear comparison basis.
Explain whether “tokens” means input, output, their sum or a provider-specific
count; distinguish model usage from money and tool calls from completed work.

Instead of “binding control: 7 / 16; no economic superiority”, write:

> In this test AW blocked an edit but allowed unrelated reading. Both agents
> respected the restriction. The older version made seven AW calls; the candidate
> made sixteen. This run shows preserved behaviour at higher call cost, not an
> improvement in reliability or monetary cost.

Label invented examples as illustrative. Keep exact revisions, raw logs and
receipt identifiers available for verification, but do not make the reader decode
them to discover what was tested. Preserve failed attempts and unknown causes.
A successful retry does not establish why the first attempt failed.

## Check the text from a fresh reader's position

Trace an ordinary case and a relevant boundary case using only the task, supplied
facts and linked procedure. Can the reader choose the next step, obtain its input
and recognise completion without asking what the author meant? Check an
unrelated case too: the text must not create work where it does not apply.

Check links, metadata, examples and generated copies with existing tools. Those
checks establish structure, not comprehension. For a material behaviour change,
use a bounded fresh-reader exercise; record confusion, wrong actions and reminders
rather than counting a tool invocation as success. Do not require a new agent run
or permanent regression for every wording edit.

Reviewers apply the same questions, not their familiarity with the implementation.
Keep author validation distinct from independent review. Fix the source of an
ambiguous instruction instead of adding another warning elsewhere.
