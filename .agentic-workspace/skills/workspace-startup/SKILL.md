---
name: workspace-startup
description: Start or resume repository work; decide whether current AW facts or a specialised procedure are needed.
---

# Start ordinary work

Read the task and applicable repository instructions. If supplied text and current
sources suffice, work directly. A new session or context loss alone requires no
AW call, specialist read or duplicate plan. Reuse observations while their relevant
sources and scope remain current and their content is still available.

**Before implementation, establish the target checkout's executor policy.** Read
its `.agentic-workspace/config.local.toml` and any selected
`workspace.shared_config_path`; local values take precedence. No declaration
means `local-preferred`. An earlier report, parent checkout or available editor
cannot establish this checkout's policy. For an invalid or unavailable configured
source, use native `start` to obtain the restriction and recovery; do not assume
the default. Under `required-best-fit`, obtain or reuse current executor admission
before affected implementation, including host edits. Follow
`assignment_context.next_step` and [Assignment](../../planning/skills/planning-assignment/SKILL.md).
`local-preferred` needs no routine comparison; `best-fit-advisory` advice does not
prohibit local work. Independent executor requirements still bind.

**Obtain current AW facts when the next action depends on them.** Missing or changed
permission, setup, state, evidence or recovery needed for an edit, test or claim
requires native `start`. Use [ordinary use](references/ordinary.md) for the
configured invocation: local `workspace.cli_invoke`, then repository config,
otherwise `agentic-workspace`. A missing PATH command does not make that invocation
unavailable. When AW cannot run, preserve managed state and use
[the unavailable-runtime procedure](references/unavailable.md); do not infer
missing permission or custody from readable sources.

Load another procedure only for a concern this task needs:

- At entry, judge whether decomposition or durable continuity would materially
  improve execution. Reuse an adequate issue, repository record or explicitly
  related owner. Otherwise use [Planning work](../../planning/skills/planning-work/SKILL.md)
  before important meaning is lost; do not postpone the first judgment to handoff.
  Unrelated remembered plans remain inert.
- Before choosing validation or designing, adding, changing, retaining or removing
  tests, use [proof selection](../workspace-proof-selection/references/select.md).
  Reuse guidance already read; this needs no Verification module or runtime call.
- For setup/refresh or a useful missing setup connection exposed by task sources,
  use [consumer setup](../workspace-setup-jumpstart/references/consumers.md) before
  the dependent action, even after `already-current` or `owner-managed`. Missing
  files alone imply no setup work; reuse settled choices.
- For a finding, correction, unmet prerequisite or useful improvement that could
  change what happens next, supply `material` through
  [ordinary ingress](references/ordinary.md#current-material-and-needs) before
  losing it or taking the dependent action. Applicable repository observation
  rules also cover friction despite eventual success. Nomination needs no proven
  defect or predicted recurrence; no signal needs no scan or call.
- When already-selected retained facts could change an imminent decision, or their
  controlling source changed, use [related findings](../workspace-instruction-correction/references/related.md).
  A requested review of retained repository knowledge uses
  [the selected improvement review](../workspace-instruction-correction/references/review.md).
- Before handoff, pause or context loss, use
  [Planning continuity](../../planning/skills/planning-work/references/continuity.md)
  if existing records omit meaning a later actor needs. Verify the saved result;
  unchanged progress and simple completed work need no new artifact.

Read a returned restriction's `basis`, exact `affects` and recovery before the
dependent action or claim. Use [restriction handling](references/constraints.md)
for an unresolved requirement, owner route, unavailable recovery or human decision.
A restriction alone is no request for human approval. For managed changes, follow
the responsible component's exact request/action through
[owner interaction](references/owners.md); a route or skill grants no authority.
If `start` returns `inactive` with `configuration.enabled: false`, end ordinary AW
startup without retrying or asking to enable it; independent repository rules remain.

Finish when the requested outcome and applicable evidence, protection, producer,
reviewer and custody requirements are satisfied. A completed slice with a pending
prerequisite leaves that objective unfinished. AW bookkeeping or missing optional
attestation adds no acceptance criterion or final-call requirement. Preserve a
material evidence limit once in existing task/PR evidence. Keep lessons only when
they have [future value](references/reconcile.md).
