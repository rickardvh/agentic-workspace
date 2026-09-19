# P1 powerskill source audit and proposed implementation boundary

Status: historical design record from accepted #3454 under #3409 / #3445.
The current implementation disposition and bounded evidence are recorded in
[P1 migration integration](powerskill-p1-integration.md). The proposal and
future-tense statements below describe the design subject, not a second active
workflow or a claim that implementation/review has completed.

Audit subject: `cc2b236b0d0a546d0c47c9c1e59ede857d679477` (2026-09-19).
The working checkout was clean before creating this lane's Planning owner. Both
native binaries built with `cargo build --locked --workspace --bins`.

## Evidence and coverage

The ordinary path is `operating::start` -> `native_public::start_selected` ->
current owner contributions -> `compile_value` -> the operating projection.
`operating::invoke` reobserves an exact owner action; it does not interpret skill
prose. `native_frontier::Resolution` controls optional detail, while mandatory
contributions remain present. `native_methods::BINDINGS` currently contains two
fixed consumers: resources and proof-procedure. Neither is a generic semantic
skill interpreter.

The source boundary includes these native entrypoints and their directly relevant
consumers: `native_routes`, `native_methods`, `native_instructions`,
`native_configuration_procedure`, `native_resources`, `native_proof_procedure`,
`native_planning`, `native_requirements`, `native_assignment`,
`native_memory_learning`, `native_memory`, `native_skill_exposure`, and the
operating reference/answer path. Symbols below are in
`crates/agentic-workspace-core/src/` at the audit subject.

Agent-facing sources include the eight entries in
`.agentic-workspace/skills/REGISTRY.json`, the named Memory capture/hygiene
procedures, package Planning skills, `tools/skills/REGISTRY.json` maintainer
entrypoints, `AGENTS.md`, the WORKFLOW pointer, applicable operating instructions,
and the knowledge-disposition reference. Package bootstrap and payload copies
are distribution consequences, not additional procedure owners.

Coverage is at material procedure/owner-group level, not every conditional.
Compiler/parser internals, filesystem safety, custody journals, standalone domain
algorithms, CI implementation, fixtures and release automation are excluded as
execution/validation mechanisms. Historical `instruction_clause_ir.py` and its
contract are not a demonstrated live ordinary native extension seam; do not
restore them. Current source-maintenance enclaves in OWNERSHIP remain distinct
from the shipped product. A search hit or an old command in prose does not prove
current executability.

The external [Agent Skills format](https://agentskills.io/specification) and
[host loading guide](https://agentskills.io/client-implementation/adding-skills-support)
were read on 2026-09-19. A selected SKILL.md is loaded in full; additional relative
resources permit lazy delivery. These format observations do not prove activation
or execution on any AW host.

## Complete proposed group disposition

`M` means MIGRATE; `K` means KEEP_NATIVE (or keep an already adequate transparent
skill unchanged); `R` means RETIRE_OR_MERGE. These are proposed dispositions for
review, not permission to remove binding meaning. Mixed groups identify both
sides of the boundary. M1Ã¢â‚¬â€œM5 are bounded implementation destinations under #3411;
C1Ã¢â‚¬â€œC3 below belong to #3410.

| Group and current source/consumer | Disposition and destination | Guarantee retained / subtraction obligation | Agent-facing; public; module consequence |
| --- | --- | --- | --- |
| Startup SKILL.md: ordinary use, evidence, correction, specialized routes, exact requests, unavailable runtime, residue | M, M1: small entry plus referenced procedure fragments | Preserve evidence sufficiency, authority distinctions and actual no-runtime limits. Remove duplicated full-tree text from the entry; do not create a second manual flow. | simplify/migrate; keep start/invoke; none |
| `workspace-intent-discovery`, `workspace-work-shape` | M/R, M1: one intent procedure with vocabulary as a reference | Agent decides meaning and work shape; remove duplicate shape/routing prose and reference-only skill catalogue entry where no independent consumer needs it. | merge; no new operation; retain Planning domain meaning |
| `workspace-transition-gates` | R, M1: retain unique interpretive material with relevant startup/proof fragments | Delete competing phase choreography and stale fallback names; preserve actual restrictions through native owners. | retire/merge; #3442 audits surviving gate concepts; none |
| Setup SKILL.md plus `native_configuration_procedure::{concern,observe,attach}` | M/K, M2: setup fragments over exact Configuration requests | Move method selection/post-write interpretation to skills. Keep effective configuration facts, write permissions, affected-owner observation and confirmed-effect semantics native. Do not relabel all `observe` branches as procedure. | migrate; keep useful behavior observation pending #3442; retain domain meaning |
| Correction SKILL.md: instruction vs advisory vs decision vs ordinary source repair | M, M2: selected destination fragments | Keep publication, source delegations, receiving evidence, no-retention and recovery in current owners. Remove repeated request-transport instructions already owned by startup. | migrate; keep exact writers; none |
| `native_resources::compose` and resource SKILL.md | M/K, M3: generic bounded composition plus resource fragments | Remove skill-name selection and fixed proposal/action choreography. Keep resource observation, path bounds, policy, retention, Git registration, leases and cleanup recovery native. | migrate; remove compose-specific facade after equivalent direct owner access; none |
| `native_proof_procedure::view/present` and proof SKILL.md | M/K, M3: proof sequence over generic composition | Remove fixed prepare/execute/admit sequence and SKILL/COMMAND switch. Keep unique-required-action determination, exact check execution, receipt admission, strict claims and no-retry recovery in Verification. | migrate; proof-procedure removal under #3442 after migration; retain Verification meaning |
| Planning high-assurance lifecycle, orchestrator workflow, autopilot | M/R, M4d / #3459: final umbrella consolidation | Merge overlapping umbrellas; preserve local/non-local restrictions and current owner handoffs. Replace historical command suggestions with supported owner references. | migrate/merge; worker remains direct pending #3442; candidate procedural descriptor cleanup #3443 |
| Planning decompose, intake, new-plan-tighten, reporting, intent verification, closeout | M/K, M4a / #3456: Planning fragments plus adequate plain references | Move selection/sequence only. Keep original intent, owner creation/update, continuity, custody and claim evidence native. Small single-purpose interpretation may remain ordinary Markdown. No independent phase taxonomy. | migrate/simplify; exact Planning operations retained; retain domain meaning |
| Planning assurance-delegation, manual-delegation, returned-result | M/K, M4b / #3457: pre-assignment, transport and return fragments | Assignment keeps feasibility/comparison admission, binding target, sealed input/output, integration and recovery. Delete duplicated legacy `assignment.*` command recipes where unsupported. No P2 delegation-methodology expansion. | migrate; retain worker and exact assignment operations pending #3442; retain domain meaning |
| Planning review-pass / promote-review-findings | K/M, M4c / #3458: preserve bounded review meaning; route continuation through common fragments | Independent review remains externally initiated and never becomes a skill completion flag. Remove duplicate closeout/activation procedure, not reviewer evidence. | simplify where duplicated; no new operation; retain review meaning |
| Memory capture/hygiene and `native_memory_learning::view` | M/K, M5: capture/disposition fragments | Move richest-owner/materiality explanation; keep explicit candidate nomination, pending claim consequences, source-set identity, receiving-source validation, publication and no-retention admission native. Optional-skill bypass must not drop candidate obligations. | migrate; exact Memory operations retained; retain advisory domain meaning |
| Package Memory/Planning bootstrap adoption/upgrade/uninstall guidance | R/K, M2: consolidate shared setup method; retain domain-specific preservation | No resurrection of retired package host commands. Keep custom-content and Memory-state preservation, separate from Configuration footprint removal. | merge/simplify; #3442 checks lifecycle resurrection; retain module state boundaries |
| Maintainer issue shaping/creation, PR review, dogfood, ownership/path/foundation checks | K/R, M5: keep already transparent bounded procedures; merge duplicated source-owner guidance | Keep source-only helper transport and independent review eligibility. `ownership-ledger-check` still calls WORKFLOW a shared contract although WORKFLOW calls itself a pointer: repair this misleading owner reference. Do not migrate all helper code into a runtime. | simplify exact duplicate; no shipped command; none |
| `native_routes::{catalogue,procedure,discovery}` / semantic route selection | K with C1 extension | Keep passive source admission, collisions, declared registry roots and agent applicability. Add procedure-resource identity without a second catalogue or per-skill native dispatch. | keep exact routes; audit route facade under #3442; no module-name registration requirement |
| `native_public`, `operating`, `native_frontier`, `native_instructions`, Assignment/Planning/Memory/Verification domain contributions | K | Current composition, binding applicability, exact references, effect/claim restrictions and recovery are domain/shared mechanics. Advisory question wording may become a skill fragment; the owner request and unresolved consequence survive optional-skill absence. | inspectable current detail; keep exact primitives; #3443 audits procedural contribution fields |
| `AGENTS.md` / WORKFLOW / operating instructions / knowledge-disposition reference | K/R, M1 and M5 | Keep the small bootstrap pointer and repository-owned constraints. Reconcile competing procedural wording through its actual source owner without changing trust pins. #3417 is closed and the promotion reference now delegates to startup/correction; preserve that correction. | keep pointer, merge competing method prose; no new operation; none |

Each migration child must include its source/payload mirror changes and deletion
obligations. A later discovered member of one of these groups stays in that
group's obligation. An actually new semantic group requires an explicit audit
revision. No row is excluded merely because extraction is difficult.

## Minimum design proposal

### 1. Source and loading

Use an ordinary small SKILL.md with a relative link to `references/procedure.md`.
That resource contains one fenced, versioned JSON control object and ordinary
Markdown fragments referenced by exact relative path. JSON avoids a new parser
dependency and ambiguous YAML coercion. The selected control skeleton is bounded;
large branch prose is not embedded in it. The same natural-language question and
branch descriptions serve manual readers. No generated fallback transcript or
second independently maintained tree.

The standard entry names the configured AW invocation and the procedure resource;
it must not imply the host natively understands the extension. Plain skills need
no extension. Bind qualified identity to registry source plus skill path, and
permit exact host-owned skill/resource selection through the existing route
source path. Same-name conflicts stay explicit; no implicit package-over-host
precedence. A host-owned override selects a distinct source identity.

### 2. Questions and material

A question requires stable local identity, a natural-language semantic question
or criteria, named branch identities/descriptions and exact next fragment/resource
references. Suggested context/evidence references and bounded semantic material
are optional. One generic answer envelope carries a disposition (`answered`,
`unknown`, `defer`, `no-match`, `conflict`), selected branch IDs, optional bounded
material and optional exact evidence references. No per-question JSON schema,
fact/predicate DSL or exhaustive evidence declaration is required. Unresolved
dispositions remain unresolved rather than falling through to the first branch.

The public submission path is the existing start request/answer transport,
extended for a procedure-local question. It must not impersonate the existing
owner question by manufacturing an action/request envelope. Rich answer material
may be shown to a later fragment or supplied as requested data to a current owner
request; the owner validates it independently. No shell interpolation, action
body construction, authority labels or arbitrary callbacks in the control form.

### 3. Custody and currentness

Source text belongs to the skill owner. Semantic answers/material live in explicit
bounded caller carriage, identified by task, skill instance, question/criteria,
selected source/resource identities and relevant evidence. Carriage is advisory
input and must be revalidated; a digest is not truth or permission. Navigation is
derived from current source plus available answers. Missing semantic material
means re-ask/reconsider, never reconstruction from a cursor or hidden parent chat.

Longer-lived semantic conclusions go through existing Planning/decision/Memory
owners only when warranted. Do not add a global answer database. Changed relevant
resources/criteria or evidence invalidate the dependent answer and descendants;
unrelated files do not restart the procedure. Source-set changes are dependencies,
not merely changed-file hashes. Confirmed or uncertain effects remain with their
native effect owner even if all procedure carriage is lost.

### 4. Policy and direct use

Optional procedure has no restriction authority. Native start/invoke continues to
compose all binding requirements. A procedure may nominate an existing current
owner request or action reference; only the owner can admit its effect. Conditional
policy must be admitted by the existing instruction/domain owner separately.
Deleting/replacing the skill cannot waive proof, Assignment, review or protection.

### 5. Control and bounded composition

Provide only selected fragment delivery, semantic question/answer, explicit next
references, and current owner-reference composition. Terminal state means method
finished, never task complete. A worklist can yield independent questions together;
current retained answers or owner-returned settled decisions can progress without
another model turn. No semantic expression evaluator, global variables, scheduler
or unrestricted loop.

Owner composition consumes current typed results and exact returned references
by stable public identity, without copied action fields or private JSON pointers.
Effect/traversal bounds and no-progress detection are native implementation safety,
not author-programmed loop, retry or effect controls. Admission and recovery remain
with the owner and its explicit typed continuations; uncertainty never authorizes
replay. C2b supplies the generic public reference seam. Resource/proof adaptations
consume it in M3 rather than becoming generic capability special cases.

### 6. Native integration and inspectability

C1 extends `native_routes` resource admission and `operating` detail delivery;
C2a integrates procedure-local questions, answers and current caller carriage
with the existing request/answer machinery. C2b adds exact current owner-reference
continuation/composition. Reuse `decision_source::relative`,
bounded source reads, current task identity and existing effect invocation.
Resource actions presently use their dedicated consumer shape, so adapting that
owner to the generic exact-reference seam is explicit M3 work, not presumed
reuse. Proof receipt admission likewise needs a typed continuation, not a copied
native_proof_procedure implementation in a skill.

Current detail must show source/instance, fragment/question, purpose, legitimate
alternatives or settled reason, evidence refs, affected method/owner consequence,
dependencies and reentry. It is explanation of source and procedure, not hidden
reasoning. C3 ships every referenced resource through payload ownership and
existing host exposure. Unsafe/missing resources fail at selected scope, discovery
executes nothing, and refresh/removal preserve host edits and effect custody.

## Neutral authoring walkthrough (design example, not executable syntax)

A host skill `change-note` has a small entry pointing to its procedure resource.
The resource asks: "Does the observed change alter behavior visible to a user?
Compare the stated intent with the patch; defer when evidence is insufficient."
Two named branches point to `user-note.md` and `internal-note.md`. An answer may
include a concise impact summary and exact evidence refs without a local schema.
Both branches end by
returning a draft note; neither publishes it.

Normal path: read the question and patch, answer user-visible with the impact
summary, receive only user-note.md, draft the note. Ambiguity: conflict or unknown
returns the competing descriptions and missing-evidence explanation, no guessed
branch. Reentry: retained current answer recovers the selected fragment; lost
answer asks again; changing the criterion cannot reuse the old label. No runtime:
read the same question and selected linked Markdown manually. A later native
publication step would remain unavailable, not be simulated.

A human edits one natural-language condition or destination reference without
native code. JSON punctuation and reference upkeep
are real authoring costs. Compare with a fairly factored ordinary skill, not a
full tree forced into SKILL.md. This walkthrough establishes design intelligibility
only; actual host activation, execution and benefit remain C3/#3411 evidence.

## Proposed stacked work units and proof boundaries

| Unit | Dependency and complete PR outcome | Required present evidence |
| --- | --- | --- |
| C1 / #3446 under #3410 | Reconciled #3409 shaping per external reply; passive source/resource form, qualified identity, validation and inspectable selected detail | Plain skill unaffected; missing/unsafe resource and collision; lazy branch delivery; source drift |
| C2a / #3447 under #3410 | C1; semantic question/answer carriage and currentness only | Cross-task/instance and stale answers; lost material; unresolved/conflict; supplied-answer protocol proof does not establish model judgment |
| C2b / #3455 under #3410 | C2a; generic exact current owner-reference continuation/composition | Current public identity; owner validation/authority; missing/ambiguous/no-progress; confirmed/uncertain recovery; one read-only and one existing effect/request case |
| C3 / #3448 under #3410 | C2b; installable bundle lifecycle and supported host vertical path | Installed Python/TypeScript/JSON/native parity where transport differs; host-owned edits, refresh/removal; neutral actual host walkthrough |
| M1 / #3449 under #3411 | C3; startup/intent/reference consolidation | Small full-loaded entry, same manual sources, direct and unavailable path; no binding obligation loss |
| M2 / #3450 under #3411 | C3; configuration/correction/bootstrap procedure migration | Authorized write, deferred/unknown result, receiving-owner consequence and preservation |
| M3 / #3451 under #3411 | C3; resource/proof-specific adaptation consuming C2b, sequence extraction and deletion | Equivalent direct/skill restrictions; typed receipt continuation; no repeated uncertain effect; helpers removed |
| M4 / #3452 under #3411 | Coordination outcome covering M4aÃ¢â‚¬â€œM4d; not an implementation leaf | Complete original Planning/Assignment obligation; all four leaves accepted before coordination closeout |
| M4a / #3456 under #3452 | C3; intake, decompose, tighten, reporting, intent verification and closeout | Planning continuity/custody; intent/claim separation; duplicate deletion; direct/manual parity |
| M4b / #3457 under #3452 | C3; assurance/manual delegation and returned-result procedure | Local/manual/non-local boundaries; Assignment admission and return recovery; no P2 delegation strategy |
| M4c / #3458 under #3452 | C3; review-pass and finding-promotion continuation | Externally initiated findings; Planning-owned continuation only; independent review/claim authority retained |
| M4d / #3459 under #3452 | Accepted M4aÃ¢â‚¬â€œM4c; retire/merge high-assurance lifecycle, orchestrator workflow and autopilot umbrellas | Unique-meaning disposition; duplicate deletion and no resurrection; no replacement workflow taxonomy |
| M5 / #3453 under #3411 | C3; Memory and maintainer reference consolidation | Candidate consequences survive bypass; no-retention and receiving evidence; independent review unchanged |
| #3411 integration | M1Ã¢â‚¬â€œM5 | Audit-subject-to-current-head sweep, package exposure and one bounded final host walkthrough; every M/R row accounted for |
| #3442 / #3443 | Accepted #3408 | Fresh actual public/field inventory; complete remove/merge dispositions, direct operations, neutral modules, generated parity and no resurrection |
| #3404 / #3405 -> #3406 | Accepted #3441 | Final contract references and integrated customization guide validated against actual supported artifact |

These units match the externally shaped GitHub sub-issue graph. The shaping reply
authorizes implementation after artifact reconciliation; independent acceptance
and issue closure remain separate. #3410 cannot close from C1,
and #3411 cannot close from a proving subset. Public/module contraction must use
the post-migration head, not prematurely freeze this proposal. Fresh final RC and
stable admission remain #3277/#2985 after accepted P1.

## Validation, uncertainty and completion cost

This patch adds no product behavior or permanent tests. Source inspection and the
successful native build establish the observed baseline only. Existing frontier,
route, effect, Planning and Memory tests identify reusable proof classes; they
have not been run as proof of this proposed extension. No source-only walkthrough
is counted as model behavior or measured economic benefit.

Independent shaping acceptance remains required for #3409 closure. The external
shaping reply settles the minimum contract and issue boundaries and permits
implementation after this reconciliation. The revised artifacts are ready for
focused recheck; the implementation agent does not self-approve this design or
request a reviewer to approve its own implementation.

Outstanding before #3409 closure: independent acceptance; accepted parent
dispositions; any source-reference or boundary corrections from
that review. No issue, migration lane, P1 outcome or release is claimed complete.
Observed overhead includes owner/assignment preparation, source reads, a failed
bare Python invocation, corrected Windows path queries and bounded request
reentry. Total successful-completion cost and host comparative economics are
unmeasured; they are not zero.

## Artifact end-state

After independent acceptance, retain this audit only as a compact design record
while its dispositions and rationale remain useful. It is not an active workflow
or a substitute for current source/owner facts. Reconcile superseded claims rather
than leaving the proposal as apparent current authority.

The epic Planning record carries the remaining P1 continuation. When it no longer
has continuation value, close, archive or remove it through Planning according to
the current owner lifecycle. Do not leave a completed lane as an active plan or
delete managed state directly merely to clear residue.
