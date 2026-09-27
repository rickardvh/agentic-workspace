# Public human decisions (#3687)

## Governing rule and current contract

[Governing intent](../../SYSTEM_INTENT.md) limits human escalation to Verification
steps explicitly requiring human judgement and tasks explicitly configured for
human owners. Missing delegation is not a human escalation condition.

The shared compiler requires both `human_context` and `human_eligibility` for a
human decision. The latter names the current owner revision, work identity,
source reference, exact declaration and its digest. It admits only Verification's
`human_judgment_required = true` or Assignment's explicit `owner_kind = "human"`
with a target identity. The native owner reobserves the declaration before
admitting an answer or returned task. Caller prose cannot establish eligibility.
The basis and explanation participate in the exact answer identity and survive
full, compact and carried projections.

## Producer inventory

| Producer | Current resolution |
| --- | --- |
| Configuration, adoption and skill exposure | Exact domain confirmation of the prepared change. |
| Instruction and intent publication | Exact domain confirmation under current source and task authority. |
| Memory disposition and capture | Domain decision; new records identify the acting agent. Historical human records keep their original bytes and provenance. |
| Planning selector transfer | Domain decision bound to the exact existing selector. Historical custody remains readable. |
| Source reconciliation and claim assessment | Domain judgement; no independent review or command proof is implied. |
| Verification current evidence | Domain judgement by default. An explicit current requirement with `human_judgment_required = true` supplies the human exception, which policy delegation cannot waive. |
| Human-owned assignment | A target with `owner_kind = "human"` and `target_id` receives the current task through the existing manual handoff. No automatic process or current-host execution is admitted for that target. A manual agent transport does not qualify. |

`bounded-domain-answer` asks the acting agent for the named judgement under current
task authority. `bounded-human-answer` requires the positive eligibility basis.
`owner-recovery-required` supplies a supported recovery; `owner-resolution-unavailable`
preserves a block without inventing a human permission request. Exact proposal
binding, source protection, custody and independent review requirements remain.

No new permission store, human-owner registry or alternate execution path is
introduced. Configuration and assurance declarations remain with their existing
owners. This document records the contract and evidence, not another policy source.

## Bounded reader evidence

A fresh reader of the old real Configuration request could identify the exact
image-pin write and its authority limit, but could not explain why the replacement
was needed, what it contained, or the operational consequences of deferring.
The reader needed clarification before making an informed recommendation.

A different fresh reader saw only the candidate public request and ordinary task
context. It correctly explained the missing Python project installation, the
repaired image's 25-test preparation result, both options, the retained old
configuration on deferral, and the distinction between preparation and admitted
native proof. It required no clarification to understand the decision and did
not answer the authorisation.

A third fresh reader saw only an unavailable-executor packet. It identified the
missing image, refused to turn the block into a human permission question, and
identified preparing/correcting the executor followed by proof as the recovery.
It noted that the packet lacked a concrete preparation procedure. The returned
recovery now tells the caller to prepare the Linux Docker daemon and declared
immutable image with offline dependencies, then select proof again. Diagnostic
details remain separate from that action.

A further fresh reader received the repaired capability packet alone. It
identified the missing image, the required daemon/image preparation and fresh
proof selection, and the absence of any human authorisation path. It needed no
clarification to understand the result or recovery direction.

After removing the source-assessment approval loop, another fresh reader received
only that public request. It correctly identified the acting agent as the
assessor, found no need for a human answer, and separated publication from
independent review and completion. It needed no clarification about the decision;
checking the underlying assessment still requires the named source material.

These exercises assess comprehension, not implementation review or approval.

For the blocker repair, a fresh reader compared two native compiler outputs
constructed from bounded executor-gap inputs. It distinguished supplied recovery
from unavailable resolution, requested no human answer, preserved the affected
release claim and did not copy recovery from one packet to the other. It noted
that claim-scoped blockers can coexist with an otherwise direct task status;
the explicit `affects` field kept that boundary clear. This exercise used fixture
inputs and made no claim about a live Docker daemon.

Shared contract tests cover missing/forged eligibility, owner/work/declaration
staleness, required context and option alignment. The existing current-evidence
and manual-handoff lifecycles exercise both permitted human exceptions and the
ordinary domain controls. Configuration carriage checks preserve domain decisions
across full, compact and carried consumers. Test execution results are recorded
separately; these cases do not constitute independent review.

The final fresh reader received five actual native fixture packets: ordinary
Configuration, ordinary current evidence, explicitly human Verification,
manually transported agent work and explicitly human-owned work. It assigned each
to the correct actor, did not treat manual transport or repository source ownership
as human authority, and preserved deferral, proof and review limits. It correctly
required the cited evidence before judging the assessments and noted that an
actual task recipient still needs a delivery arrangement. It did not execute a
fixture request, inspect implementation or approve a PR.

Validation reused the existing public owner lifecycles. The changed paths passed
174 public cases; one file-symlink case was skipped because the host cannot create
that link, with directory junction coverage retained. Nine final focused cases
covered eligibility, stale declarations, non-waivable human judgement, domain
Configuration and both task-owner types. The Rust suite passed 180 cases with
three subprocess-only fixtures ignored. Only the native human-assignment case is
added to the existing adapter matrix; owner semantics do not need four copies.

Hosted checks, current source reconciliation and external independent review
remain separate requirements. This inventory does not close parent #3665.
