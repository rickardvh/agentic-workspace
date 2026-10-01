# Report views for continuing work

Some AW reports combine existing Planning, Verification and task information into
small views that make interrupted work cheaper to resume.

These views do not create another state store or workflow engine. They summarise
records that already exist.

## Available report sections

| Report section | What it helps answer |
| --- | --- |
| `completion_contract` | What must be true before the work can honestly be called complete? |
| `repair_loop_residue` | What problem was found, what changed, what was checked and what remains? |
| `structured_findings` | What finding was recorded and what still needs to happen with it? |
| `external_evidence_safety` | Is external evidence still current enough to use? |
| `workflow_compliance_summary` | Which required workflow steps were completed, skipped or unavailable? |
| `continuation_next_actions` | What are the most useful next actions and what would let the agent stop? |
| `migration_pilot_template` | How can a migration be split into inventory, target design, parity checks and rollout? |
| `compact_output_criteria` | Which facts must a compact handoff preserve? |
| `automation_readiness` | What should be checked before relying on an external workflow? |
| `section_catalog` | Which optional report sections exist? |

The exact JSON field names are part of the API. Users do not need to learn a
separate vocabulary for the fact that these are generated report views.

## What AW should and should not do

AW can keep repository-visible task records, saved evidence and compact summaries.

It should not become:

- a workflow dispatcher;
- a secrets manager;
- a provider-specific ticket synchroniser;
- a global task manager;
- the final judge of whether implementation choices are good.

The agent or human still interprets the work and decides among legitimate options.

## Use the views only when they help

Start with the normal current-task result:

```bash
agentic-workspace start --target ./repo --format json
```

Load an optional report section only when the current task or handoff needs it.

For issue or project completion, distinguish the final requested outcome from a
useful partial change. A partial PR should not silently become evidence that the
whole issue is complete.

A future session should be able to recover:

- the intended outcome;
- important evidence;
- the next unfinished action;
- the condition for stopping;
- material changed files;
- unresolved risks.

It should not need the original chat transcript to understand those facts.
