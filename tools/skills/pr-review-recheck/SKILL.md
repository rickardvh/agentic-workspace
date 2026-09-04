---
name: pr-review-recheck
description: Independently review or re-review Agentic Workspace pull requests when the current agent did not implement or modify the PR patch. Use only for external review authority; do not use while addressing feedback, implementing fixes, reporting implementation evidence, or assessing your own changes.
---

# PR Review / Recheck

Use this repo-owned skill only as an independent external reviewer of an Agentic Workspace PR. This is maintainer workflow guidance for this repository only; do not ship it as an installed AW skill.

## Eligibility Boundary

Before using this procedure, establish that the current agent did not implement, modify, or push the PR patch being reviewed.

- An implementation agent addressing review comments may report its fixes and evidence, but must not use this skill, emit an authoritative `merge-ready` marker, or satisfy `Review approval` for its own work.
- A request to address blockers, fix CI, update a PR, or check whether comments were addressed does not assign independent review authority.
- Human approval to continue implementation does not make the implementation agent independent. Route the completed head to a distinct external review agent or leave `Review approval` pending.
- A reviewer may share the GitHub account that opened the PR; that is only an account/API limitation and does not permit the agent that implemented the patch to approve itself.
- If authorship or role separation is unclear, stop before applying this skill and request an independent review.

## Procedure

1. Identify the PR's claimed intent:
   - PR title and body;
   - linked issue(s) and closure claims;
   - any review comments, evidence reports, or requested fixes.
2. Audit the linked issue's system-shaping assumptions against current evidence, system intent, and domain ownership:
   - distinguish `PR violates a sound issue requirement` from `PR reveals that the issue requirement is wrong or too strong`;
   - distinguish a useful slice from satisfaction of the underlying intent;
   - check whether the PR adds machinery only to satisfy an over-specified mechanism when a smaller owner-aligned result serves the invariant;
   - refine the issue before forcing harmful acceptance when the human-owned why is unchanged; ask the human or domain owner when changing the issue would change that why.
3. Inspect the current changed-file set before opening broad files.
4. For first review, compare the diff against the linked issue's final intended outcome, non-solutions, and evidence requirements after the assumption audit.
5. For recheck, start from the previous blocker or requested change, then inspect only the follow-up delta unless new evidence points wider.
6. Check proof separately from intent satisfaction:
   - CI and reported validation;
   - focused tests for changed behavior;
   - generated/payload sync when shipped or mirrored surfaces changed;
   - semver label when package behavior or shipped payload changes.
7. Check closure honesty:
   - what landed;
   - what intent it serves;
   - what remains unresolved;
   - whether the PR may honestly close each linked issue.
8. For PRs that use longitudinal evaluation as part of issue closure, check the split explicitly:
   - deterministic implementation behavior still needs present-tense proof and cannot be deferred into an evaluation;
   - the evaluation must have owner, criteria, evidence sources, report sinks, collection policy, conclusion policy, and a fresh/current admitted result unless the PR only claims definition setup;
   - known defects, failed or stale proof, vague future-evidence text, superseded results, or missing current authority block closure;
   - direct deterministic work should remain directly closable when proof and intent are satisfied; do not add evaluation ceremony where no future-evidence uncertainty exists.
9. Decide the action:
   - approve / ready when intent, proof, CI, labels, and closure all line up;
   - comment with a blocker when the ordinary path would be wrong after merge;
   - comment with non-blocking suggestions only when they should not delay merge;
   - merge only when the user explicitly asks or the current instruction permits it.
10. Treat the review approval check as the merge boundary:
   - `merge-ready` for the current head admits the review side of merge;
   - a prior `merge-ready` decision also admits a later head only when every intervening commit is a trusted-base merge and the stable PR patch is unchanged;
   - the newest trusted decision wins, so a later blocker remains blocking;
   - ordinary follow-up commits, unrelated merges, patch-changing conflict resolutions, absent/malformed/untrusted history, or unverifiable topology keep `Review approval` failing.

## Recheck Focus

When rechecking after a fix, do not repeat the whole original review by default. Verify:

- the specific blocker was removed;
- no stale checked-in state or residue remains;
- tests/evidence were updated if the blocker concerned behavior;
- the PR body, labels, and closure claims still match the new state.

## Assumption Audit Example

If an issue requires every selector to be cheaper than every default projection, but a selector intentionally requests extra enrichment, do not demand caching machinery solely to satisfy that impossible absolute. Recommend refining the issue to require query-shaped dependencies and attributable extra work, then review the PR against that invariant. This challenges the proposed mechanism without silently replacing the human-owned goal of bounded projection cost.

## Blockers

Treat these as blockers unless the human explicitly accepts the risk:

- linked issue would close without final satisfaction being true;
- longitudinal evaluation is used to substitute for unfinished implementation, missing present proof, known defects, vague future evidence, stale/superseded results, or absent current evaluation authority;
- proof is missing, stale, too narrow, or contradicted by the diff;
- checked-in Planning, Memory, payload, or generated state is stale after the claimed closeout;
- package-affecting changes lack exactly one semver label;
- a shipped payload mirror is out of sync with the source surface;
- a draft PR is treated as merge-ready without explicit direction.

## Output

Report in this shape:

- `decision`: approve / ready / comment / block / merge-ready / not-ready
- `what_landed`: concise summary of the actual change
- `intent_served`: which issue or product intent is served
- `proof`: CI, validation, focused checks, or missing proof
- `unresolved`: blockers or remaining non-blocking risks
- `closure_honest`: yes / no / partial, with issue refs and any evaluation-boundary reason
- `next_action`: comment, approve, wait, request fix, label, or merge

## Rules

- Prefer evidence from the current PR head over stale prior comments.
- Do not infer merge readiness from passing CI alone.
- Keep comments focused on actionable blockers or durable suggestions.
- When GitHub cannot submit a formal review because the independent reviewer shares the PR author's account, the configured reviewer automation may use a top-level terminal marker. This repository admits that marker by its exact PR, head, policy, and decision contract; transport provenance, `user.login`, and `author_association` are not reliable authority signals. This does not authorize implementation-agent self-review: implementation sessions must not use the reviewer automation or emit `aw-chatgpt-review` markers for their own patch.
