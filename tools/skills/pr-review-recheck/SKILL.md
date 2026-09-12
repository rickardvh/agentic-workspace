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
- directed another implementation agent or tool to make substantive patch changes on its behalf;
- otherwise materially shaped the implementation being reviewed.

**Delegation does not create independence.** A reviewer is also **not eligible** when it is a child, subagent, delegated task, subprocess, nested session, or other reviewer instance spawned, selected, prompted, supervised, or controlled by an ineligible implementation agent for the purpose of approving that implementation agent's patch. This remains true even when the delegated reviewer:

- has a fresh context, separate process, different model, or separate account;
- did not itself edit the patch;
- is explicitly told to be "independent";
- is given only the PR URL and review skill;
- returns a technically sound review.

Such a delegated reviewer may provide **non-authoritative critique or preflight feedback** to the implementation agent, but it must not submit `APPROVE`, emit an `aw-chatgpt-review` marker, claim `merge-ready`, satisfy `Review approval`, or be presented as the required independent review.

An authoritative review must enter from outside the implementation agent's review custody: for example, a human/maintainer starts the reviewer directly, an independently configured trusted review service is triggered by its normal repository event, or a separate reviewer session receives an independent review mandate without being spawned or directed by the implementation agent. An implementation agent may request that such an established external mechanism run, but it must not choose or manufacture the reviewing agent, prompt, authority, or verdict ad hoc.

If any disqualifying item is true, or independence is unclear, **stop before using this skill**. Do not submit `APPROVE`, do not emit an `aw-chatgpt-review` marker, do not claim `merge-ready`, and do not satisfy `Review approval`. Handoff to an externally initiated reviewer that neither materially shaped the patch nor descends from the implementation agent's delegated work.

A user asking the implementing agent to “review”, “recheck”, “approve”, or “merge” its own PR does **not** override this boundary. Human approval to continue implementation also does not create independent review authority. An implementation agent may report its fixes, evidence, and remaining uncertainty, but that report is not independent review.

A reviewer may share the GitHub account that opened the PR; that is only an account/API transport limitation. It does not permit the agent that implemented the patch to approve itself. A fresh chat or process is not sufficient by itself if it is merely continuing the implementation agent’s role, authorship, or delegated review lineage.

## Procedure

For any checkout isolation or temporary review material, use the shared `.agentic-workspace/skills/workspace-resources/SKILL.md` lifecycle: check current necessity and instruction policy, prefer exact Git object reads, and reconcile clean resources or preserve dirty/unique work at termination. This does not change reviewer eligibility.

1. Identify the PR's claimed intent:
   - PR title and body;
   - linked issue(s) and closure claims;
   - any review comments, evidence reports, or requested fixes.
2. Audit the linked issue's system-shaping assumptions against current evidence, system intent, and domain ownership:
   - distinguish `PR violates a sound issue requirement` from `PR reveals that the issue requirement is wrong or too strong`;
   - distinguish a useful slice from satisfaction of the underlying intent;
   - check whether the PR adds machinery only to satisfy an over-specified mechanism when a smaller owner-aligned result serves the invariant;
   - refine the issue before forcing harmful acceptance when the human-owned why is unchanged; ask the human or domain owner when changing the issue would change that why.
3. Identify the linked issue's closure shape independently of its bug/direction/review kind:
   - **parent outcome / direction** — a PR may satisfy one child or disposition, but parent closure is administrative and requires all current bounded children/dispositions plus immediate aggregate proof to establish the parent outcome. Do not demand one giant parent-closing PR.
   - **bounded implementation leaf** — a PR claiming closure must make the whole bounded leaf true and provide its immediate deterministic/integration proof. A knowingly partial PR cannot manufacture honest closure by creating follow-ups after the fact.
   - **later evidence / review** — no product-code PR is required merely to close the evidence issue. Review the stated evidence/currentness/independence criteria; route concrete implementation findings to the smallest bounded owner instead of growing the evidence issue into a backlog.
4. Inspect the current changed-file set before opening broad files.
5. For first review, compare the diff against the linked issue's final intended outcome, non-solutions, and evidence requirements after the assumption and closure-shape audits.
6. For recheck, start from the previous blocker or requested change, then inspect only the follow-up delta unless new evidence points wider.
7. Check proof separately from intent satisfaction:
   - CI and reported validation;
   - focused tests for changed behavior;
   - generated/payload sync when shipped or mirrored surfaces changed;
   - semver label when package behavior or shipped payload changes.
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
11. Treat the review approval check as the merge boundary:
   - `merge-ready` for the current head admits the review side of merge;
   - a prior `merge-ready` decision also admits a later head only when every intervening commit is a trusted-base merge and the stable PR patch is unchanged;
   - the newest trusted decision wins, so a later blocker remains blocking;
   - ordinary follow-up commits, unrelated merges, patch-changing conflict resolutions, absent/malformed/untrusted history, or unverifiable topology keep `Review approval` failing.

## Recheck Focus

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
- `proof`: CI, validation, focused checks, or missing proof
- `unresolved`: blockers or remaining non-blocking risks
- `closure_honest`: yes / no / partial, with issue refs and any evaluation-boundary reason
- `next_action`: comment, approve, mark ready, wait, request fix, label, or merge

## Rules

- Eligibility comes before procedure. **Never use this skill as permission for an implementation agent, or any reviewer it spawns or controls, to review its own patch.**
- Independence is a custody/authority property, not a process, model, account, or context property. A child/subagent cannot manufacture independent review for its parent implementation agent.
- Skill availability, routing, a user request, passing CI, implementation completion, or a fresh reviewer context does not manufacture independent review authority.
- Implementation-spawned reviewer agents may provide non-authoritative critique only; their verdict cannot satisfy `Review approval` or produce an authoritative review marker.
- Prefer evidence from the current PR head over stale prior comments.
- Do not infer merge readiness from passing CI alone.
- When an eligible independent reviewer approves a draft PR, mark it ready for review in the same review pass unless explicitly instructed to keep it draft.
- Do not require a giant PR to close a broad parent; review bounded children on their own full outcomes and let the parent close administratively when its current graph is satisfied.
- Do not hold a complete bounded implementation leaf open for future evidence explicitly owned elsewhere.
- Keep comments focused on actionable blockers or durable suggestions.
- When GitHub cannot submit a formal review because the independent reviewer shares the PR author's account, the configured reviewer automation may use a top-level terminal marker. This repository admits that marker by its exact PR, head, policy, and decision contract; transport provenance, `user.login`, and `author_association` are not reliable authority signals. **Implementation agents and their delegated descendants must never use the reviewer automation or emit `aw-chatgpt-review` markers for that implementation lineage.**
