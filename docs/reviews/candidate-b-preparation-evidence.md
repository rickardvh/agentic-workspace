# Candidate B preparation evidence

## Issue-form preparation (#3262)

The first Candidate B probe adapts the existing repository issue-body aid and
integrates it into `github-issue-creation`. This is implementation evidence, not
independent acceptance of #3262 or completion of #3276.

### Exact subject and bounded trace

Baseline: accepted master `dda514d2f1d4ecc91e81cb7fba99d1c8d19e06ce`.
The after trace uses this PR's helper and the checked-in
`github-issue-body/examples/direction-request.json`, with all required semantic
fields explicitly supplied. Each trace runs in a fresh Python process on Windows
with the repository environment. No GitHub mutation, model worker, network fetch,
runtime resolution, or detail fetch occurs.

| Observation | Before | After |
| --- | ---: | ---: |
| Helper machine calls | 1 | 1 |
| Preparation-local source reads (excluding imports/request load) | 1 form | 1 form + 1 helper |
| YAML parses / request schema validations | 1 / 1 | 1 / 1 |
| Preparation SHA-256 digests, no additional source refs | 0 | 3 |
| Request JSON bytes, compact serialisation | 1373 | 1373 |
| Result JSON bytes, compact serialisation | 1501 | 2221 |
| Body bytes | 1033 | 873 |
| Preparation elapsed | 4.12 ms | 4.78 ms |
| Fresh-process elapsed, including Python/imports | 158.36 ms | 161.37 ms |
| Trace retries / repairs | 0 / 0 | 0 / 0 |

Single observations are not a statistical performance claim. Imported dependency
reads are outside the source-read count. The smaller body removes invented
optional-field TODO sections; supplied substantive fields remain intact. The
larger packet carries identity, completeness, and authority boundaries.

The previous ordinary skill required a model-mediated form inspection followed
by formatting/default reconciliation. The new ordinary path is one preparation
call after shaping, without carrying the 4735-byte direction form into the model
for that complete-input case. This is **procedure-step accounting (2 to 1)**,
not measured model inference calls: no controlled model comparison was run.
Incomplete input still requires semantic work; its diagnostic packet deliberately
returns current form fields/options. No speedup or lower total agent cost is
claimed. No cache/reuse layer is justified by this trace.

Development validation initially exposed a Windows test text-decoding assumption
and unsupported mandatory bug-form checkboxes; both were corrected before the
passing run. The initial edit command also encountered an unavailable bare
`python`; the existing repository environment was used. These are actual repair
costs, distinct from the zero-repair final trace.

### Fidelity, availability and subtraction

- Existing owner tests cover current direction/bug/review forms, supplied
  parent/leaf/later-evidence completion text, explicit checkbox assertions,
  missing/ambiguous/placeholder input, current template changes, helper/source/input
  drift and unrelated-source controls. The CLI exercises unavailable inputs and
  returns no body for incomplete requests.
- Preparation reads current forms and local source references. URLs/IDs remain
  explicitly external-currentness-unobserved. `--previous` compares only declared
  local preparation inputs and always recomputes; neither a prior packet nor a
  current comparison grants creation authority.
- The single retained formatter accepts typed shaped input. Planning lane/archive/
  decomposition conversion, semantic completion defaults, dropdown guessing and
  placeholder synthesis are removed. Existing scalar CLI convenience converges
  on the same preparation function.
- Python, PyYAML and jsonschema remain repository-maintainer dependencies in the
  existing locked environment. No shipped runtime, dependency, or public AW
  command is added. Missing tools/dependencies use the skill's direct current-form
  Markdown fallback.
- #3263 should derive its material availability contract only after the companion
  #3261 probe. This local comparison is not a proposed generic dependency ABI.
- #2929 creation replay is not exercised here: this implementation had an existing
  bounded issue owner and required no legitimate new issue. Creating a fixture
  issue merely for evidence would add external noise. That bounded inapplicability
  applies to this leaf, not to all remaining Candidate B work.

### Proof disposition and stop boundary

The existing issue-body owner suite is consolidated around input/form fidelity,
failure boundaries and exact local dependencies. Obsolete default-generation and
Planning-conversion tests are removed. Closure examples test text preservation,
not duplicate issue-shaping decisions. The existing aid-manifest suite and strict
source/payload check cover integration; no new CI constituent or cross-adapter
matrix is added. This is repository-only Python/Markdown work, so Rust semantics
and generated public contracts are unchanged.

Stop after focused owner/integration checks and repository commit checks pass,
then obtain independent review. Tests do not establish external-write authority,
independent acceptance, broad-owner reconciliation, Candidate B publication, or
#3276 completion. Total comparative operating cost remains unknown.

### Independent-review correction

The external review of `442009270` found that the bug form's `render: shell`
textarea attribute was ignored. The helper now wraps supplied text in the
form-selected code block, choosing a longer fence when the text contains
backticks. Unsupported render attributes fail explicitly. The current-form
assertion now expects the shell block; one focused owner case covers embedded
fences, a changed render language, and unsupported render syntax. This extends
form-structure fidelity without a new CI lane or adapter matrix. All 34 focused
issue-body/agent-aid cases pass. The earlier measurement remains a pre-correction
trace; it is not relabelled as a measurement of the corrected helper. Independent
recheck is still required.

## Trusted review preparation (#3261)

The ordinary independent-review skill now names one standard-library helper,
loaded from exact selected trusted Git bytes with Python isolated imports. The
review subject never selects or supplies executable tooling. Eligibility is an
external custody judgement; the helper's assertion is not proof of independence.
No review or approval of the implementation was performed by its implementer.

The existing GitHub GET transport is sufficient for collection: PR, all file
pages, reviews, inline comments, issue comments, head checks/statuses and linked
issue observations. Exact Git object reads supply trusted helper/procedure and
ancestor guidance identities. Current AW route/procedure references already
select the review skill; no new operating-decision, why/detail API or review
runtime is needed. Exact external pagination and comparison were the missing
deterministic mechanics.

The fixture has 101 files and one linked issue. First preparation and recheck each
perform nine logical GETs (pagination adds physical requests when required), one
Git tree listing and five exact Git blob reads (four guidance files plus helper).
Both reobserve external state; none of those reads is cached across an authority
barrier. The first compact-serialised packet is 29215 bytes and unchanged recheck
15384 bytes. Seven unchanged evidence bodies are replaced by exact prior identity
references. Obligations are retained unchanged. A lost comparison returns full
preparation. Source IDs/digests are carried; they are not semantic acknowledgement.

Manual collection requires those nine logical requests plus guidance reads and
model assembly/comparison. The executable path exposes one caller invocation for
first review or recheck. This is procedure/transport accounting, not an experiment
measuring inference calls. A pre-final fixture sample spent 1.839 ms collecting
and 1.552 ms rechecking after imports, excluding real network and process latency.
It establishes no live latency or total-agent-cost improvement. Fixture calls
have zero retries; the implementation corrected one fixture's moved-head counter
and restored explicit creation-skill closure terms exposed by the existing
workflow checks. Real network, credential and provider costs remain unknown.

Permanent proof adds one repo-helper owner suite for complete pagination, exact
subject/unknown evidence, review-only delta/obligation preservation and trusted
loader rejection of worktree replacement. It extends existing workflow skill
checks, not semantic verdict tests or a new CI constituent. #3262's formatter
tests remain the separate semantic-input preservation owner.

**Delta disposition: REVIEW_ONLY.** No second materially different delta consumer
has demonstrated a generic need. Review observations must not be memoised as
current authority; no cache, event ledger or session owner is added. The shared
#3263 need is only selected executable material identity/availability, not review
collection, comparison semantics or an executor.

## Predecessor reconciliation before deriving #3263

Baseline: accepted master `7cfca6a17`, which includes Candidate A and #3285/#3286.
#3059, #2981 and #2661 were already administratively closed when reobserved.
Their latest comments ask for this reconciliation; closure itself is not used as
proof. The table numbers refer to the ordered acceptance checkboxes in each
issue's current body. Grouped rows disposition every criterion without converting
these closed reconstruction owners into future optimisation backlogs.

Current source/evidence anchors:

- `docs/maintainer/operating-carriage.md`, native operating/carriage and invoke
  owners, and `tests/test_native_operating_carriage.py` /
  `tests/test_native_invoke_continuation.py`: exact compact/full carriage, bounded
  answers, work/source rejection, post-effect truth, fresh recovery and source
  delivery without satisfaction.
- `tests/test_native_former_routes.py`: negative selection reuse across fresh
  entry, unrelated changes and opaque discovery-set additions with no residue;
  native route admission owns source membership, not caller change history.
- Native Planning lifetime and source-reconciliation owners/tests preserve
  semantic subject lifetime, source-set changes, bounded semantic judgement and
  current repair; `native_instructions.rs` and `native_config.rs` remain policy
  owners. No helper result replaces their authority.
- `docs/maintainer/operating-carriage.md` records the accepted within-operation
  removal of duplicate source-view/schema construction (3 to 2 parses per start,
  12 to 8 per invoke) while reopening governing sources across barriers.
- Candidate A's recorded accepted delegation/Assignment and release-conformance
  evidence remains historical accepted evidence, not a new claim about hidden
  provider context or fresh independent review.

| Owner / criteria | Disposition | Current meaning and evidence |
| --- | --- | --- |
| #3059: 1–6, 8–9, 11, 13–14 | satisfied on current master | Compact/carried exact references and material; changed-work rejection; truthful continuation; selective source delivery and fresh reconstruction. Existing carriage/invoke/source owners and tests above. |
| #3059: 7 | satisfied on current master | Bounded answer plus already-authorised action is machine-carried; no generic action loop. Resource composition in #3265 is an additional consumer, not a prerequisite retroactively reopening this outcome. |
| #3059: 10 | satisfied on current master | Duplicate immutable derivation was eliminated with measured parse reduction; fresh barrier observations remain. |
| #3059: 12 | satisfied on current master | Accepted Assignment self-sufficient entry/return boundary remains; unobservable host context is explicitly unknown rather than a false savings claim. |
| #3059: 15 | obsolete/superseded | Reconstruction's exact first-cutover #2909 gate was consumed by accepted cutover/Candidate A. Candidate B has its own current preview admission; it cannot reuse old release acceptance. |
| #2981: 1, 3–6, 9–12, 14–17, 19–20 | satisfied on current master | Current producer/contracts/source sets and semantic subjects own reuse; native owner checks and exact carried references preserve barriers/partial invalidation. Stable eligibility remains separate from attempts; this does not assert that every owner is cached. |
| #2981: 2, 18 | satisfied on current master | Existing derivation elimination and explicit do-not-memoise source observations; no new cache is needed for either pilot. |
| #2981: 7–8 | satisfied on current master | Positive current selections and negative route posture are revalidated through existing native route/source identity; opaque registry membership invalidates negative selection. No durable helper result cache is inferred. |
| #2981: 13 | obsolete/superseded | A mandatory new cross-call economic demonstration is superseded by the latest profile-first gate: introduce a retained case only when cheaper validation is demonstrated. The pilots justify no new retained semantic cache. |
| #2981: 21 | obsolete/superseded | Historical reconstruction aggregation is superseded by Candidate B's exact integrated evidence and later publication, without another cache layer. |
| #2661: 1–14, 16 | satisfied on current master | Existing source/currentness, negative-route/source-set, semantic admission and carried-context controls reconstruct from current owners without event history. Drift affects dependent material, not an unrelated delivered source. |
| #2661: 15 | satisfied on current master | Direct entry has bounded current-source checks and no mandatory local residue. Cost is not proportional to unseen history; this does not promise constant runtime across arbitrary active owner/source counts. |
| #2661: 17 | obsolete/superseded | The old first-stable reconstruction gate is consumed; Candidate B retains its own public currentness/conformance and preview gates. |

No new bounded residual is supported by the two pilot traces. The later #3263
availability and #3265 resource composition leaves are already the smallest
explicit Candidate B owners; neither calls for broad reconstruction, a generic
why API or cross-domain delta. No new issue is created merely to obtain #2929
creation dogfood. Its real-creation replay remains bounded-inapplicable unless
subsequent integration exposes a legitimate new issue need.

## Review feedback follow-through

The #3287 review identified that file-identity comparison did not supply the actual
follow-up code patch. Recheck preparation now requests the exact prior-head to
current-head comparison and includes text patches, with no history/session state
or authority change. It refuses to treat divergent merge-base output, a capped
inventory, missing/truncated patches or transport failure as a complete tree
delta. These cases remain partial and require manual exact-tree inspection.
Draft and merged state are included and bracketed by the final subject read;
missing values are explicitly unavailable. The earlier nine-request measurement
describes unchanged-head rechecks: moved-head preparation now adds one bounded
GET. No revised latency or total-cost improvement is claimed.

Extended the existing preparation owner tests instead of adding a suite or CI
constituent: actual patch content and exact endpoints, comparison failure,
divergence, cap, incomplete/binary patch and head movement share the existing
recheck scenario. Four owner tests pass. These observations establish evidence
collection/currentness, not semantic review or independent acceptance. The bounded
claim has no remaining implementation blocker; independent re-review remains due.

## Minimal selected executable availability (#3263)

The two concrete pilots need helper bytes plus their actual material: current
issue forms and the existing Python project/lock for issue preparation; trusted
review helper plus testing procedure for review preparation. Supplied shaped
sources and external review evidence remain per-invocation inputs, not permanent
skill dependencies. The selected procedure's own bytes are always included.

The existing skill registry accepts an optional `executable` declaration:
a file entrypoint or the existing native `resources` command, plus a bounded
flat set of exact repository-relative files. There is no new registry, graph,
runtime or import/prose inference. Both repo pilots declare their material in
`tools/skills/REGISTRY.json`; the packaged resource skill references its existing
native command without copying source code into installed repositories.

Selected route/procedure detail carries one executable revision over the selected
declaration/procedure/material, native implementation/contract where applicable,
and relevant runtime compatibility. Unrelated directory contents and the whole
registry are excluded. A changed helper/template/contract changes this identity;
a missing required file fails explicitly. Ordinary root/vocabulary discovery
does not read those dependencies. Optional files are simply undeclared.

For external file helpers, passive discovery establishes material currentness,
**not Python, package, GitHub credential or transport availability**. Overall
availability remains unavailable with an explicit unknown-runtime reason until
the caller establishes its invocation environment; direct/Markdown use remains
valid. Native resource availability uses the existing pre-state compatibility
owner and compiled resource/public-contract identities. Incompatible readers are
reported as incompatible. A static/no-runtime reader cannot infer that this
runtime observation occurred from declaration files alone.

The existing aid checker validates the same declaration schema and exact file
closure without importing or running the helpers. Package-native identities are
compiled, so required resource code is not mirrored into host repos. Source and
shipped registry bytes are generated together. No mandatory metadata is added to
Markdown-only skills.

### Salvage disposition

- #2257 **reuse**: exact material dependencies, unavailable diagnostics, passive
  declaration checks, and minimal install/resource provenance.
- #2257 **adapt**: one native selected-detail result replaces the old universal
  viability/catalogue assumptions; executable material is optional and Markdown
  competence remains available. Native resources use compiled ownership.
- #2257 **retire from this design**: mandatory executable closure for every skill,
  old doctor/profile/lifecycle routing framework and blanket payload mirroring.
  This does not reopen or claim a reimplementation of closed historical scope.
- #2822 **evidence-only outside Candidate B**: no kernel/store/replay code, state,
  candidate graph, cycle detector or research session is promoted into product
  skill execution. Fresh observation and disposable comparison are already
  satisfied by existing public/native owners.

### Validation scope

Two native owner cases extend existing route tests for changed/missing material,
unrelated/optional source controls, passive discovery and installed native
compatibility/removal. Existing four-surface known-leaf tests cover unchanged
projection carriage rather than duplicating the new semantics across adapters.
One existing aid-checker case covers static dangling material and passive helper
bytes. No new CI constituent, broad scan or runtime probe is introduced.

## Native resource procedure (#3265)

The shipped resource skill now uses `compose: true` on the existing resource
request. Direct/no-resource work needs no call; an explicit direct request
returns without source/resource-owner reads or residue. Every effectful sequence
has a fixed shape: selected executable availability, native proposal, fresh
material check, exact native action admission. There is no action loop. Missing
isolation need/policy returns the native proposal. Composition never fills
`permits-isolation` or changes native preservation policy.

A composed result carries `resource_context` (exact target/task/changed/path)
and the native build environment. A fresh process reobserves the same resource;
it cannot submit an old effect revision in composition mode. Native owner errors
return unknown effect outcome and the exact context for reentry, never automatic
retry or replacement creation. Native proposal/result fields retain their own
effect semantics even when process execution succeeds.

The first installed consumer exposed one additional exact compatibility need:
knowing the native command exists does not establish support for composition.
Its declaration therefore names the existing reader capability
`resource-procedure-v1`. The existing runtime capability observation owns that
fact; unsupported capabilities fail closed. No separate version store or runtime
probe is introduced. Older readers reject the new optional declaration rather
than advertising the new callable mode.

### Matched scratch lifecycle observation

A Windows fresh-process fixture used the same target/task/current skill bytes,
created temporary material, and cleaned up the exact container. Both paths used
the current native resource semantics and left zero containers.

| Observation | Explicit proposal/action | Composed |
| --- | ---: | ---: |
| Public calls, create + cleanup | 4 | 2 |
| Native resource-owner resolutions | 4 | 4 |
| Additional selected availability checks | 0 | 4 |
| Serialised result bytes, all calls | 7450 | 4869 |
| Elapsed including processes | 175.39 ms | 148.52 ms |
| Residual resource containers | 0 | 0 |

This is one fixture sample, not a statistical latency or provider-cost claim.
The reduction removes deterministic action-envelope copying and process calls;
it does not remove required owner currentness checks. Selected availability
checks add registry/procedure/schema/runtime work; source-read/parse/digest
microcounts were not instrumented. No extra whole-workspace `start` or model
detail fetch is introduced by the composer itself. Native cleanup retains its
existing owner-reference observation. No repair/retry occurred in this final
trace; development corrected the result's exact cleanup-context carriage.

For worktrees, the deterministic public-call sequence contracts from proposal,
judgement-proposal, action (3) to proposal, judgement-plus-action (2), retaining the
one semantic necessity/policy judgement. Cleanup contracts from 2 calls to 1.
Fresh recovery similarly reobserves the same path and composes only the currently
available action. Direct use remains zero calls (or zero owner calls for an
explicit direct result). Those are procedure counts, not measured model inference.

### Proof and subtraction

The existing resource owner suite is reused for dirty/untracked/ignored material,
unique commits, interrupted registration/output cleanup, source/policy drift and
owner references. Two composition cases add only direct/scratch/reentry and
isolation-judgement handoff boundaries. Existing minimal/mirrored install lifecycle
cases now create/clean a composed resource and reject it after uninstall; they
do not duplicate the preservation matrix in every adapter. The combined resource
and skills-first suite passes 30 cases in 35.37 seconds.

The shipped procedure replaces manual action-envelope carriage with the native
mode and keeps the explicit proposal/action path as a bounded fallback. All
filesystem/Git effects remain in the original native owner. No wrapper script,
session state, scheduler, cache, research executor or arbitrary command runner is
retained.

## Candidate B implementation closeout boundary

#3262 is merged. The remaining review-preparation, availability and resource
implementation is supplied as a small dependent PR stack. Independent review
and merging remain external; no implementing agent has reviewed or approved the
stack. Candidate B itself is **not release-complete** until these leaves are
independently accepted/closed and the exact integrated preview is published and
verified. Candidate A's `preview-v0.55.0` remains the accepted release baseline.
No preview-v0.56.0 tag is created from unaccepted implementation heads.

No legitimate new issue was necessary during this tranche, so #2929 real creation
replay has the bounded inapplicability recorded above; no fixture issue or new
product defect was hidden in the coordination owner. #3260, Candidate C and
#2985 support-bearing admission remain separate and open. Total comparative
agent cost remains unknown despite the bounded procedure reductions.
