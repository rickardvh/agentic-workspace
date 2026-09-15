# Candidate B publication and reconciliation (#3276)

## Accepted implementation

Candidate A (#3275) and its published `preview-v0.55.0` are the accepted baseline.
The Candidate B leaves are independently accepted and closed:

| Owner | Accepted PR | Reviewed head |
| --- | --- | --- |
| #3262 issue preparation | #3285 | `ae7f09d59` |
| #3261 trusted review preparation | #3287 | `190655958fe8a4612d6df244bc42ebca73091bbd` |
| #3263 passive executable availability | #3288 | `a7ad1736a196f54d863731cb23c43f073983ff4f` |
| #3265 native resource composition | #3289 | `d7f5b315a138a7e7cc9852a78ec2b2b12cbe89cb` |

The final stack is integrated at accepted source
`3fd508feba856354e30fd4afc82930f2e6012c87`. Independent review comments explicitly
clear the follow-up patch/draft-state findings and accept the refreshed dependent
heads. This record consumes those external decisions; it is not self-review.

The [preparation evidence](candidate-b-preparation-evidence.md) retains the owner
proof, subtraction inventory, cost limits, #3059/#2981/#2661 reconciliation and
#2257/#2822 dispositions. Review delta remains `REVIEW_ONLY`; no cache, generic
delta, runtime/session owner or new effect/proof authority was introduced.

## Immutable preview subject

- Tag: `preview-v0.56.0`.
- Accepted source: `3fd508feba856354e30fd4afc82930f2e6012c87`.
- Release-only artifact commit: `87cf9ea4b2b0e1d6d59152ef707c3900b5b90595`.
- Publisher: [run 34962615722](https://github.com/rickardvh/agentic-workspace/actions/runs/34962615722).
- Public release: [preview-v0.56.0](https://github.com/rickardvh/agentic-workspace/releases/tag/preview-v0.56.0).

The publisher completed successfully. Admission and the three Linux runtime lanes
(Python 3.11/Node 20, Python 3.13/Node 24 and Python 3.14/Node 24) passed, along with
package/install/start, security, provenance and public-byte smoke. Exact npm
artifact conformance passed on Node 20, 24 and 25. The release has 13 assets.
The distribution remains Alpha and the preview is non-support-bearing; no Windows,
macOS or manylinux release support is inferred from these Linux x64 receipts.

After publication, the trusted release helper independently admitted the remote
tag against its Git objects and downloaded/verified the full public asset set:
`published_bytes_complete: true`. The first download transport failed; a fresh
read-only retry succeeded without any publication retry or tag change. Manifest,
package/native identities, coordinated version, receipt inventory and checksums
matched. `gh attestation verify` also verified the downloaded manifest against the
repository's trusted master publisher and run 34962615722. Its SHA-256 is
`976cb4d2c9cc7dc637711140ad1c9fb926130f27f3840c64ed02d12ea28e856b`.
Security readiness belongs to this exact artifact; it does not claim that GitHub's
separately tracked legacy Dependabot alerts were closed.

## Consequential issue-creation dogfood (#2929)

The earlier no-new-issue disposition was accurate during implementation. Actual
preview publication exposed a recurring, bounded maintainer-consumer defect:
commit hooks created unleased `.ruff_cache`, `.uv-cache-root`, package Ruff caches
and `scratch/validation-results` in the normalization worktree. Native resources
correctly preserved them. The release helper then raised from cleanup after tag
push and publisher dispatch, suppressing its structured publication result.

That new evidence justified [#3291](https://github.com/rickardvh/agentic-workspace/issues/3291),
a bounded repo-release-consumer leaf. It does not reopen the accepted native
preservation contract. The current worktree was safely recovered and removed;
future ordinary helper cleanup and truthful result reporting remain #3291's scope.
There is no need to move or republish the immutable Candidate B tag.

Before the first issue-creation mutation, the acting agent selected
`github/issues/create` from the task's need to route the observed defect. Native
selection returned both shaping and creation procedures. Their instructions were
consumed before final shaping/preparation and before the external mutation:

| Selected material | Exact SHA-256 revision |
| --- | --- |
| Shaping skill | `c11dfaa7cd380e4dddfa7d4dc2a3e0fe91e0d8af928cb3c5f6fd2ff3b2fbc2c3` |
| Creation skill | `d62061f3438dc8e06523a4480ed7541dd8c5800b3c71b382a8fcfa6b5b43e5a0` |
| Bug form | `255a1a4cfaa6084ede3a878ebbb68080060e4a4e4cc2472f2daa7f79f915f2d1` |
| Issue helper | `de6f577b31e5d97c7dc8d5ef6a86f860a872bbcb0a5390bb15704e51d2a223ec` |
| Prepared semantic input | `8fdb1e46f544aaae54b3e35ce63d936da8916bc546edf4b08c703dcb22e36fe2` |

Native executable detail reported material current and external runtime unknown,
with no authority effect. The existing repository `uv` environment supplied actual
invocation availability. Current forms were read and current labels obtained with
`gh label list`; no copied route/template data determined content. One malformed
optional source-reference input failed honestly before mutation and was corrected
to the helper's object schema. The prepared result bound current form/helper/input
and two local source files, preserved the bug form's shell rendering, supplied
the `[Bug]:` title prefix and `bug` label, and granted no write authority.

The authorized task included routing actionable dogfood findings; the creation
skill supplied the transport procedure. `gh issue create --body-file` performed
one creation. A fresh `gh issue view` confirmed the intended title, body and label.
The issue's identity and residual scope are explicitly carried here and into the
current Planning continuation; no automatic GitHub ingestion is assumed.

A separate fresh-process control used historical prose containing “create GitHub
issue” and “review” while selecting no semantic route. Native status was current,
routes were empty, and both issue instructions remained inapplicable with empty
guidance/procedure lists. Lexical overlap did not grant applicability or mutation.
This complements the prior real refinement replay recorded in #2929. The real
creation trace is now available for independent evidence review; no new product
route code or permanent test/CI constituent was needed for that evidence.

## Cost, recovery and completion boundaries

The accepted preparation measurements show reduced model-mediated deterministic
work and explicitly separate added hashing/schema/availability work. A moved-head
review recheck now adds one bounded GET; there is no provider-token, statistical
latency or total-operating-cost reduction claim. The live creation required an
input repair; publication required manual cache disposition. Both costs are part
of the observed result, not hidden by successful current-state queries.

The normalization worktree was necessary because release preparation rewrites
tracked package versions. Native policy judgment preceded its creation. After
publication, exact newly-created hook output was preserved in task scratch and
the UV cache cleaned through `uv cache clean`; native composed teardown of the
same worktree returned `committed` with no blockers. The main checkout and
unrelated worktrees were preserved. #3291 owns recurrence prevention.

Candidate B does not close #3260, Candidate C, or #2985's support-bearing/maturity
outcome. Historical source-assurance admissions are not advanced simply because
the accepted source changed. Publication verification is complete. Independent
review of this evidence record remains before administrative closure of #3276
and the real-creation evidence owner #2929. The current Planning continuation
carries these exact external observations and leaves the larger v1 intent open.
