---
name: workspace-startup
description: Start or resume repository work; decide whether current AW facts or a specialised procedure are needed.
---

# Start ordinary work

Read the task and applicable repository instructions whenever work starts or
resumes. Then decide what information the next action needs:

- If the supplied text and current sources suffice, do the work directly. A new
  session or context loss alone does not require a command.
- If an edit, test, completion claim or recovery depends on missing or changed
  permission, setup, state or evidence, use native `start` to obtain those facts.
  [Ordinary use](references/ordinary.md) explains the configured command.

Reuse an observation while its relevant sources and scope remain unchanged and
its content is still available. A saved response does not grant current permission.
After context loss, recover only missing or invalidated facts needed by this task.

## Follow the result for the affected action

If `start` returns `status: inactive` with `configuration.enabled: false`, end AW
startup and continue repository work under the existing repository, user and host
rules. Do not retry unchanged startup or ask the user to enable AW. This opt-out
supplies no repository permissions and waives no repository requirements. Explicit
AW setup, diagnostics and recovery remain available through their existing paths.

If `start` reports a restriction, read its `affects` field and the supplied request
for resolving it. Keep that action blocked until the responsible component returns
a result that allows it; continue authorised work outside that scope. Having a
shell or editor does not remove a restriction. See
[restricted actions](references/constraints.md) when the result needs interpretation.

A restriction is not a request for human approval. Relay the owner's complete
human decision context only when its returned resolution requires a bounded
human answer and its `human_eligibility` names a current Verification requirement
for human judgment or an explicitly configured human task owner. Routine domain
decisions belong to the acting agent under the current task authority.
For `owner-recovery-required`, follow the supplied recovery. For
`current-owner-route`, follow the matching consequence route and complete any
bounded owner selection; a route does not resolve the restriction. For
`owner-resolution-unavailable`, explain the missing fact or capability and that
no supported resolution is currently supplied. Preserve the affected block and
continue unrelated work; do not invent a recovery or ask the user to waive it.

AW calls the component responsible for a rule, record or operation its **owner**.
For changes to managed state, use that component's exact returned request/action
through [the owner interaction procedure](references/owners.md).
If setup or package refresh needs attention, follow the
[setup procedure](../workspace-setup-jumpstart/SKILL.md), then return to the task.
If AW cannot run, [read the relevant sources](references/unavailable.md), preserve
managed state and report which current facts remain unknown.

## Handle findings and unfinished work

When a source/test finding, correction, unmet prerequisite or useful improvement
could change what happens next, include it in the `material` input to `start`
before losing it or taking the dependent action. See
[how to supply a finding](references/ordinary.md#current-material-and-needs).
Follow the returned restrictions and relevant procedure choices. Current policy
determines whether to repair, report or take no action; a finding grants no write.

Before a handoff, pause or context loss, check whether existing records explain
the remaining objective, accepted decisions and next step. A diff may omit that
meaning. If losing it would cause rediscovery or unsafe continuation, use
[Planning continuity](../../planning/skills/planning-work/references/continuity.md)
and verify the saved result. Reuse an adequate record; simple completed work and
unchanged progress need no new artifact. On resume, establish whether the selected
plan actually belongs to this task.

Finish when the requested outcome and its required evidence are established.
Historical status alone does not reopen completed work. Reobserve a captured
fact when the current action depends on it; update retained meaning only when
its loss or a wrong currently relied-upon instruction would change safe continuation.
A completed slice with a pending prerequisite leaves the objective unfinished;
report the remaining work. Keep lessons only when they have
[future value](references/reconcile.md). Load another [procedure](procedure.md)
only for a concern the current task needs. Reading a skill grants no permission,
proof success or completion authority.
