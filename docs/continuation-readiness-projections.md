# Continuation Readiness Projections

Agentic Workspace uses derived projections for completion, repair, finding, external-evidence, migration, compaction, and automation-readiness questions. These projections assemble facts from Planning, Verification, report state, and provider-agnostic external evidence. They do not create a new state store, workflow runner, ticket bridge, or agent-owned classifier.

Use them when a compact report answer should make continuation cheaper without making AW decide the work for the agent.

## Projection Sections

| Report section | Purpose |
| --- | --- |
| `completion_contract` | Shows the Planning completion-contract lens: what must become true, what proves it, constraints, out-of-bounds work, iteration rule, and blocked stop condition. |
| `repair_loop_residue` | Summarizes validation-driven repair residue: observed problem, inspection findings, focused change, validation evidence, remaining gap, continuation input, and stop reason. |
| `structured_findings` | Provides a compact finding shape with owner and disposition fields so review, friction, Verification, and promotion residue can be routed or dismissed. |
| `external_evidence_safety` | Summarizes external source freshness, local state, divergence, stale-after, closeout safety, and refresh route without making external systems authoritative. |
| `continuation_next_actions` | Ranks next actions by available evidence, confidence, validation route, and stop condition. |
| `migration_pilot_template` | Defines an optional migration-pilot decomposition pattern with inventory, target design, parity proof, validation, and rollout boundaries. |
| `compact_output_criteria` | Names the fields compact outputs must preserve or point to: intent, evidence, next action, stop condition, changed surfaces, and unresolved risk. |
| `automation_readiness` | Gives a provider-agnostic checklist for evaluating external workflows while keeping execution, secrets, and side effects outside AW. |

## Boundary

AW should own the repo-visible substrate:

- checked-in Planning and Verification context;
- provider-agnostic external evidence snapshots;
- compact derived answers;
- proof, closeout, and continuation posture;
- repo-local readiness guidance.

AW should not own:

- runtime orchestration;
- workflow dispatch;
- secrets management;
- provider-specific ticket or CI synchronization;
- global task management;
- the final reasoning judgment about whether work is direct, planned, delegated, done, partial, or blocked.

## Use In Workflow

For ordinary work, start with:

```bash
agentic-workspace start --target ./repo --format json
```

Use a projection only when the compact answer, task shape, or closeout question needs it:

```bash
agentic-workspace report --target ./repo --section completion_contract --format json
agentic-workspace report --target ./repo --section external_evidence_safety --format json
agentic-workspace report --target ./repo --section continuation_next_actions --format json
```

The projections are designed to be restartable: a future session should recover the current intent, evidence, next action, stop condition, changed surfaces or selector, and unresolved risk without rereading chat history.
