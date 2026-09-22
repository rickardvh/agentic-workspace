# Native Planning creation

## Current work, remembered selection, and task posture

`planning.current_work_id` is the public current-work identity. `selection_scope`
is the advisory local thread cursor (or `default` storage slot). Old selector
files named that cursor `current_work_id`; the native reader treats it only as a
legacy scope alias and rejects conflicting aliases. Newly acquired selectors
write `selection_scope` and mechanically derive the legacy cursor alias from it.
No task wording, thread name, or default-slot match
admits a current owner.

Fresh entry exposes `incumbent_owner` as remembered context and leaves
`selected_owner` null until an explicit continuation or exact retained
current-work/source custody establishes the relation. Existing custody and
source-currentness checks still govern every mutation. An unresolved or independent
relation exposes no material update, recovery, handoff retention or result adoption
request. Retargeting a material request to fresh work cannot bypass this gate.
An exact retained update can establish same-work continuation only against its
committed postimage; it does not refresh the previous source reconciliation.

The continuation request accepts `answer: independent` separately from optional
`task_posture: direct | planned`. With posture omitted, `task_relation` is
independent and `required_transition` remains `determine-posture`; this is not a
direct-work assertion. The emitted `planning-posture` decision then offers direct
and planned choices through `planning/posture/v1`; ordinary bounded answering
constructs the next request without manually adding a hidden posture field.
Direct posture creates no owner or selector residue.
Planned posture allows the existing creation and explicit selection path,
preserving the previous owner. The deprecated `unrelated-direct` input derives
independent/direct semantics and is rejected alongside `planning.create`.

This preserves the separation established by #2175/#2229 and #2277/#2279:
current work binds admission, actor-local selection supplies a hint, and semantic
relation and required transition remain distinct. There is no new task registry
or relevance classifier. Reworded continuation still requires explicit judgement.

The public Planning `planning/create/v1` request creates one current compact `planning-execplan/v1` owner. Request material uses the canonical schema's existing field definitions. The acting agent authors outcome, scope, constraints, stops, dependency facts, proof obligations, continuation and next action. Rust supplies only the confined work-bound identity/path and initial planned/shaping revision; it does not fill placeholder judgements or generate proof.

Creation exclusively acquires an absent owner document. It does not acquire a selector, alter the former Planning state file, or activate another owner. Its result offers a separate exact current continuation request. Existing selector ownership remains preserved. Direct unrelated work creates no state.

The new document retains only typed creation provenance: exact invocation digest and prepared immutable attempt/commit custody. The full invocation is retained once by the immutable effect owner. The common attempt owner validates those references; Planning verifies the exact creation record and original owner identity before excluding provenance from semantic identity. Exact initial bytes are required only to replay creation; later current owner edits remain readable and produce normal semantic-versus-attempt reconciliation. The final file digest is not an input to its own prepared commit, avoiding circular provenance identity. This is one existing owner document, not a new ledger or Planning representation.

Completed creation can replay in a fresh process with exact retained commit evidence. Creation replay with a missing commit or changed source/provenance stays uncertain or rejected, with no overwrite or blind retry. Creation grants no completion claim or proof. Later source-owner semantic revisions stale dependent work; same-semantic attempt observations preserve subject identity. Neither may replay the stale creation invocation or pretend it still owns the changed bytes.

Public proof independently exercises native CLI with no Python/Node on PATH, Python, TypeScript and JSON start/invoke, separate selection and fresh owner continuation, stale work/arguments/occupied paths, changed provenance/material, and missing completion evidence. A missing commit fixture proves conservative uncertainty, not actual OS crash scheduling or power-loss durability. Existing native attempt and owner tests cover their separate process-interruption contracts.

An explicit destination request can now switch an already native-owned selector. The existing Planning reconciliation invocation retains its exact prior selector digest, independently inspected committed producer custody and destination selector fields. These are effect-currentness inputs, separate from material Planning identity. Creation still does not select the new owner. The selector owner validates and retains the same bounded transition in its existing carrier and common immutable attempt; it creates no transfer ledger and changes neither Plan body.

Fresh continuation accepts retained transition context only after producer validation and exact current postimage comparison. Stale preimages, changed destination semantics, forged invocation fields and unfamiliar postimages preserve current bytes. Public proof exercises all four consumers, and a child-process exit fixture proves recovery in another process after both attempt and commit retention. This proves these explicit publication boundaries, not power-loss durability or universal writer coordination. The owner recomputes the small current selector/source projection and reuses only exactly validated producer evidence; no memoisation framework is introduced (#2981).

Historical local selectors still require authority-correct acquisition or transfer before replacement (#3001/#2984). Their old receipts, valid JSON and current hashes are observations, not release authority; malformed historical TypeScript scaffolds are not silently converted into a new semantic authority. No currently admitted native authority-holder acquisition adapter is supplied by this layer. It does not establish full native delegation, source configuration migration, independent acceptance or first-stable admission.

A selected owner whose lifecycle or phase is explicitly closed, complete,
completed or archived remains preserved read-only. Unrelated work need not
acquire Planning state from that quiescent source. Same-task continuation keeps
the exact Planning subject, scope and proof obligations visible and requires
owner reentry; the status grants neither task completion nor Verification.
Closeout remains active, and unknown lifecycle values fail closed. Explicit
selection of another live owner continues to require native selector custody;
historical selectors gain no transfer authority from being closed.

Native-created owners with admitted continuation expose `planning/update/v1` through `planning.update_requests`.
The caller supplies the canonical material and frontier fields; Rust preserves
identity, path and creation custody and returns an exact `planning.update`
invocation. Historical Plans without native creation custody remain read-only.
The update shares Planning's existing lock and preserves the selector. A later
current continuation reconciles the new source. Material changes stale dependent
proof, while frontier-only changes preserve material identity. Reopening a closed
or blocked owner requires explicit caller-authored frontier inputs and grants no
proof or task completion.

Only the latest update provenance is carried by the Plan; common immutable
attempts retain the preceding invocations. Unknown bytes are preserved. A process
exit after common admission but before the Plan retains its postimage leaves the
original source intact and the attempt uncertain: neither an existing attempt
filename nor retry grants custody. A process exit after the exact postimage is
retained permits fresh `start` with admitted continuation to return `planning.pending_update.invocation`;
`invoke` still validates current task, capability and restrictions before it
finishes the prepared commit. This is process-interruption evidence, not a
power-loss durability claim or complete automatic recovery of the initial gap.

Retained Python record, deletion and rollback paths and TypeScript Plan overwrite
paths refuse native provenance carriers and route back to this owner. The marker
is a restriction only; it cannot acquire custody. Native operations share the
existing Planning lock and recheck exact bytes; arbitrary external editors are
not participants in that cooperative protocol.

The original invocation keeps its exact task identity, including wording and
changed paths. After a fresh caller admits current `continue-selected`, the
owner directly exposes `planning.update-recover`. The explicit recovery request
remains available to clients; no model request-copying turn is needed. This is a new
current re-entry action bound to the exact retained postimage, effect and
selected owner. It cannot also change selection, admit historical custody or
substitute the old task identity. Stale source, capability, continuation and
unrelated work are rejected.

Recovery has its own common admission and result. Under the existing Planning
lock it finalises only the original prepared outcome, returning original
outcome/custody separately from its own. It writes no material Plan bytes and
grants neither proof nor terminality. Interruption before its own result remains
common attempt uncertainty; an independently observable committed original
outcome does not fabricate completion of the re-entry attempt. No filename scan
or additional recovery ledger supplies missing custody. The earlier original
admission-before-postimage uncertainty remains unchanged.

The Rust process test terminates the actual update writer after publication and
recovers through fresh reworded current continuation. Four public consumers
also exercise genuine producer bytes with the result deliberately withheld;
that deterministic fixture is not another process-interruption observation.

Current creation and update requests also accept the existing optional canonical
`adaptive_assurance`, `risk_registry_refs` and `invariant_refs` declarations.
Omitting them creates no defaults; omitting them from an update preserves the
current owner's value. Explicit empty lists mean known empty, while absent
fields remain unknown. Invalid declarations preserve the source and fail closed.
The Planning owner retains these exact declarations in its existing material
proof state. A change therefore stales dependent subject-bound proof even when
scope and frontier stay unchanged. Verification applicability consumes only the
declared profiles and exact risk/invariant references, never prose, successful
process exits or Planning completion. These declarations grant no evidence.
Verification strategy selects those same current profile IDs as Planning-owned
requirements and exposes the configured command obligations. An unavailable
profile remains an exact strategy gap. An explicit empty profile list removes
no independently binding requirement and grants no proof or waiver.

Strategy regression negatives inspect the composed public decision's pending
and ready operations. Two inherited assertions previously read the removed
private `verification.contribution`; their replacement preserves the stale-work
and disallowed-command no-operation invariants across all four consumers.

For already Planning-owned work, a current sealed Assignment handoff directly
exposes the exact `planning.update` operation. The explicit
`planning.handoff_retention_requests` remain available to clients. Planning records assigned, returned,
or integration-pending continuation in its existing relationship observations;
it does not create another execution ledger or interpret worker success as
acceptance. Direct work has no retention request and acquires no Plan.

After interruption, continue/reconcile the selected owner normally.
`planning.handoff_continuation` exposes the original task, scope and complete
request set with `revalidation-required` status. Follow that reentry through
ordinary `start`; Assignment, transport, integration and Verification each
revalidate their own inputs. Changed dependencies, policy or work cannot renew
an old result. Retention itself grants no execution, result-use, integration,
proof or completion authority.

Observation-only updates keep the semantic Planning subject unchanged. An
earlier explicit Planning continuation can survive only when it is the exact
request retained in the current committed owner payload, the same owner is
selected and its semantic subject still matches. Modified answers, foreign or
uncommitted payloads, different owners and material edits do not qualify.
Source selection and capability/work validation remain independent checks.

Later observations replace only the same assignment's retained observation;
returned work cannot regress to assigned, and integrated work sheds obsolete
integration-pending state. Unknown or other-assignment observations are
preserved for responsible-owner reconciliation. Existing return adoption clears
only its own retained continuation after actual result admission/integration.
The final canonical document and serialised source bound are checked before
admission, with exact published bytes checked again before writing.

This advances proportional #2970/#2947 continuation without claiming complete
independent-owner ingress, all transport/cancellation outcomes, or cumulative
#2909/#2990 acceptance. Existing Planning creation, material maintenance and
postimage recovery remain the same owner paths.


## Terminal retention

Ordinary entry exposes a bounded `planning_retention` hint when Planning history
needs current judgment or an interrupted retirement needs recovery. Its detail
reference resolves `planning.terminal_retention`, including an exact
`planning/terminal-disposition/v1` request. Read the offered records before
asserting terminal intent, absence of unresolved work and absence of continuing
value. Archive location merely discovers legacy candidates; it grants no custody.
The native operation admits the exact source preimages and current request.

The owner preserves current selection and explicit consumers in Planning, proof,
Memory, Verification, evaluation, reconstruction and system-intent sources.
Source changes or newly appearing consumers stale disposition. Each batch offers
at most 32 unreferenced records. Source traversal is confined, rejects links and
reparse points, and bounds depth, file count and bytes; interpreter caches are not
owner sources. Historical consumers must be disposed by their own owners first.

Retirement retains exact immutable attempt custody in a temporary local Planning
carrier before removing any source. A fresh `planning/recover-terminal-disposition/v1`
request can finish only the admitted deletion set, preserving changed or newly
referenced remaining sources. The last recovery attempt is retained separately
from the original attempt, allowing another fresh recovery after interruption.
Settled disposition clears its carrier and creates no tracked tombstone. Generic
local effect receipts retain their existing lifecycle; this operation does not
claim to bound that separate owner or to complete the underlying work.

The cooperative Planning lock and immediate source checks provide process
interruption safety, not power-loss durability or exclusion of arbitrary external
editors. A crash before the complete carrier is published preserves the sources
and uncertain admission. Native lifecycle evidence covers creation, selection,
closure and disposal while keeping only the current selected owner; archive
migration still requires each record's current semantic disposition.
