# Priority 4: repository control, Verification and configuration

This draft implements the Priority 4 daily-use lane under #3207. It composes the
accepted Verification, configuration writer, independent-owner and currentness
slices; it does not close the larger coordination issue or claim external review.

## Instruction and correction ownership

The source owner publishes exact Markdown in either canonical directory through
`instructions/edit-source/v1` and `instructions.write`. Source scope follows the
user's intended portability. Publication requires an exact bounded human answer
or an explicit current shared-policy grant for that exact instruction source.
The six optional authoring fields are `paths`, `read`, `reconcile`, `use`, `checks`
and `protect`; legacy route metadata remains readable but is not new authoring.

Both scopes use the same parser, source discovery and currentness. Local source
publication verifies Git ignore/untracked status. Existing unknown bytes, links,
changed postimages and stronger source protections cannot be acquired by shape.
The shared attempt store seals the exact publication; interruption after the
postimage uses a returned recovery request, without rewriting the source.
Publication records grant no ongoing mutation custody. Exact current published
bytes can admit local checks/reconciliation; edited bytes require fresh admission.
A fresh repository consumer can use the existing explicit Git-snapshot admission
for portable checked-in hard declarations without copying local execution state.

The new routed correction skill handles the bounded #2726 -> #2638 instruction
path. It interprets future intent and scope without requiring the user to name AW
storage. Task-only corrections stay unretained; other semantic destinations keep
their existing owners. The main skill points to it progressively. `use` resolves
short skill names or qualified routes through the existing bounded registry owner,
with explicit missing/ambiguous results and no effect authority by reference.

## Verification

Admitted inline instruction commands and named manifest checks enter the existing
selected-command producer. Exact command/source/runtime evidence satisfies only
the corresponding check. Multiple required commands require their own current
coverage; source drift invalidates affected evidence. Checks, reconciliation and
semantic claim sufficiency remain distinct.

`verification/reconcile-sources/v1` keeps its recoverable Verification receipt.
A shared policy delegation for the exact canonical source and resulting-work path
set can authorize the acting agent's semantic judgment. Removing/changing that
policy invalidates dependent judgment currentness. No delegation supplies an
independent reviewer or weakens another owner's proof floor.

`verification/review-claim/v1` provides a bounded positive semantic claim-review
path over exact current work/Planning subject, source postimages, strategy and
current evidence. A human answer or exact current policy delegation supplies the
judgment. Caller carriage can reuse that answer only while every binding remains
current; no rendered outcome or process-local authority is retained. Ordinary
unrequested work does not scan claim postimages or create proof/Planning state.
The accepted answer removes only Verification's generic semantic-judgment gap;
source reconciliation, required checks, strategy/profile/assurance floors, other
owners and unfinished Planning remain independently binding. Required external
review without an admitted sufficient producer returns an exact review gap; a
semantic agent judgment never impersonates independent acceptance.

## Configuration source lifetime and decisions

The existing durable-choice writer remains the mutation owner. An explicit shared
policy delegation for an exact config source can authorize ordinary durable edits;
module enablement, independent capability admission and delegation-policy editing
still require the exact human decision. Discovery/defaults are not recommendations
or permission. Source, policy, capability and postimage drift invalidate answers.

A deliberate deferred choice can invoke `configuration.defer-choice`. One bounded
current owner continuation per source/key lives in
`.agentic-workspace/local/configuration/`, outside human policy. It uses existing
attempt custody, survives a fresh task/process and exposes a newly current resume
request. Changed context requires fresh judgment; a resumed successful source edit
consumes its continuation. This is unresolved choice custody, not setup history,
learned state, a questionnaire engine or permission to replay an old answer.

| Recognized source intent | Current disposition |
| --- | --- |
| Shared/local invocation and source selection | Retained durable choice; exact source writer |
| Local safety and review ceilings | Retained, intersected by current native policy; source protections also cover config writes |
| Independent module settings | Current capability-owned settings, progressively exposed through the existing shared writer |
| Semantic deciding grants | Shared explicit exact-owner/path policy; never inferred from local state or prior effects |
| Verification strategies/profiles/commands | Verification manifest owns operational method; human floors remain binding |
| Assignment answers/target outcomes | Their existing work/evidence owners; not writable durable config fields |
| Deferred setup choice | Current configuration continuation outside policy |
| Former delegation/runtime/Memory/diagnostic controls | Existing native residual disposition retains exact source/field/affected-owner gaps; no silent source retirement |
| Deprecated posture knobs | Remain absent; no restored alias matrix |

The lived-in shared/local policy sources are not rewritten by this lane. The
existing roughly 945-to-120-line shared-config reduction remains an ownership
result, not a line-count acceptance rule. Source disposition tests cover recognized
former intent and unaffected direct work; read-only discovery creates no provider
work. Full automatic host delegation/adaptation stays with the later lane.

## Evidence

Instruction publication, instruction/Verification composition, claim review and
configuration owner tests exercise native
publication, local reconciliation and command execution, current semantic claim
review, explicit grants, fresh-session defer/resume, drift, interrupted publication,
unknown material, ignore policy and stronger repository protection. Related
configuration/source/proof/currentness/skills-first suites retain their existing
owner tests. Rust workspace tests, Clippy, generated/payload checks, Python lint
and type checks cover the shared implementation and projection contracts.

Historical validation before consolidation: 73 tests passed across Priority 4 control,
configuration admission and source reconciliation, followed by the added escaped
publication case (1 passed): 74 total in this focused set. Rust workspace tests,
Clippy, full lint/type checks and generated-file checks passed. Earlier broader
proof/currentness/resource/skills coverage contributed 172 passes and one
platform-dependent skip; its four historical-payload fixture failures were
corrected and passed in the final configuration run. Current-install fixtures
stage the actual shipped roster, while a separate negative preserves rejection
of historical provenance that omits new payload files. The repository's historical
installation receipt is not rewritten or presented as a new installation.

Review follow-through separates the satisfied check consequence from write
protections on the same instruction. The regression uses current native command
evidence across all four public interfaces, verifies a protected instruction write
still fails, and verifies source drift restores the completion restriction. The
full Priority 4 control suite passes after the fix (40 tests).

The ordinary full-response cost guard retains its 100,000-byte ceiling. Optional
configuration creation proposals are now returned only after the current read-only
`creation_discovery_request`; the route fixture response is approximately 99,200
bytes, down from 103,840. Discovery binds the current task, policy, sources and
capability contract, creates no files, and grants no write authority. The route,
configuration, Priority 4, carriage and skills suites pass (128 tests across the
main run and the corrected stale-error assertion rerun). Rust workspace tests pass.

The PR stays draft. Exact-candidate aggregate conformance and independent external
acceptance remain separately owned under #3207/#2909; broader #2726 and #2334
completion rules are not replaced by an implementation report.

Current test ownership and the reduced recurring CI selection supersede the
historical batch counts above; see [the reconstruction test audit](maintainer/test-strategy-reconstruction-audit.md).
