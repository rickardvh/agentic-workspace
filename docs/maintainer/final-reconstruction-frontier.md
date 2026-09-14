# Final reconstruction implementation frontier

P0 disposition for #3249, observed 2026-09-14 against integrated
`b9638adae9aefbf45ce1cd8d719a0c4b125797e5` plus this dependency-policy PR.
This is implementation-owned input for independent review, not candidate
selection, independent acceptance, or permission to close an issue.
Refreshed against the [P0 coordination amendment](https://github.com/rickardvh/agentic-workspace/issues/3249#issuecomment-5662737272)
and #3250: dependency-policy integration alone no longer empties P0.

## Post-C54 change audit

The source baseline is C54 `08a4e0e20c246b59ca3eb7987ab73f1b90a92ad9`, not
the release-normalized P54 commit. [#3208](https://github.com/rickardvh/agentic-workspace/issues/3208)
records independent acceptance of #3238/#3239/#3241/#3242/#3244/#3245, aggregate
run 34824210173 and publisher/public-byte run 34826351874. The immutable preview
remains evidence; it is not the eventual stable subject.

The entire integrated post-C54 delta is #3248: pinned compiler/provenance,
inherited unsafe-code prohibition, and a local-output ignore rule. Its recorded
Windows and fresh Linux builds, Clippy, Rust tests, five native topology cases,
13 npm/source-artifact cases and hosted merge-sufficiency run 34829129036 cover
that bounded substrate. No product-semantic change or second implementation
continuation appears in the integrated log. This audit does not self-review #3248
or replace its accepted independent disposition in #3249.

This PR completes the remaining advisory/license/source mechanism under #3246:
one pinned cargo-deny, full locked workspace, explicit license/source policy,
blocking security and publisher execution, and a documented RSA public-key-only
advisory exception. The existing security receipt fingerprints the Rust inputs
and verifies wiring; scan execution remains the actual checker/job result.
Source archives include the same policy and runner for reproducible checking.

One concrete local preparation defect surfaced: the installed `READING.json`
matched the shipped file byte-for-byte, but was absent from the checked-in
payload provenance roster. Native startup therefore returned
`native-payload-target-unproven`. The user explicitly authorized the roster
repair. Adding the missing entry makes native payload status `satisfied`,
without changing installed bytes, product behavior or admission policy.
The full structured-file audit also found the existing read-profile copies and
Rust toolchain declaration unclassified. Their entries now point to their
existing generator/toolchain owners alongside the new deny policy; this adds no
new validation mechanism or generated product surface.

## Open-issue classification

The refreshed audit inventories all 93 open issues using their completion boundaries,
the current #3208 acceptance/checklist, C53/C54 owner evidence maps and #3138
ledger. Some individual issue
bodies still describe pre-C54 partial slices; the later accepted cumulative
outcome in #3208 is the basis below. Candidate-complete means the accepted
preview outcome under its supported scope; P1 must still bind required evidence
to the final candidate. No row is new independent final-owner acceptance.

| Classification | Issues | Current consequence |
| --- | --- | --- |
| Release blocker: implementation/substrate | #3246 | This PR needs independent acceptance and integration. Then reconcile its combined toolchain/lint/provenance/dependency/platform result. |
| Release blocker: P0 lived-in convergence | #3250 | Current-surface corrections, actual-checkout owner-state preservation, supported convergence and second-pass idempotence must pass before candidate freeze. No convergence proof is claimed by this inventory. |
| Release blocker: bounded current-surface corrections | #3224, #2613, #2767 | The 2026-09-14 owner amendments supply concrete counterevidence to the earlier candidate-complete classification. Correct managed procedure/defaults, disposition config by lifetime, and support owner-preserving convergence only as needed by #3250; the broad parents do not become wholesale release gates. |
| Release blocker: exact-candidate evidence | #3020, #3059, #2909, #3077 | C54 disposition exists; refresh only changed claims and required exact-subject proof in P1. No known additional implementation is inferred from open state. |
| Release blocker: admission/public truth/cutover | #2990, #2616, #3014, #2983, #3249 | P2-P4 completion rules still apply. This PR cannot freeze/admit/promote the candidate or close these parents. |
| Candidate-complete / awaiting administrative closure: interface and control | #3223, #3218, #3217, #2989, #2987, #2986, #2985, #2981, #2930, #2638, #2606, #2334 | Accepted C53 foundations plus C54 owner/aggregate outcome. Keep currentness, proof, independent-owner and explicit unavailable-operation boundaries. |
| Candidate-complete / awaiting administrative closure: safety and maintainer preparation | #3236, #3232, #3227, #3226, #3221, #3220, #3013, #3012, #3001, #3000, #2997, #2995, #2984 | Accepted C53/C54 safety, instruction, resource, source-preservation and test-strategy dispositions; #3138 already lists the independently accepted migration/intent leaves. |
| Candidate-complete / awaiting administrative closure: Planning | #3195, #2970, #2661 | Accepted portable work/lifetime behavior; local custody and exact final-candidate proof remain distinct. |
| Candidate-complete / awaiting administrative closure: Assignment | #3231, #3194, #3193, #2947, #2916, #2818, #2817, #2210, #2209 | C54 accepted supported posture/transport/return/replacement/evidence composition. No universal provider or economic claim. |
| Candidate-complete / awaiting administrative closure: retained knowledge | #3040, #2809, #2726, #2648, #2647, #2570 | C54 accepted Memory/decision/correction/adaptation destinations; no automatic refresh of stale archive authority. |
| Candidate-complete / awaiting administrative closure: bounded owner leaves | #3139, #3140, #3141, #3142, #3143, #3144, #3145, #3146, #3147, #3149, #3150, #3151, #3152, #3153, #3154, #3155, #3156, #3157, #3158, #3159, #3160, #3161, #3162, #3163 | Existing #3138 accepted-leaf ledger; reconcile administrative closure in its owner, not from this table. |
| Later evidence / non-blocking | #3191, #3192, #2929, #2821, #2822, #2823, #2824, #2825, #2826, #2827, #2998 | Longitudinal/provider/research evidence and its independent harness. No new concrete release defect was supplied by these open bodies. |
| Later evidence / non-blocking remainder | #3041 | The bounded real-archive evidence required by #3040 was consumed in C54. Additional archive dogfood/refresh is not an automatic stable implementation gate. |

Explicitly unsupported/retired classes remain within those accepted owner
dispositions: blanket legacy removal/adoption and the former Python lifecycle
runtime; automatic provider transports or private-state guarantees without current
host evidence; runtime/effect/proof authority from a repository-only read; custom
self-approval enforcement; and published Windows/macOS/other-architecture support
without actual-host artifact admission. These are not whole issues falsely marked
retired. The safety, delegation, C53/C54 conformance and Rust-toolchain documents
retain their precise supported boundaries.

## P0 handoff and proof boundary

At audit entry there were no open PRs targeting `reconstruct/first-stable`.
The only open repository PR was draft #3138, from reconstruction to `master`;
it remains a promotion ledger and must not be ordinarily merged. At refresh,
#3251 is the only open PR targeting reconstruction. That PR inventory is not an
empty implementation frontier: #3250 and its bounded upstream corrections remain
P0 work even without another open PR. No candidate is frozen here, and no later
exact-subject gate is declared current.

The amended P0 exit sequence is:

1. Independently accept/integrate the #3246 dependency-policy result and reconcile
   its combined toolchain/lint/provenance/dependency/platform outcome.
2. Under #3224/#2613/#2767, correct the release-relevant managed/default/config
   sources consumed by #3250. Disposition config sections as retain, derive,
   transfer, ask or retire according to their current semantic owner. Cleaning
   installed copies while refresh recreates them is insufficient.
3. For #3250, inventory checked-in installed surfaces by owner/lifetime and
   separately audit ignored local state on the actual checkout. Preserve current
   human/local policy and useful Planning/Memory/Verification/instruction/decision
   state; keep local contents local. Execute the supported current convergence
   path and record its exact source identity and before/after evidence.
4. Repeat that path on the same candidate. Prove no unexplained semantic diff,
   lost owner state, resurrected retired commands/manuals/config obligations, or
   incorrect necessary-surface/removal classification. A clean fixture or one
   successful pass cannot satisfy this gate.
5. Independently accept the bounded owner corrections and lived-in proof, then
   re-query PRs and owners for remaining release-relevant work. Feed the evidence
   to #2909/#2990 before freezing the exact P1 candidate.

Any reusable defect found during dogfood returns to its smallest product owner
and remains P0 until fixed and re-tested. Proof-only gaps on a stable converged
tree can be resolved before P1 freeze without expanding product scope. This is
a temporary batch-exit condition, not a new migration framework or authority.

Focused proof covers the real locked positive scan, separate advisory/license/
source rejection experiments, the runner's version and failure boundary, missing
publisher gates and Rust-input fingerprint changes in the existing security
tests, and source-archive policy inclusion. Existing compiler/native topology
proof is reused for unchanged substrate; broader release-equivalent and actual
platform admission remains P1/P2. The experiments do not add permanent tests of
cargo-deny's own policy engine. Small retained tests protect only AW's runner,
wiring and receipt/source-package contracts.

The earlier provenance finding was repaired in the existing provenance owner with
explicit authorization; no second payload synchronizer or audit stack was added.
That repair does not establish #3250's broader lived-in convergence outcome.
Recurring cost is one Rust scan in security CI plus the same scan at publication;
tool installation is pinned and uncached. Optional nextest, caches, coverage,
rustdoc strictness and profile tuning remain deferred as documented under #3246.
Stop implementation proof once the bounded checks and normal hooks pass; escalate
only a named failed boundary. Independent review is the next step for this
dependency-policy implementation; the amended convergence gate above remains
required before the final no-open-continuation check can permit P0 exit.
