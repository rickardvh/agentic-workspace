# Recheck a changed subject

For recheck, start from the previous blocker or requested change, then inspect only the follow-up delta unless new evidence points wider.

## Trusted executable preparation

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
