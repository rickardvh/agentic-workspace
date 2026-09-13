# First-stable safety disposition

This is the Priority 0 implementation and disposition under #3208, based on
accepted C53 `472e94b85d9ec1a8d5e0da0e63d13ee1621eb558`. It covers the currently
retained native surface, not the later delegation, adaptation, or publication
tranches. It is implementation evidence for independent review; it does not
approve its own PR, close #3208, or admit a release candidate.

## Constructible consequence recovery (#3226)

Compact and full output include `consequence_recovery` when blockers exist.
Each entry identifies the owner and exact affected consequence identities, with
current selectors/references to that owner's existing public request material
or already exposed action/decision.
Fetch a returned reference with the same target/task/changed/request context;
the runtime reobserves it before returning detail. Existing owner requests carry
the necessary prerequisite envelopes. A changed task, source, configuration, or
Assignment invalidates the old reference or request.

Several owner prerequisites remain visible together. An owner without an exposed
public route is explicitly `public-owner-route-unavailable`; a consumer must
not invent a request or interpret discovery as permission. The blocker itself
retains its code, source diagnosis, affected effects/claims, and any existing
recovery instruction. `status: direct` still describes task-global status only.

Configuration owns attribution of its residuals. Local target/runtime residuals
route to Assignment, whose existing exact retained-local admission can discharge
the implementation restriction. Remaining delegation and completion restrictions
survive and route to their remaining owner instead of repeating a satisfied
Assignment comparison. This introduces no new Assignment semantics, persistent router, or
module-specific choreography in the canonical skill.

## Candidate preparation and review (#3227, #3236)

The clarified requirement is behavioral: an agent that implemented or materially
changed a PR must not review/approve it or spawn/direct a reviewer to do so.
`AGENTS.md`, delivered on ordinary Codex entry, carries the rule to report
`ready for independent review` and stop after implementation or review fixes.
The external-review skill preserves eligibility while allowing ordinary issue
shaping, review feedback and re-review by an externally initiated reviewer.

The custom Review approval workflow, publisher, dedicated tests, token allowance
and required-status entry are retired. No marker/provenance/check-run contract,
App, relay, watermark or replacement enforcement layer is required. Existing
historical-comment intake remains able to read old reviews; it does not grant
this implementing agent approval authority. No new permanent regression suite
is added for the instruction. Ordinary implementation/re-review replay supplies
the behavioral evidence: encounter missing independent review, report readiness,
and stop without approving or manufacturing a reviewer.

The hook removes Git's `rev-parse --local-env-vars` environment variables from
dependency/validation subprocesses before both fresh and transported validation
runs. Caller Git discovery, staged-path checks, and formatting's `git add` retain
the original environment, including a temporary commit index. Normal sync,
format, lint, type, and path checks remain enabled.

An isolated Windows reproduction identifies the contamination mechanism:
`git init --bare` in a cache directory with an inherited absolute `GIT_DIR`
changes the caller's `core.bare` to true. Supplying an explicit init destination
does not reproduce it. The corrected hook boundary is exercised with cold cache
creation followed by success or failure in ordinary and linked worktrees,
including a long cache path. These fixtures compare exact caller HEAD, index,
alternate index, and shared config bytes. They prove Git-context isolation;
they do not claim to eliminate independent Windows path-length or network failures.

## Retained effects and custody (#3000, #3001)

The current public invocation allowlist in `native_public.rs`, dedicated resource
owner, and explicitly linked independent owners bound this inventory. Operation
declarations, current source authority and exact custody remain prerequisites;
this table supplies none of them.

| Retained family | Commit/retry and ownership boundary | Existing evidence |
| --- | --- | --- |
| Configuration write, recover, defer | Exact authorized source preimage and retained postimage; creation is exclusive; interrupted publication recovers or preserves unknown material. | Native configuration/advisory tests and Rust configuration interruption cases. |
| Instruction write/recover | Exact source/policy/human authority, exclusive absent creation, current preimage before replacement; no path-based acquisition. | Native instruction tests, including protected source and publication interruption. |
| Planning reconcile/create/update/recover | Source-owner admission or explicit transfer precedes replacement; durable attempts and source/currentness distinguish replay, recovery and uncertainty. | Shared-core custody/race cases, native creation/lifetime and Rust process-interruption cases. |
| Memory disposition and Memory/repository decision capture/recover | Bounded current owner authority, captured pre/postimage, exact manifest publication and policy-drift rejection. | Native Memory disposition/capture and Rust interruption cases. |
| Verification process/report and source reconciliation | Attempt precedes launch; unknown completion does not relaunch; committed receipt/index publication is recoverable; evidence does not grant task completion. | Native proof actual interruption/concurrency, shared-core attempt and Rust proof-publication cases. |
| Delegation process and patch integration | Attempt admission and carrier creation precede process execution; uncertain attempts fail closed. Exact terminal custody recovers result publication. Patches bind the captured baseline and preserve concurrent work. | Native delegation/patch journeys and shared-core actual interrupted-process cases. |
| Independently linked owners | Current repository admission, common custody/attempt contract, exact recovery, and responsible-owner admission before cross-owner consequences. | Separate native owner fixture: authority negatives, interrupted carrier recovery and Planning consumption. |
| Scratch/worktree creation and removal | Current policy and exact creation lease/registration; unknown content and unique work are preserved; interrupted teardown reobserves the same resource. | Native resource lifecycle, stale registration, retention, and disposable-output cases. |
| Optional diagnostics | Local non-authoritative capture; exclusive registration and exact publication custody; failures omit diagnostics without changing the operation outcome. | Native diagnostics tests and Rust registration interruption/concurrency cases. |

Fresh-process replay requires the same committed effect identity; different
inputs or unknown records cannot become success. A filesystem lock alone is not
effect knowledge. Diagnostic omission and owner uncertainty are truthful outcomes,
not evidence of successful execution. Later feature tranches must preserve these
same boundaries for any added effect before candidate selection.

## Former authority and removal (#2984)

`workspace.remove-legacy`, automatic name/schema-based adoption, and the old
Python callback/module dispatcher are not supported native product operations.
Their historical issue examples are retired mechanisms, not implementation
requirements to restore. There is no native blanket package-removal/adoption
operation and no prefilled destructive confirmation. Static package path lists
do not grant deletion authority.

Current Configuration residuals stay visible at their source revision until the
relevant owner consumes them or the affected behavior remains blocked. Planning
selection/material without current custody is preserved; `continue-selected`
establishes task relationship, not source transfer. Memory advisory sources and
retained system-intent interpretation remain source observations with explicit
freshness/admission limits. Missing or malformed authority does not become an
empty successful state. These are current owner boundaries, not a continuing
generic migration workflow. Existing native source/custody tests cover valid-
looking unowned content, malformed sources, explicit transfer, and direct quietness.

The checkout's payload roster was repaired with explicit user authorization to
match the declared source manifest. It adds the two installed skills and removes
the retired operating-loop entry; it does not rewrite historical installation
time or claim a new release. The negative payload test now constructs a missing
roster entry explicitly instead of depending on stale checkout metadata.

## Diagnostics retained boundary (#2995)

The sole ordinary capture path remains native `maintainer_logging`. Enablement
and path privacy come from local `config.local.toml` `[session_logging]`;
`AW_SESSION_LOGGING_DISABLE=1` takes precedence and cannot enable capture.
Without opt-in and a bounded logical session identity no diagnostic state is
created. Absolute, repository-relative and redacted path modes affect capture;
session/correlation identities are salted and request material is represented by
bounded metadata rather than raw prompts or owner content.

The retained maintainer analysis/share-safe export helpers can read native
events; they do not restore the retired public `session-log` command family or
become Planning, Memory, Verification, target evidence, or completion inputs.
Native policy/path, disabled-overhead, invalid-source, corrupted/foreign-state,
concurrent-registration and export tests cover this retained boundary. Exact
release-artifact and platform revalidation remains #2990.

## Proof and retention

Reuse the existing native owner, Rust interruption, and shared-core contracts.
Extend the existing Planning/current-Assignment for
the new discovery boundary. Retain one hook test family
for cross-repository Git-context contamination, a distinct failure class missing
from the prior hook checks. No new aggregate suite, recurring CI job, issue-named
test taxonomy, or duplicate per-operation ledger is introduced.

Stop after this inventory's custody/retry risks, changed public projection,
hook isolation, diagnostics disposition, and required maintainer checks pass.
Escalate a concrete failed owner boundary; do not use a broad historical command
suite to resurrect unsupported mechanisms. Independent PR approval and exact
C54 aggregate/public-byte evidence remain separate.

The configured-checkout recovery trace uses eight native calls: initial Planning
question, continuation answer, three exact owner-detail fetches, task requirements,
execution selection, and comparative Assignment. It uses zero full-projection
fetches and ends with zero implementation/task blockers. Before this change the
compact result exposed no owner mapping for those restrictions; full-detail
discovery was necessary. This proves constructibility, not fewer total calls or
universal model-cost improvement. Public owner requests still carry their exact
identity fields; the trace copies those bytes mechanically rather than inventing
envelopes. More complete burden acceptance remains #3059.

Validation on this tranche: the retained-safety selection passed 407 cases;
its two outdated fixture expectations were corrected and passed targeted reruns.
The historical payload negative now constructs its own missing entry, and the
source Node transport rejects implicit binary discovery before succeeding with
the explicit development binary. The final targeted recovery/payload selection
passed nine cases, and Node transport, hook, Review and diagnostics passed 59.
Rust core tests passed 118 cases (three subprocess-only fixtures ignored by the
parent harness), with all five operating tests rerun after the final projection
change. Both native binaries build; maintainer surfaces, lint, type checking,
formatting, structured inventory and absolute-path checks pass.

Two pre-existing historical guards remain failing, as already described in
`reconstruction-conformance.md`: `check_validation_runtime_plan.py` expects the
absent `memory freshness`, `memory freshness strict` and `workspace native command
admission` labels; `check_runtime_implementation_ownership.py` exceeds old Python
file/function ratchets in unchanged files. This tranche does not rewrite old
measurement receipts or claim those guards passed. Independent approval remains outstanding.
