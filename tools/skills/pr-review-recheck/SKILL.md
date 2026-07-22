---
name: pr-review-recheck
description: Review, re-review, or assess merge readiness for Agentic Workspace pull requests while preserving intent, proof, closure, CI, and semver boundaries.
---

# PR Review / Recheck

Use this repo-owned skill when reviewing an Agentic Workspace PR, checking a fix after review feedback, or deciding whether a PR is ready to merge. This is maintainer workflow guidance for this repository only; do not ship it as an installed AW skill.

## Procedure

1. Identify the PR's claimed intent:
   - PR title and body;
   - linked issue(s) and closure claims;
   - any review comments, evidence reports, or requested fixes.
2. Inspect the current changed-file set before opening broad files.
3. For first review, compare the diff against the linked issue's final intended outcome, non-solutions, and evidence requirements.
4. For recheck, start from the previous blocker or requested change, then inspect only the follow-up delta unless new evidence points wider.
5. Check proof separately from intent satisfaction:
   - CI and reported validation;
   - focused tests for changed behavior;
   - generated/payload sync when shipped or mirrored surfaces changed;
   - semver label when package behavior or shipped payload changes.
6. Check closure honesty:
   - what landed;
   - what intent it serves;
   - what remains unresolved;
   - whether the PR may honestly close each linked issue.
7. For PRs that use longitudinal evaluation as part of issue closure, check the split explicitly:
   - deterministic implementation behavior still needs present-tense proof and cannot be deferred into an evaluation;
   - the evaluation must have owner, criteria, evidence sources, report sinks, collection policy, conclusion policy, and a fresh/current admitted result unless the PR only claims definition setup;
   - known defects, failed or stale proof, vague future-evidence text, superseded results, or missing current authority block closure;
   - direct deterministic work should remain directly closable when proof and intent are satisfied; do not add evaluation ceremony where no future-evidence uncertainty exists.
8. Decide the action:
   - approve / ready when intent, proof, CI, labels, and closure all line up;
   - comment with a blocker when the ordinary path would be wrong after merge;
   - comment with non-blocking suggestions only when they should not delay merge;
   - merge only when the user explicitly asks or the current instruction permits it.

## Recheck Focus

When rechecking after a fix, do not repeat the whole original review by default. Verify:

- the specific blocker was removed;
- no stale checked-in state or residue remains;
- tests/evidence were updated if the blocker concerned behavior;
- the PR body, labels, and closure claims still match the new state.

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
- If GitHub disallows a formal review action on an own-account PR, post the review as a top-level PR comment instead.
