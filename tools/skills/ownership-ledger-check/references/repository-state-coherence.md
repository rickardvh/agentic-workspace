# Review current AW repository state

Use this procedure when Verification reports `aw_repository_state_coherence`
due or unknown. The result is one current assessment of this repository's
operating context. It does not certify product correctness or release readiness.

## Enter through the same owner

An ordinary agent and an external manual or scheduled runner both call the
repository's configured native `start` with the repository target and their
actual task. Read the matching `material.items` need, its reason and procedure,
then the Verification `current_evidence` detail. A scheduler should only arrange
that call; the manifest and this procedure own the review's scope and method.
When the condition is satisfied and current, stop without another review.
The requirement restricts parent-lane closeout, where unresolved operating context
could falsely imply a settled lane. It does not restrict unrelated implementation
or slice/work completion. Claim coherence only when its current Verification
assessment is satisfied.

The declaration in `.agentic-workspace/verification/manifest.toml` expires after
seven days. That bounds discovery of new or semantically changed surfaces outside
the exact dependency list. Intent, ownership, configuration, operating guidance
and Verification anchors make common changes due sooner. The procedure itself
also participates in currentness. No directory watcher or startup scan is needed.

## Compare current meaning

Start with the declared anchors. Follow their current references only where they
can change an agent's next action or claim. During a due review, inspect the
immediate repository instruction and maintainer-procedure entries for additions;
use the ownership ledger's read guidance to select other relevant sources. This
bounded discovery belongs to the due review, never every ordinary startup.

For each relevant binding, compare what it asks the agent to do with the source
that owns that meaning:

| Binding | Compare and identify a finding |
| --- | --- |
| Intent, instruction, ownership or scope reference | Check the current target and its role, including moved files, path scope and owner. An existing file with the wrong role is still a finding. An optional absent path or future scope explicitly allowed by its owner is not. |
| Proof command or procedure | Read the command's current implementation and relevant tests as well as its invocation. Confirm that the promised evidence is what it now observes. For example, a catalogue check cannot prove installed-consumer behavior. Run the smallest check if source inspection leaves a material ambiguity. |
| Current continuation or unanswered question | Read only a task-supplied, selected, or otherwise actively relied-upon Plan's next action, accepted decisions and dependencies. Compare with the owning current source. If it asks for work already completed or a question already settled, identify the actual affected next action. A record's age alone is no finding. |

`SYSTEM_INTENT.md`, repository policy, applicable instructions, current source and
their accepted source-owned decisions govern the comparison. Use the configured
decision archive or an accepted GitHub issue/PR decision only when a current
ambiguity needs it. Attribute the exact issue, PR, comment or revision and explain
what it settles. An old discussion does not reopen an accepted decision.

Archived Plans, prior receipts and retained historical evidence are controls, not
an execution queue. Do not traverse them merely because they exist. If current
guidance actively relies on one, inspect that specific dependency and distinguish
its historical evidence from a current instruction. Preserve explicit intentional
exceptions, including unresolved source custody; never replace them by convention.

## Resolve findings and publish

Record only each concrete mismatch, its affected action, source evidence and
responsible owner. Supply material findings to `start` as described in
[current material](../../../../.agentic-workspace/skills/workspace-startup/references/ordinary.md#current-material-and-needs).
Use the existing instruction/source owner for guidance, the canonical source and
regeneration path for managed payload, Planning for active continuation, and
Verification for proof declarations or evidence. Follow the returned request or
explicit scoped gap through the [owner procedure](../../../../.agentic-workspace/skills/workspace-startup/references/owners.md).
Recheck any authorized repair against the affected consumer. The obligation grants
no new mutation, review, proof or completion authority and creates no issue or Plan.

Publish through the exact Verification assessment request:

- **satisfied**: the bounded comparisons have evidence, with no unresolved current
  mismatch. Explain intentional exceptions and history controls where relevant.
- **failed**: a current mismatch remains, even if repair is deferred or forbidden.
  Name its owner and affected action; routing alone does not satisfy the condition.
- **unknown**: a necessary fact cannot be established. If GitHub is unavailable,
  name the specific decision and judgment that remain unknown; do not invent it
  or block unrelated work. Known findings remain reported alongside the gap.

Replace the concise [supporting evidence](repository-state-coherence-evidence.md)
with the current comparison and exact source references. It explains the judgment;
Verification's `proof/current/current-evidence.json` owns satisfaction. Supply the
actual observation time, outcome, bounded reason and evidence reference to the
returned request, answer its exact decision, and invoke its returned action.
Verify the resulting status and that satisfied ordinary entry has no need for
this identity. Follow returned recovery after an uncertain write; do not replay it.

Repeat assessments replace the same evidence and requirement entry. Do not append
run logs, make a second backlog, or copy this checklist into a scheduler prompt.
Stop when Verification reports the supported outcome and any remaining scoped
finding has its existing owner or an explicit gap.
