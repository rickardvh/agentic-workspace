# Final reconstruction implementation frontier

P0 implementation disposition for #3249, observed 2026-09-14 in PR #3252
against integrated `12105291f3d87abb12a4de0a2e5a7fcc2fd9a1c3`.
This is implementation-owned evidence for independent review. It does not freeze
P1, independently accept this PR, or close the coordination parents.

## Accepted substrate and post-C54 audit

The source baseline is C54 `08a4e0e20c246b59ca3eb7987ab73f1b90a92ad9`.
#3208 records the accepted immutable preview, aggregate run 34824210173 and
publisher/public-byte run 34826351874. That preview remains historical evidence.

The accepted post-C54 substrate is #3248 plus #3251. Together they establish
#3246's pinned compiler/components and provenance, inherited unsafe-code
prohibition, default Clippy with warnings denied, locked builds and one pinned
cargo-deny advisory/license/source gate in security and publication. The narrow
RSA public-key-only exception remains explicit in `deny.toml`. Source archives
carry the same policy and runner. Existing actual Windows and Linux substrate
proof is reused for those unchanged mechanisms; published platform support still
requires the selected artifact's actual-host admission. No lower MSRV is implied.
See `rust-toolchain.md` for the deliberate deferral of nextest, coverage, caches,
rustdoc strictness and profile tuning. This reconciliation records the accepted
#3248/#3251 outcome; it is not a new review of those changes.

PR #3252 supplies the remaining #3224/#2613/#2767 corrections and #3250 lived-in
convergence below. Its new product behavior needs independent acceptance.

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
| Release blocker: implementation/substrate | #3246 | Accepted #3248/#3251 core result reconciled above; optional tools remain deferred. |
| Release blocker: P0 lived-in convergence | #3250 | PR #3252 supplies current-surface corrections and actual-checkout convergence evidence below; independent acceptance remains required before freeze. |
| Release blocker: bounded current-surface corrections | #3224, #2613, #2767 | The 2026-09-14 owner amendments supply concrete counterevidence to the earlier candidate-complete classification. Correct managed procedure/defaults, disposition config by lifetime, and support owner-preserving convergence only as needed by #3250; the broad parents do not become wholesale release gates. |
| Release blocker: exact-candidate evidence | #3020, #3059, #2909, #3077 | C54 disposition exists; refresh only changed claims and required exact-subject proof in P1. No known additional implementation is inferred from open state. |
| Release blocker: admission/public truth/cutover | #2990, #2616, #3014, #2983, #3249 | P2-P4 completion rules still apply. This PR cannot freeze/admit/promote the candidate or close these parents. |
| Open parent outcome: skills-first interface | #3223 | Administrative completion still requires independent satisfaction of its bounded children/amended owners and disposition of competing generic procedure surfaces. Its current stable-critical implementation dependency is the bounded #3224 correction, followed by exact-candidate/aggregate evidence under #2909. This does not make the broad parent a wholesale release gate. |
| Candidate-complete / awaiting administrative closure: interface and control | #3218, #3217, #2989, #2987, #2986, #2985, #2981, #2930, #2638, #2606, #2334 | Accepted C53 foundations plus C54 owner/aggregate outcome. Keep currentness, proof, independent-owner and explicit unavailable-operation boundaries. |
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

## Source and lifetime disposition

| Surface | Disposition and current owner |
| --- | --- |
| Config schema, module selection, invocation, artifact posture and latitude | Retain durable repository/environment choices; config is repository-owned policy. |
| Assurance level/escalation/closeout and instruction/decision admissions | Retain owner policy and exact existing archive revisions; do not advance trust from HEAD. |
| System-intent source selection | Retain repository intent; the native owner derives current observations. |
| Payload target/capability/required-before-work | Retain target admission policy; derive byte currentness from the selected artifact and actual files. |
| Compatibility advisory defaults | Retire old reader/resource preferences; current contracts derive capability, not a copied compatibility registry. |
| Module update URLs/cadence | Retire obsolete master/git update machinery; installation identity comes from the selected immutable artifact, without automatic dependency movement. |
| Workflow obligations | Transfer still-useful required/recommended repository expectations to AGENTS.md with the same force. Retire command recipes and generic procedural duplication. |
| Empty test-data policy | Retire inert empty representation; it carried no constraint. |
| Jumpstart/config/findings manuals and system-intent WORKFLOW | Replace competing procedure with narrow references to the canonical skill/current owner. Historical setup findings are not current admission. |
| No-CLI script/policy | Compatibility pointer only, exit 1, runtime facts unknown and authority none; no synthetic decision packet or module discovery. |
| Package copies/read profile | Derive through the existing interface generator and artifact roster. Correct reference closure against actual installed files. |
| Planning/Memory roots | Preserve repository-owned domain state. Package-file removal never owns the whole domain tree. |
| Human config/instructions and promoted output | Remain repository-owned; no package-wide overwrite or reset. |

The fix changes canonical sources and their existing generator, so another source
refresh does not recreate the removed policy/manuals. The installed command guard
checks every declared shipped file against the current native CLI contract.

## Native convergence and preservation evidence

The existing Configuration writer now offers lazy payload discovery and exact
per-file proposals from the selected native artifact. It reuses its source-bound
human decision, admission, confinement, publication marker and recovery machinery.
There is no new CLI family, lifecycle registry, migration ledger or Python host.
Caller-chosen paths/content are rejected. Package refresh cannot be automatically
delegated through a config-policy grant. A payload mismatch permits its bounded
Configuration repair while still blocking unrelated implementation/claims.

Actual checkout baseline: 1,924 tracked AW/instruction files and 675 existing
non-scratch local files were hash-inventoried before source convergence. No file
was lost. The only 12 tracked changes were AGENTS.md, shared config, ownership,
read profile, three managed reference docs, two fallback pointers, setup skill,
system-intent pointer and provenance. All other tracked owner files and all 675
original local files remained byte-identical. The local config and existing
Planning/Memory/Verification/instruction/decision content were preserved.

After building both native executables from the proposed source, the actual
checkout followed each current Configuration request/authorization/action. The
first native pass refreshed only payload provenance (postimage SHA-256
`5a4e125f8f6f54adc597a0b4e69c7790eb78aca3a78a5cc20dd80d5a1807493c`)
and reported all 20 declared files current. The second pass reported the same
20 current files and made zero writes. Package source corrections had already
been derived by their canonical generator; native convergence proved artifact
byte parity rather than silently copying arbitrary target content. The exact
committed subject and final validation are recorded in PR #3252.

Ignored local state was separately classified through the current Resources
owner. Existing effects, decision-point intent, Planning and Verification proof
receipts retain their structured owners; logs are local runtime material;
scratch remains disposable only through its current resource owner. README,
assignment-runs, conclusions, correction-event artifacts, delegation artifacts,
former-root-scratch, improvement-pressure, locks, mutation-claims and
transport-capabilities were reported as unowned residue and preserved. A bounded
native-source audit found no matching current readers for those historical
names. Their existence confers no current semantic authority or deletion right.
No private contents or hash inventory are promoted into shared state.

One earlier dependency-policy scratch container exceeds the Resources owner's
16 MiB removal bound. Its retained experiments are historical proof material;
cleanup refusal was respected. It neither supplies current domain authority nor
blocks convergence. This does not claim every historical byte was removed.

## Necessary surfaces, removal and proof boundary

Full installed-reference closure passes against the current source and shipped
payload. Required local references resolve; optional absent module/local sources
carry explicit degraded semantics. The existing source-maintenance lifecycle
fixtures cover generated policy/ownership, repeated upgrades and bounded removal;
they are not the installed native convergence proof. Native coverage separately
exercises all 20 payload files, preservation of human/local bytes, refusal of
arbitrary paths/content and stale source, and a no-write second pass. Interruption
after payload publication recovers without rewriting the committed source, using
the same writer as config creation/edit recovery.

Removal classification preserves whole Memory/Planning roots, human config,
local owner state and repository output. Only explicitly declared package files
are replaceable/removable under their own contracts. There is no blanket native
uninstall or arbitrary-target adoption claim. Unknown files are preserved until
an actual owner admits removal; no recursive domain reset is implied.

## P0 handoff

All remaining P0 implementation is in PR #3252. #3223 remains an open parent:
its bounded consolidation dependency needs independent acceptance, and later
aggregate/exact-candidate evidence remains with #2909. The implementation-owned
checks above do not count as review. Independently accept and integrate this PR,
then re-query current PRs and owners for any remaining release-relevant
continuation before selecting the P1 candidate. A concrete failure returns to
#3224/#2613/#2767 as appropriate; #2990 and #3014 do not implement fixes.
