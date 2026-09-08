# Current Verification strategy assessment

The existing Verification owner exposes a typed `verification/strategy/v1` request. It binds the agent's level/profile assessment to the exact current task, work, source and capability identity. This is execution strategy judgment, never proof, reviewer authentication or claim admission. Returned execution request sets carry the accepted assessment and current applicability request, so fresh invocation re-enters those owners without parent-chat state or hidden reconstruction.

| Source control | Current consumption | Remaining boundary |
| --- | --- | --- |
| `default_level` | Baseline guidance when no current assessment exists. | No inference that a baseline establishes task proof sufficiency. |
| `agent_may_escalate` | Raising the baseline is refused when forbidden. | Permission does not select a level automatically. |
| `agent_may_deescalate` | Lowering the baseline is refused when forbidden. | No source obligation is waived by level judgment. |
| `proof_profiles` | Current binding requirements and exact typed Planning declarations select profiles; recommended profiles remain optional. Agent selection adds known profiles. Required/optional/disallowed roles stay distinct. | Each required command needs current admitted evidence for that exact profile route. Absent Planning profile declarations remain unknown. |
| `domain_proof_lanes` | Existing path-scoped candidates remain available, subject to selected profile disallows. | Full composition, semantic scope and evidence sufficiency remain unresolved. |
| `subsystem_profiles`, `strict_closeout` | Existing source owner restrictions remain. | No subsystem fact reconstruction or claim waiver is introduced. |

A required profile cannot be omitted by an empty agent selection. Unknown selected profiles, unsupported profile fields, contradictory command roles and a required command forbidden by another selected profile refuse execution. Disallowed commands also restrict existing manifest and domain routes. Level changes and command availability do not satisfy independent review, task judgment or evidence lifetime.

The ordinary claim request's `evidence_refs` can discharge a profile's command
obligation when every required command has a current admitted native execution
receipt for that exact profile route. Freshness re-derives task/work identity,
selected strategy, runtime and source inputs; publication and exact execution
artifact admission are also required. The obligation reports missing commands
and supporting receipt refs. A manual report, failed command, matching command
from another route, stale source or unrelated task does not count.

This establishes only the configured command obligation. Task judgment,
independent/domain review and other assurance obligations remain with their
owners; no completion claim follows from command discharge. There is no new
receipt format, evidence store or producer.

Profile discovery is bounded to 32 descriptors and 16 command candidates. Selected profile metadata uses the existing 32 KiB selected-route bound; unselected profiles are not copied into the public strategy forest. Full source remains the current owner. Verification reads and validates the shared configuration once per owner view, then reuses that observation for applicability, domain candidates and strategy policy; no durable cache is added.

## Publication capacity and proof

A full authenticated 2048-entry receipt index now refuses a new execution before attempt admission or launching a process. The publication check and publisher share the same capacity predicate. Existing committed invocation replay remains valid. Capacity remains an explicit owner compaction gap; no historical index adoption or new compaction mechanism is introduced.

Four public consumers independently assert baseline/permission behavior, required versus recommended profiles, source/task drift, manifest/domain disallow, complete typed request execution/replay and the Planning projection gap. The authenticated full-index test asserts no process marker, no new attempt and unchanged index. Process success and publication still cannot manufacture proof.

No provider calls or monetary estimates were used. Implementation friction included an initially incorrect object wrapper around the existing request-set array and a stale-source fixture expecting a diagnostic where the canonical contract correctly raises a capability-currentness error. Both fixtures now use the actual public contract. These checks are implementation proof, not independent acceptance; #2334/#2613/#2981 remain open for the stated owner and evidence gaps.
