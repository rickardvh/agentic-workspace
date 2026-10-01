# Routine task context

AW keeps Planning, Memory, Verification, project instructions and other sources
separate. An ordinary agent should not need to learn each internal subsystem
before starting work.

The routine task view answers five practical questions without storing another
copy of the underlying information:

| Question | Typical source |
| --- | --- |
| What project rule applies? | Repository instructions and configuration |
| What work is unfinished? | Planning |
| What checks matter? | Verification and project test policy |
| What useful lesson should I know? | Memory and project documentation |
| What information should be saved or moved elsewhere after this task? | Planning, Memory, docs, configuration or issues |

The exact JSON fields used by the implementation remain defined by their
contracts. This page describes the purpose of the combined view, not another data
model users need to maintain.

## Keep the view small

Show information only when it can change the next action, required checks or a
completion decision.

For example:

- a project rule affecting the changed path should appear;
- unfinished Planning work for another task should not;
- a stale Memory note should be reconsidered before it is relied upon;
- a required Verification procedure should be visible before claiming the work
  complete.

Do not dump every known source into startup output.

## Use existing components for changes

The combined view does not own project rules, plans, lessons or evidence.

When the task reveals something worth keeping:

- unfinished work goes to Planning;
- a reusable lesson goes to Memory;
- a binding project rule goes to documentation or configuration;
- a checking procedure or evidence gap goes to Verification;
- a product improvement that needs review can go to an issue.

Use the specific operation returned by the component that maintains that record.

## Recheck changed information

If a saved rule, lesson or test result depends on files that changed, check it
again before relying on it. Do not treat an old hash, previous conversation or
successful test name as enough by itself.

When a relevant external source is unavailable, report that gap rather than
inventing a current answer.

## Completion

A component having nothing left to do does not automatically mean the user's task
is complete. Completion still depends on the requested outcome and the checks the
repository requires.

Small tasks should remain quiet when none of these sources matter.
