---
name: pr-review-recheck
description: Independently review or re-review Agentic Workspace pull requests. Review-only: never use from the implementation lineage, including a child/subagent spawned or directed by an agent that materially shaped the PR patch.
---

# PR Review / Recheck

Use this repo-owned skill only as an independent external reviewer of an Agentic Workspace PR. This is maintainer workflow guidance for this repository only; do not ship it as an installed AW skill.

This skill defines a procedure for an already-eligible independent reviewer. **Being routed to this skill, finding it in the repository, being asked to review a PR, or being spawned as a reviewer does not grant review authority.**

## Mandatory eligibility gate

Before using any review procedure below, establish that the current reviewer is independent of the PR patch **and independent of the implementation lineage that produced it**.

The current agent/session is **not eligible** if it did any of the following for the PR head or the patch now under review:

- wrote, edited, generated, or deleted code, tests, documentation, configuration, or other patch content;
- pushed, rebased, cherry-picked, merged, conflict-resolved, or otherwise changed the PR head;
- addressed review feedback or CI failures by mutating the patch;
- directed or delegated substantive patch mutation from within implementation custody, on the implementer's behalf;
- otherwise materially shaped the PR patch from within implementation custody.

Issue shaping and ordinary review feedback do not constitute implementation custody. An externally initiated reviewer does not become ineligible merely by defining or refining intent/acceptance criteria before implementation, identifying blockers, requesting fixes, or re-reviewing later revisions, even when the implementation follows that feedback. Independence is lost when the reviewer writes or edits patch content, changes the PR head, acts within the implementation lineage, or directs/delegates substantive patch mutation on the implementer's behalf. Review feedback is not such delegation; taking responsibility for executing the patch change is.

**Delegation does not create independence.** A reviewer is also **not eligible** when it is a child, subagent, delegated task, subprocess, nested session, or other reviewer instance spawned, selected, prompted, supervised, or controlled by an ineligible implementation agent for the purpose of approving that implementation agent's patch. This remains true even when the delegated reviewer:

- has a fresh context, separate process, different model, or separate account;
- did not itself edit the patch;
- is explicitly told to be "independent";
- is given only the PR URL and review skill;
- returns a technically sound review.

Such a delegated reviewer may provide **non-authoritative critique or preflight feedback** to the implementation agent, but it must not submit `APPROVE`, claim `merge-ready`, or be presented as the required independent review.

An authoritative review must enter from outside the implementation agent's review custody: for example, a human/maintainer starts the reviewer directly, an independently configured trusted review service is triggered by its normal repository event, or a separate reviewer session receives an independent review mandate without being spawned or directed by the implementation agent. An implementation agent may request that such an established external mechanism run, but it must not choose or manufacture the reviewing agent, prompt, authority, or verdict ad hoc.

If any disqualifying item is true, or independence is unclear, **stop before using this skill**. Do not submit `APPROVE`, do not claim `merge-ready`. Handoff to an externally initiated reviewer that neither materially shaped the patch nor descends from the implementation agent's delegated work.

A user asking the implementing agent to “review”, “recheck”, “approve”, or “merge” its own PR does **not** override this boundary. Human approval to continue implementation also does not create independent review authority. An implementation agent may report its fixes, evidence, and remaining uncertainty, but that report is not independent review.

A reviewer may share the GitHub account that opened the PR; that is only an account/API transport limitation. It does not permit the agent that implemented the patch to approve itself. A fresh chat or process is not sufficient by itself if it is merely continuing the implementation agent’s role, authorship, or delegated review lineage.

## Procedure

For any checkout isolation or temporary review material, use the shared `.agentic-workspace/skills/workspace-resources/SKILL.md` lifecycle: check current necessity and instruction policy, prefer exact Git object reads, and reconcile clean resources or preserve dirty/unique work at termination. This does not change reviewer eligibility.

1. Prepare current evidence with the trusted helper below, then identify the PR's
   claimed intent from its body, linked issues, closure claims and requested fixes.
   The helper collects facts; it does not interpret those claims or establish
   eligibility, correctness, proof sufficiency or a verdict.
2. Audit the linked issue's system-shaping assumptions against current evidence, system intent, and domain ownership:
   - distinguish `PR violates a sound issue requirement` from `PR reveals that the issue requirement is wrong or too strong`;
   - distinguish a useful slice from satisfaction of the underlying intent;
   - check whether the PR adds machinery only to satisfy an over-specified mechanism when a smaller owner-aligned result serves the invariant;
   - refine the issue before forcing harmful acceptance when the human-owned why is unchanged; ask the human or domain owner when changing the issue would change that why.
3. Identify the linked issue's closure shape independently of its bug/direction/review kind:
   - **parent outcome / direction** — a PR may satisfy one child or disposition, but parent closure is administrative and requires all current bounded children/dispositions plus immediate aggregate proof to establish the parent outcome. Do not demand one giant parent-closing PR.
   - **bounded implementation leaf** — a PR claiming closure must make the whole bounded leaf true and provide its immediate deterministic/integration proof. A knowingly partial PR cannot manufacture honest closure by creating follow-ups after the fact.
   - **later evidence / review** — no product-code PR is required merely to close the evidence issue. Review the stated evidence/currentness/independence criteria; route concrete implementation findings to the smallest bounded owner instead of growing the evidence issue into a backlog.
4. Use the prepared complete changed-file set before opening broad files.
5. For first review, compare the diff against the linked issue's final intended outcome, non-solutions, and evidence requirements after the assumption and closure-shape audits.
6. For recheck, start from the previous blocker or requested change, then inspect only the follow-up delta unless new evidence points wider.
7. Check proof separately from intent satisfaction:
   - Resolve every `owner_currentness` obligation in trusted preparation for this
     PR's exact base and head. When a governing source changes, run its existing
     owner/currentness check at that head and record the owner, check, base, head,
     status (`current`, `stale`, or `unknown`) and evidence reference through
     `--owner-evidence`. Use `--owner-obligations` for additional named owners
     discovered from changed paths or review obligations; each entry supplies
     `owner`, `check`, and `sources`. These are reviewer observations, never
     arbitrary executable commands or a replacement domain interpreter.
   - For independently mergeable stacked PRs, a downstream integration result
     cannot satisfy a lower layer's obligation. Report the stale/unknown PR layer
     separately from any current integration head. Reconcile in the introducing
     layer, then rebase descendants and remove redundant downstream residue.
     Recheck only affected owner-sensitive subjects. An unrelated stack needs no
     all-owner matrix. Missing runtime, source objects, or owner evidence stays
     `unknown` and cannot support merge readiness. Preparation selects System
     Intent sources from the trusted owner's existing source records; it does not
     infer currentness from whether a mirror file appears in the diff.
   - CI and reported validation;
   - focused tests for changed behavior;
   - generated/payload sync when shipped or mirrored surfaces changed;
   - semver label when package behavior or shipped payload changes.
   For behavior, test (including embedded Rust/package cases) or CI changes, read
   `docs/maintainer/testing-strategy.md` and audit the test/CI delta disposition:
   durable claim and lowest sufficient owner/contract; duplicate semantic proof;
   justification for each repeated public surface; durable taxonomy; recurring
   merge-CI burden; and named/bounded failure localization. Inspect the claimed
   lower-level replacement before accepting deletion of high-risk evidence. Use
   the strategy's controlled block/accept examples to distinguish duplication
   from a distinct transport or high-risk composition claim. Do not run broad
   suites merely to audit their necessity. Any broad validation must have a
   visible current-claim escalation reason through the existing proof owner.
   Distinguish evidence design, current patch validation and permanent retention:
   ask whether a new permanent case should exist at all, what distinct durable
   failure it catches, and whether existing stable owner evidence already covers
   it. An incident reproduction or a passing new regression is not retention
   justification. Audit the bounded stop/escalate argument: evidence contribution
   and limits, mandatory floors, and the named residual risk (if any). Do not
   demand unspecified broader suites once the bounded claim is sufficiently
   proven; do not accept a stopping argument that skips binding proof. Proof of
   governance machinery is not proof that an unrelated patch applied the strategy.
8. Check closure honesty:
   - what landed;
   - what intent it serves;
   - what remains unresolved;
   - whether the PR may honestly close each linked issue under that issue's closure shape;
   - whether later evidence explicitly owned elsewhere is being incorrectly used to keep an otherwise-complete bounded implementation leaf open.
9. For PRs that use longitudinal evaluation as part of issue closure, check the split explicitly:
   - deterministic implementation behavior still needs present-tense proof and cannot be deferred into an evaluation;
   - the evaluation must have owner, criteria, evidence sources, report sinks, collection policy, conclusion policy, and a fresh/current admitted result unless the PR only claims definition setup;
   - known defects, failed or stale proof, vague future-evidence text, superseded results, or missing current authority block closure;
   - direct deterministic work should remain directly closable when proof and intent are satisfied; do not add evaluation ceremony where no future-evidence uncertainty exists;
   - when longitudinal evidence is explicitly owned by a separate later-evidence issue, absence of that future observation is not a blocker for a bounded implementation leaf whose present behavior and proof are complete.
10. Decide the action:
   - approve / ready when intent, proof, CI, labels, and closure all line up;
   - if an eligible independent review approves a PR that is still draft, mark it **ready for review as part of the approval action** unless the user has explicitly required it to remain draft; do not leave an approved PR draft by default;
   - comment with a blocker when the ordinary path would be wrong after merge;
   - comment with non-blocking suggestions only when they should not delay merge;
   - merge only when the user explicitly asks or the current instruction permits it.
## Recheck Focus

### Trusted executable preparation

After the eligibility gate, select the exact full commit SHA of a trusted
reviewer/repository baseline. Read this skill from that baseline. Never run the
PR head's helper or use its modified skill as trusted review procedure. In a
checkout containing the trusted Git objects, invoke the helper through this
Git-object loader (replace the baseline, repository and PR arguments):

The selected `github/pr/review` route/procedure detail reports the same optional
executable material identity used by other skills. Consume it when available in
the trusted baseline checkout; current worktree material is not admission of
trusted review tooling. Missing material blocks that executable path. Passive
discovery leaves external Python/`gh` runtime availability unknown; establish it
in the explicit trusted invocation environment or use the manual fallback.

```text
python -I -c "import subprocess,sys; s=subprocess.check_output(['git','show',sys.argv[1]+':tools/skills/pr-review-recheck/prepare.py']); exec(compile(s,'trusted-review-preparation','exec'),{'__name__':'__main__','TRUSTED_HELPER_BYTES':s})" <trusted-full-commit-sha> --repo <owner/repo> --pr <number> --eligibility independent
```

Use an available trusted Python interpreter; this standard-library maintainer aid
adds no shipped Python dependency. `-I` excludes working-directory modules from
imports. The loader reads exact baseline bytes without checking out or importing
PR-head code. The `independent` argument records the reviewer's already-established
eligibility assertion; the helper cannot establish custody from an account or
process. Preparation performs only local Git object reads and GitHub GET requests
through the available `gh` transport.

The packet contains exact base/head/repository identities, complete paginated
files, current draft/merged state, linked issue references and observations, reviews/comments, CI/status and
trusted guidance identities. Scoped `AGENTS.md` references follow changed-path
ancestry; semantic applicability beyond those relationships remains reviewer work.
Read guidance through its exact baseline/path, not the current worktree.
Observations cover the reported collection interval, not an atomic snapshot or
ongoing external-state admission. A changed head/base or `stale` packet requires
fresh preparation. `partial`/`unavailable` observations cannot mean no blockers.

For a recheck, retain the prior packet with an `obligations` list containing the
reviewer's unresolved blockers and pass `--previous <prior-packet.json>`. The helper
reobserves current evidence and reports changed/added/removed evidence and file
identities. For a usable exact prior head, `evidence.followup_patch` also carries
the prior-head to current-head text patches from a read-only GitHub comparison;
an unchanged head yields an empty patch without a compare request. The comparison
is bounded to fewer than 300 files and requires the prior head to be the merge
base. Divergent history, transport failure, the file cap, or missing/incomplete
patches (including binary files) report unavailable and make preparation partial;
use an exact tree diff manually in those cases. The final subject observation
also brackets this collection, so a head moving during comparison makes the
packet stale. Missing draft/merged fields are explicitly unavailable.
Unchanged observations carry their exact prior identity rather than
retransmitting their bodies; omit `--previous` to retrieve the full fresh content
if the earlier evidence is no longer available. Prior obligations are preserved without machine resolution; use the
delta to focus semantic inspection. Comparison is `REVIEW_ONLY`, with no product
delta API, cache or session owner. Lost or unusable comparison falls back to full
preparation. Source changes invalidate only their dependent evidence; unrelated
repository files are not blanket invalidators. Select a new trusted baseline when
the governing accepted procedure changes; the subject cannot promote itself into
trusted tooling.

If Python, `gh`, trusted objects or remote evidence are unavailable, report the
exact gap and use the manual procedure: read PR identity/body, enumerate all file
pages, collect linked issue/review/comment/CI observations, and read the trusted
review/testing/ancestor guidance. Preserve unavailable evidence explicitly. Do
not execute subject tooling to repair preparation or infer review authority from
a successful helper exit.

When rechecking after a fix, do not repeat the whole original review by default. Verify:

- the specific blocker was removed;
- no stale checked-in state or residue remains;
- tests/evidence were updated if the blocker concerned behavior;
- the PR body, labels, and closure claims still match the new state and closure shape.

## Closure-Shape Examples

- A delegation parent may remain open after a correct worker-entry leaf merges; review that leaf against its whole bounded worker-entry outcome rather than demanding provider replacement or later real-provider economics in the same PR.
- A bounded adaptation leaf with current authority/application/currentness fixtures may close while a separate later-evidence issue continues to observe repository-lifetime payoff. Do not convert the leaf into a months-long evidence queue.

## Assumption Audit Example

If an issue requires every selector to be cheaper than every default projection, but a selector intentionally requests extra enrichment, do not demand caching machinery solely to satisfy that impossible absolute. Recommend refining the issue to require query-shaped dependencies and attributable extra work, then review the PR against that invariant. This challenges the proposed mechanism without silently replacing the human-owned goal of bounded projection cost.

## Blockers

Treat these as blockers unless the human explicitly accepts the underlying product risk; the independent-review eligibility boundary itself is not waivable by the implementing agent:

- the current reviewer materially shaped the PR patch, descends from the implementation agent's delegated review lineage, or its independence is unclear;
- a bounded implementation leaf would close without its whole stated outcome and immediate proof being true;
- a knowingly partial implementation uses after-the-fact follow-ups to evade the original bounded leaf outcome rather than a genuine transparent reshaping;
- a parent is claimed complete from one useful child/slice while current containing intent remains unresolved;
- a later-evidence issue is being used as an implementation backlog instead of routing a concrete defect to a bounded owner;
- longitudinal evaluation is used to substitute for unfinished implementation, missing present proof, known defects, vague future evidence, stale/superseded results, or absent current evaluation authority;
- proof is missing, stale, too narrow, or contradicted by the diff;
- a material test/CI delta lacks its testing-strategy disposition or retains duplicate semantic proof, implementation-shaped residue, unjustified public-surface repetition, temporary batch taxonomy, opaque unbounded constituents, or recurring cost unsupported by a distinct durable merge claim;
- incident-driven permanent regression growth lacks a missing durable failure class, or the proof argument lacks a defensible bounded stop/escalate rationale;
- checked-in Planning, Memory, payload, or generated state is stale after the claimed closeout;
- package-affecting changes lack exactly one semver label;
- a shipped payload mirror is out of sync with the source surface;
- an independently approved draft PR is left draft without an explicit hold reason.

## Output

Report in this shape:

- `decision`: approve / ready / comment / block / merge-ready / not-ready
- `closure_shape`: parent outcome / bounded implementation leaf / later evidence / other
- `what_landed`: concise summary of the actual change
- `intent_served`: which issue or product intent is served
- `proof`: CI, validation, focused checks, or missing proof; for test/CI changes, include the testing-strategy disposition and any violation or justified exception
- `unresolved`: blockers or remaining non-blocking risks
- `closure_honest`: yes / no / partial, with issue refs and any evaluation-boundary reason
- `next_action`: comment, approve, mark ready, wait, request fix, label, or merge

## Rules

- Eligibility comes before procedure. **Never use this skill as permission for an implementation agent, or any reviewer it spawns or controls, to review its own patch.**
- Independence is a custody/authority property, not a process, model, account, or context property. A child/subagent cannot manufacture independent review for its parent implementation agent.
- Skill availability, routing, a user request, passing CI, implementation completion, or a fresh reviewer context does not manufacture independent review authority.
- Implementation-spawned reviewer agents may provide non-authoritative critique only; their verdict is not independent approval.
- Prefer evidence from the current PR head over stale prior comments.
- Do not infer merge readiness from passing CI alone.
- When an eligible independent reviewer approves a draft PR, mark it ready for review in the same review pass unless explicitly instructed to keep it draft.
- Do not require a giant PR to close a broad parent; review bounded children on their own full outcomes and let the parent close administratively when its current graph is satisfied.
- Do not hold a complete bounded implementation leaf open for future evidence explicitly owned elsewhere.
- Keep comments focused on actionable blockers or durable suggestions.
- When an independent reviewer shares the PR author's GitHub account and cannot submit a formal review, report the review as an ordinary PR comment identifying the reviewed head. No custom marker, App provenance or check publication is required.
