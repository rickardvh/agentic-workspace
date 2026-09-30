# Current Verification strategy assessment

The existing Verification owner exposes a typed `verification/strategy/v1` request. It binds the agent's level/profile assessment to the exact current task, work, source and capability identity. This is execution strategy judgement, never proof, reviewer authentication or claim admission. Returned execution request sets carry the accepted assessment and current applicability request, so fresh invocation re-enters those owners without parent-chat state or hidden reconstruction.

| Source control | Current consumption | Remaining boundary |
| --- | --- | --- |
| `default_level` | Baseline guidance when no current assessment exists. | No inference that a baseline establishes task proof sufficiency. |
| `agent_may_escalate` | Raising the baseline is refused when forbidden. | Permission does not select a level automatically. |
| `agent_may_deescalate` | Lowering the baseline is refused when forbidden. | No source obligation is waived by level judgement. |
| `proof_profiles` | Current binding requirements and exact typed Planning declarations select profiles; recommended profiles remain optional. Agent selection adds known profiles. Required/optional/disallowed roles stay distinct. | Each required command needs current admitted evidence for that exact profile route. Absent Planning profile declarations remain unknown. |
| `domain_proof_lanes` | Existing path-scoped candidates remain available, subject to selected profile disallows. | Full composition, semantic scope and evidence sufficiency remain unresolved. |
| `subsystem_profiles`, `strict_closeout` | Existing source owner restrictions remain. | No subsystem fact reconstruction or claim waiver is introduced. |

A required profile cannot be omitted by an empty agent selection. Unknown selected profiles, unsupported profile fields, contradictory command roles and a required command forbidden by another selected profile refuse execution. Disallowed commands also restrict existing manifest and domain routes. Level changes and command availability do not satisfy independent review, task judgement or evidence lifetime.

The ordinary claim request's `evidence_refs` can discharge a profile's command
obligation when every required command has a current admitted native execution
receipt for that exact profile route. Freshness re-derives task/work identity,
selected strategy, runtime and source inputs; local custody or repository publication and exact execution
artefact admission are also required. The obligation reports missing commands
and supporting receipt refs. A manual report, failed command, matching command
from another route, stale source or unrelated task does not count.

This establishes only the configured command obligation. Task judgement,
independent/domain review and other assurance obligations remain with their
owners; no completion claim follows from command discharge. There is no new
evidence store or producer for profile discharge.

Profile discovery is bounded to 32 descriptors and 16 command candidates. Selected profile metadata uses the existing 32 KiB selected-route bound; unselected profiles are not copied into the public strategy forest. Full source remains the current owner. Verification reads and validates the shared configuration once per owner view, then reuses that observation for applicability, domain candidates and strategy policy; no durable cache is added.

## Local execution and repository promotion

Ordinary `proof.report` execution retains its receipt in the existing ignored
Verification run/commit material. Its `proof://local/…` reference is usable by
current-checkout claim consumers, with the same runtime, source, result and
producer checks. It does not create a repository receipt or change the index.
Local references do not promise portability to another checkout.

When a durable repository consumer needs the execution, use the current
`verification/execute-selected/v1` request with its `promotion` material:
the local `evidence_ref`, repository `consumer` path and reason for retention.
The consumer must be a current Planning-owned execplan, created or updated through
its owner, whose `references` or `proof` material names the returned
`repository_reference`. An arbitrary file containing that string cannot authorize
publication. Verification binds the admitted owner material and checks the original exact successful execution before
publishing; it does not rerun the command. A missing or changed consumer, stale
proof, failed result or unproven manual report cannot gain repository authority.

The published receipt carries a bounded repository observation. It preserves the
original receipt ID, subject fingerprint and producer/outcome digests alongside
the portable subject and selected-command result. Runtime executable content
hashes, image/configuration and source hashes remain exact; machine paths and
daemon locators remain in local custody. Fresh repository claims validate the
owner consumer, projection integrity, current runtime content and source inputs
without opening the original local run or command output. Raw output and derived
measurements remain local. Repository provenance does not grant local effect
replay or independent acceptance; modified source/runtime/consumer fails closed.

The portable publication also binds the exact index postimage in its validated
repository observation. A fresh checkout can admit that index for the next
promotion, which establishes its own local attempt and recovery custody. Altered
index bytes fail admission. The predecessor's absent local carrier is not recreated;
its repository receipt remains protected during automatic supersession.

The 2048-entry publication capacity check still protects repository promotion.
It does not prevent ordinary local execution. Existing source-reconciliation
current groups remain repository-owned evidence through their own producer.

Verification disposition protects live repository consumers. For authenticated
old executions without such consumers, it offers transfer to the existing local
run carrier before retiring the repository copy and its index entry. Unknown
custody stays protected. Exact interrupted-retirement recovery and a quiet second
pass use the existing retention owner. Process success, storage lifetime and
publication do not establish task completion or independent acceptance.

For authenticated legacy receipts with an admitted Planning consumer, the same
disposition request offers `repository_transfers`. Its bounded `retain_repository`
decision preserves the consumer's historical dependency closure in the portable
format under the existing stable references, retaining original bytes in the
original local runs. This is a representation change, not fresh proof: stale
evidence remains stale. Interrupted conversion resumes from exact pre/postimages.

No provider calls or monetary estimates were used. Implementation friction included an initially incorrect object wrapper around the existing request-set array and a stale-source fixture expecting a diagnostic where the canonical contract correctly raises a capability-currentness error. Both fixtures now use the actual public contract. These checks are implementation proof, not independent acceptance; #2334/#2613/#2981 remain open for the stated owner and evidence gaps.
