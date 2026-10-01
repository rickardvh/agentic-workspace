# How AW components work together

This page summarises how the built-in components divide responsibility. It is not
a second module manual. For module-specific behaviour, see [Modules](package/modules.md).

## Keep one clear home for each kind of information

| Concern | Where it belongs | It may refer to | It should not become |
| --- | --- | --- | --- |
| Unfinished task state | Planning | Memory, Verification, project docs | a long-term knowledge base or backlog copy |
| Useful long-term repository knowledge | Memory | Planning and project docs | an active task tracker or execution log |
| Checking procedures and saved evidence | Verification | Planning, Memory and assurance requirements | a CI runner or a source of completion decisions |
| Shared setup and routing | AW core | reports and manifests from the relevant components | hidden module-specific policy |
| Generated references and adapters | Their source contracts and generators | module manifests and operation definitions | another hand-edited source of truth |

## Ordinary interaction

1. AW gives the agent the project context relevant to the task.
2. Planning says what unfinished work exists and what remains to be done.
3. Memory provides useful lessons that would otherwise be expensive to rediscover.
4. Verification provides relevant checking procedures, saved results and known gaps.
5. The agent judges how to do the work and what conclusions the available evidence supports.

If the same rule or explanation appears in several places, fix the duplication
instead of expecting readers to guess which copy is current.

## Where to put information after a task

When work finishes:

- unfinished work or the next step belongs in Planning;
- a reusable lesson belongs in Memory;
- a reusable checking procedure or known evidence gap belongs in Verification;
- stable human-facing guidance belongs in project documentation or configuration;
- narration already obvious from code, tests or pull-request history can be dropped.

Writing nothing is valid when there is nothing worth keeping.

## Which source to trust

Prefer the most specific current source for the fact you need:

1. the component that maintains the current task or evidence record;
2. project documentation or saved Memory for long-term project knowledge;
3. Verification for checking procedures and evidence gaps;
4. generated references only as views of the files that define them;
5. dated reviews and archives only for historical context.

Historical records do not become current project rules unless a current document
explicitly relies on them.
