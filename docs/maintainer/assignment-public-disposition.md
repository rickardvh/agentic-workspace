# Former Assignment command disposition

The reconstruction retires the public `assignment close` and `assignment reassign`
command forms. They belonged to the former checked-in assignment/run-state
runtime, which is not the canonical native product. Their contracts, generated
exports/resources, catalogue entries and command conformance cases are removed
together. No equivalent hidden `start` request or new CLI verb is introduced.

The source for this disposition is the former implementation at
`127950fa15a11efe5f73cd7cbbc86d3d7fd8b162`, including
`src/agentic_workspace/contracts/operations/assignment.close.json` and
`assignment.reassign.json`, their
process conformance vectors and the former public-client lifecycle tests. Git
preserves that evidence; its successful former-host behavior is not current native
product proof.

| Former responsibility | Current disposition |
| --- | --- |
| Admit a choice for exact work and eligible execution facts | Retained by native Assignment requirements, comparison and configuration requests. Material changes require re-resolution. |
| Integrate returned work without attributing preexisting edits to a worker | Retained by native bounded patch return/integration, including concurrent edits and exact recovery. |
| Consume an accepted result into durable work | Retained by native Planning result admission. A worker or publication cannot close Planning. |
| Validate proof and admit bounded outcome evidence | Retained by native Verification and Assignment's current checked-outcome evidence. Publication is not proof or deciding authority. |
| Mutate former checked-in assignment/run records to `closed` | Retired representation; no native command is added solely to preserve that state transition. |
| Supersede a live/recoverable attempt, confirm worker release, and select fresh/resumed execution | The former command/export is retired. Full native attempt replacement, visibility, retention, pause/resume and host cleanup remain explicit #2210/#2947/#2817 gaps. No completion is inferred from export removal. |

The six historical external-operation receipts retain their original execution
date, fingerprints and observations, with the existing `stale` status and an
explicit retirement reason. Regeneration accepts an explicitly retired receipt
as historical content; clients still exclude it from readiness. Removing the
marker restores strict fingerprint checks. This is not a new successful execution
or current artifact admission. The former refresh runner still calls superseded
commands such as `install`, so its failed run cannot renew those receipts.

Proof combines rejected retired operations through Python/TypeScript clients,
rejected disguised owner requests through native CLI/JSON/Python/TypeScript,
generated surface consistency, and the retained native patch/Planning/proof
lifecycle. Full public capability ingress and exact artifact support remain with
#2606/#2986/#3077/#2909/#2990. This slice does not close those parents.

Validation on the source checkout: eight public owner-request rejection cases,
25 native patch/profile cases, nine generated Node cases, generated static proof
and the representative conformance shard pass. The broader former operation
receipt-refresh runner fails on superseded CLI/import assumptions and publishes
no successful receipt. Former runtime implementation branches remain migration
evidence and broader subtraction work, not exports restored by this change.
