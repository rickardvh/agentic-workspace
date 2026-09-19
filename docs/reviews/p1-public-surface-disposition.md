# P1 public surface disposition

Implementation inventory for #3442, including the late resource integration in
#3475 after the M1-M5 extraction stack. #3473 is a contraction slice, not the final
post-migration closure. This updated disposition requires independent acceptance
at the post-#3475 head before #3442/#3441 administrative closure.

| Current surface | Disposition | Actual consumer and authority consequence |
| --- | --- | --- |
| start, compact/full/carried, exact detail references | KEEP_EXACT | CLI, Python, TypeScript and JSON clients resolve current domain facts, restrictions and requests; no effects. |
| invoke, exact action/reference carriage | KEEP_EXACT | The same clients invoke a current owner action; reobservation and owner authorization remain mandatory. |
| worker entry/expand/return | KEEP_EXACT | Sealed Assignment manual/process transport; distinct from owner admission, integration or execution authority. |
| resources audit/scratch/worktree operations | KEEP_EXACT | Native path, policy, Git lease and recovery semantics; useful directly, independently of skills. |
| resources/propose/v1 | KEEP_EXACT | Generic start clients and exact owner-reference fragments observe a proposal through the same resource primitive; discovery never executes it. |
| workspace.resources.scratch-create | KEEP_EXACT | Exact owner action creates one task-owned scratch container. |
| workspace.resources.scratch-remove | KEEP_EXACT | Exact owner action removes one current owned container, preserving retained or referenced material. |
| workspace.resources.scratch-prune | KEEP_EXACT | Exact owner action applies the primitive's bounded stale-resource cleanup policy. |
| workspace.resources.scratch-retain | KEEP_EXACT | Exact owner action records an explicit continuing-lifetime reason. |
| workspace.resources.scratch-release | KEEP_EXACT | Exact owner action releases retention after its owner settles that lifetime. |
| workspace.resources.worktree-create | KEEP_EXACT | Exact owner action applies current isolation policy and Git custody. |
| workspace.resources.worktree-remove | KEEP_EXACT | Exact owner action reconciles the same owned worktree and registration without erasing foreign work. |
| proof-procedure prepare/execute/direct | REMOVE | M3 deleted the wrapper, native dispatch, generated exports and descriptor. Proof method uses Verification exact requests/actions/receipts. |
| resources compose | REMOVE | M3 deleted fixed proposal/action chaining. Caller carries the exact returned action; uncertainty cannot replay. |
| native_methods selected skill switch | REMOVE | M3 removed skill-name dispatch; passive generic resource selection owns optional method. |
| routes discovery/selection and procedure answers | KEEP_EXACT | Current source applicability, lazy admission and caller-owned semantic carriage; policy applicability still needs explicit current route identity. |
| generic owner-reference resolution | KEEP_EXACT | Stable identity resolves one exact current native envelope, never executes or widens authority. |
| historical parser/affordance rows listed below | DEMOTE_INTERNAL | Source fixtures retained for maintenance only; per-row public audience and first-contact role claims removed. No installed transport dispatch or fallback. |

Native owner request/effect families are retained: Configuration/adoption/exposure
and recovery; instruction/intent/source reconciliation; Planning creation/update,
custody and review-claim admission; Assignment comparison, sealed delegation and
patch admission; Memory disposition, decision/advisory publication and recovery;
Verification scope, strategy, execution, receipt and claim admission; admitted
independent owner requests/operations. Each family owns facts, permission, effects
or evidence independently of optional skills. Removing one would force direct
clients through method or lose domain guarantees. They are not extra CLI commands.

The late resource owner is another retained request/effect family. Direct
`resources` consumers and generic `start`/`invoke` consumers use the same native
resource implementation, policy observation, exact proposal, currentness and
recovery checks. The direct primitive remains useful to clients managing paths
without semantic procedure. The generic owner makes those same effects addressable
through the existing owner-reference contract, avoiding a resource-specific skill
escape hatch. It is an adapter, not a second resource authority or a procedural
facade: no proposal/action chaining, retry loop, skill dispatch or implicit effect
is introduced. Both paths remain tested, including stale/protection rejection.

Seven operation declarations let exact references distinguish their effects;
collapsing them into an opaque dispatcher would lose that identity. Their schemas
repeat a small common argument shape because the existing contract admits each
operation independently. A new cross-operation schema registry solely to save
this bounded full-detail cost would add an authoring/resolution contract. Retain
the explicit declarations and account for their cost instead: the resource owner
is 4,418 JSON bytes, and the full diagnostic fixture grows to 84,489 bytes. The
test retains the former 81,000-byte ceiling for the non-resource contract, caps
this owner at 4,500 bytes and all full introspection at 86,000. Current-state
(28,000), compact (6,000) and former-selection (8,000) budgets remain unchanged.
These are diagnostic capacities, not a claim of cheaper ordinary operation.
Current decision revision maps include only relevant owners; full introspection
still exposes all declarations. Selecting a resource proposal makes its owner
relevant before exact action admission. This removes unselected effect hashes
from ordinary state instead of raising its budget or hiding current restrictions.
On the repair's Windows fixture, full/non-resource/state/compact/candidate sizes
were 84,489 / 79,998 / 27,995 / 3,434 / 1,066 JSON bytes. The existing four-transport
test enforces every budget, including unchanged state and compact ceilings.

M3 closes only from accepted #3467 extraction plus the resource-integration part
of #3475. The omission was discovered during integration. Final contraction must
therefore be checked after that integration, rather than inferring completeness
from the earlier #3473 inventory or closing #3441 before completed migration.

The finite CLI changed from five commands at #3464 to four: start, invoke, worker,
resources. No mega-command or compatibility alias was added. Historical report,
reconcile, skills, instructions, planning, memory and assignment command names are
not public aliases. Their useful current domain meaning is reached through exact
start/invoke owners. Source-maintenance metadata cannot register native commands.

Pre-v1 wrapper removals carry M3's major release metadata. Host update/removal uses
current payload/enclave inventories; neither those inventories nor generated
bindings reinstall removed wrappers. Resource route answers are retained because
they bind applicable instruction policy, not for procedural compatibility.

## Finite historical command inventory

Every row below is DEMOTE_INTERNAL, with the same source-maintenance-only consumer
and no native execution authority. Nested names are explicit, not implied aliases.

- `modules`
- `instructions`
- `instructions list`
- `instructions new`
- `instructions check`
- `instructions explain`
- `instructions routes`
- `instructions select-route`
- `instructions migrate`
- `summary`
- `planning`
- `planning new-plan`
- `planning targeted-write`
- `planning promote-to-plan`
- `planning owner-select`
- `planning decomposition-create`
- `planning lane-create`
- `planning lane-promote`
- `planning lane-activate`
- `planning lane-close`
- `planning lane-archive`
- `planning intake-artifact`
- `planning archive-plan`
- `planning closeout`
- `planning close-item`
- `planning create-review`
- `planning delegation-decision`
- `planning handoff`
- `planning report`
- `planning reconcile`
- `memory`
- `memory route`
- `memory sync-memory`
- `memory promotion-report`
- `memory capture-note`
- `memory create-note`
- `memory report`
- `evaluation`
- `evaluation register`
- `evaluation observe`
- `evaluation authority-refresh`
- `evaluation status`
- `evaluation report-preview`
- `evaluation local-delivery`
- `evaluation external-request`
- `evaluation external-host-result-import`
- `evaluation external-adapter-receipt`
- `evaluation external-delivery`
- `evaluation delivery-status`
- `evaluation retry`
- `evaluation transition`
- `evaluation prune`
- `checkpoint`
- `checkpoint write`
- `final-response`
- `final-response admit`
- `autopilot`
- `work-thread`
- `work-thread select`
- `work-thread carry-inspect`
- `work-thread carry-select`
- `work-thread carry-prune`
- `work-thread prune`
- `session-log`
- `session-log status`
- `session-log new-session`
- `session-log note`
- `session-log signal`
- `session-log analyze`
- `session-log repair`
- `session-log export`
- `start`
- `implement`
- `defaults`
- `proof`
- `setup`
- `ownership`
- `config`
- `system-intent`
- `note-delegation-outcome`
- `skills`
- `report`
- `reconcile`
- `external-evidence-submit`
- `external-evidence-query`
- `external-intent`
- `external-intent refresh-github`
- `preflight`
- `install`
- `init`
- `prompt`
- `prompt init`
- `prompt upgrade`
- `prompt uninstall`
- `status`
- `doctor`
- `upgrade`
- `uninstall`
- `agent-guidance`
- `agent-guidance promote`
- `agent-guidance edit`
- `agent-guidance merge`
- `agent-guidance split`
- `agent-guidance suppress`
- `agent-guidance revalidate`
- `agent-guidance weaken`
- `agent-guidance supersede`
- `agent-guidance retire`
- `agent-guidance delete`
- `assignment`
- `assignment admit`
- `assignment cleanup`
- `assignment status`
- `assignment dispatch`
- `assignment export`
- `assignment import`
- `assignment integrate`
- `assignment override`
- `assignment reject`
- `assignment repair`
- `correction-event`
- `correction-event identity-init`
- `correction-event submit`
- `correction-event query`
- `correction-event correct-dispute`
- `correction-event withdraw-supersede`
- `correction-event prune-compact`
