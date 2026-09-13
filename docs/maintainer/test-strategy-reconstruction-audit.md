# Reconstruction test delta disposition

This bounded audit implements #3232 in PR #3230. It records one test-delta
replacement decision, not a new test registry or proof selector. The policy stays
in [Testing Strategy](testing-strategy.md); current Verification and
workspace-proof-selection still own proof selection. Independent approval is
separately required; this implementation report is not an external review.

## Before and after

Measured on the same Windows checkout, native debug binaries, sequential pytest,
September 13, 2026. Only the affected tranche was selected for the requested
comparison; no full-repository validation was needed for the reduction claim.

| Inventory | Before (`c1f5f1891`) | After |
| --- | --- | --- |
| Temporary resource/currentness batch | `test_priority3_resources.py`: 32 collected cases | Resource, delivery, route, instruction and preview owners; shared semantics run once |
| Temporary control batch | `test_priority4_control.py`: 40 collected cases | Instruction publication, instruction/Verification, config and claim-review owners |
| Affected executable Python cases | 72 | 31, including 3 small resource adapter parity cases and a split of two unrelated claims |
| Focused sequential runtime | 179.00 seconds, 72 passed | 52.15 seconds, 31 passed (71% less) |
| New lower-level replacement | None | One native `operating` delivery-token contract test, passed in under 0.01 seconds |
| Affected ordinary CI Python selection | 72 batch cases plus 11 preview cases | 10 representative cases, no preview suite |

The count reduction comes from removing repeated executions of identical native
semantics, not parallelism, fewer safety assertions, raised budgets, or relocated
broad CI jobs. Byte-identical public wrappers do not justify four copies of every
mutation/recovery journey. The three adapter parity cases compare native CLI,
Python and TypeScript resource proposal output with the JSON core contract; they
perform no writes. Existing operating carriage and installed-consumer conformance
retain the distinct request/action transport and packaging boundaries.

## Semantic ownership and replacement map

Names below identify the old scenario families and their surviving owner. Except
for the explicit lower-level conversions, each family retains its assertions in
one JSON core ingress journey. This is the lowest existing executable boundary
for cross-owner state, fresh-process custody, Git or actual shell composition;
these are not pure parser primitives disguised as root integration.

| Former scenario family | Durable owner / retained proof and removed duplication |
| --- | --- |
| Delivery suppression, forged token, changed work, opaque new instruction | `operating::delivery_tokens_bind_work_and_source_without_discharging_restrictions` owns deterministic token semantics. `test_native_operating_carriage.py::test_delivery_is_not_satisfaction_and_opaque_sources_redeliver` retains one fresh-source discovery/composition journey; duplicate forged-token and changed-task black-box calls removed. |
| Scratch reentry, owner preservation, changed cleanup snapshot | `test_native_resources.py::test_task_scratch_reentry_cleanup_and_owner_preservation`; four copies become one. |
| Necessary isolation, dirty teardown, main Git integrity | `test_native_resources.py::test_worktree_policy_necessity_clean_teardown_and_integrity`; four copies become one. |
| Interrupted unlock, unique commits, stale registration | Resource owner keeps both checked-in and machine-local policy cases: these are distinct authority sources, not adapter repetition. |
| Retention/release, empty interruption, exact container bounds | Resource retention journey retained once. |
| Protected scratch, malformed config, current owner references, malformed custody | Distinct resource negative cases retained once; none is replaced by a happy-path cleanup smoke test. |
| Owned real Cargo/pytest/venv outputs versus unknown ignored material | Resource output-lease journey retains real tools, unlock recovery and unknown-data preservation, once instead of four times. |
| Unleased or tracked tool roots | Resource negative retained; no retroactive cleanup adoption or tracked-source deletion is permitted. |
| Preview creation consumer | Moved into `test_preview_release.py::test_preview_creation_consumer_reuses_native_terminal_lifecycle`; retains failed-normalization evidence and terminal teardown, outside unconditional merge CI. |
| Negative route conclusion and opaque registry appearance | `test_native_former_routes.py::test_negative_route_conclusion_reuses_until_opaque_discovery_changes`, one core journey. |
| Shared/local instruction composition and local loss | `test_native_instruction_write.py::test_real_local_instruction_owner_composes_and_loses_only_local_sources`, one cross-owner journey. |
| Exact correction, forged content, current delivery, drift | Instruction writer retains both canonical scopes because local ignore/untracked and portable checked-in custody differ; removes the adapter multiplier. |
| Instruction publication recovery and foreign postimage | Instruction writer retains interrupted commit recovery, current admission, foreign-source preservation and local ignore gate. Unknown Markdown key repetition is removed: `instruction_source::instruction_current_reader_rejects_invalid_paths_routes_and_unknown_metadata` already proves that parser class and passes. |
| Checked-in guard over local config and instructions | Instruction writer retains both protected write owners once. |
| Portable correction without local custody | Instruction writer retains real fresh Git clone and explicit snapshot admission once. |
| Escaped source versus recovery-reader bound | Instruction writer retains the unique pre-effect oversized-envelope rejection once. |
| Procedure selection and required independent review | Split the former combined scenario: instruction writer owns short skill identity/removal; `test_native_claim_review.py` owns rejection of an unauthenticated substitute for the required reviewer. |
| Local reconciliation, inline check and grant withdrawal | `test_native_instruction_verification.py` retains current native command evidence, separate reconciliation obligation and policy withdrawal once. |
| Checks plus protection, source drift | Same composition owner retains real current evidence releasing only the completion restriction, protected write rejection and restoration on drift, once. |
| Explicit config grant, deferred continuation | Two cases absorbed into `test_native_configuration_write.py`; current policy and fresh-session resume without policy-state pollution each run once. |
| Semantic claim versus process success, stale resulting work | `test_native_claim_review.py` retains exact human judgment, real proof evidence and stale-work rejection once. |
| Claim review with unfinished Planning subject | Claim-review owner retains normalized selected subject and unchanged open plan; no terminal grant. |

No unique failure class was dropped. No temporary priority test file remains.
The audit is bounded to these batches; it does not assert that all historical
root tests elsewhere have optimal ownership.

## Ordinary CI and release boundary

Before, one step ran schema reuse, both whole priority files, and
`test_preview_release.py -k "not built_preview_root_urls"`. A hang in a resource
build or unrelated preview fixture was attributed only to the priority step.

After, `.github/workflows/ci.yml` has independently named 2-3 minute constituents:

- Schema validator reuse: existing Rust selector.
- Delivery identity/discovery: the native token contract and one opaque-source journey.
- Resource transport/custody: 3 small adapter parity cases, one scratch and one worktree journey.
- Instruction publication/check composition: one interrupted recovery and one checks/protect journey.
- Config/review authority: one deferred-choice and one required-reviewer floor case.

Resource transport, scratch, worktree, instruction recovery, check composition,
configuration and review each have their own named step; verbose node output
identifies the active test. The 10-case selection plus the existing CI stage-policy
regression passed locally in 14.26 seconds (11 tests).

These are 10 Python cases and the focused native contracts, selected for distinct
ordinary merge boundaries. The larger owner suites remain available to current
claim-driven focused or exhaustive validation, not attached wholesale to merge
CI. The existing merge-versus-release stage-policy test now guards this boundary.
Preview/stable workflow files, exact-head dispatch admission, artifact proof and
publication gates are unchanged. The moved preview fixture remains discoverable
by the existing preview suite and exhaustive test discovery; it was not deleted
or weakened to save merge runtime.

## Implementation and review enforcement

`workspace-operating.md` now reaches tests, package code, native code and CI,
delivers the current strategy via `read`, and requires the test/CI disposition
before permanent proof is added or presented for approval. It leaves all source
protections and proof owners intact. `pr-review-recheck` now audits that disposition,
lower-level replacements, repetition, durable names, CI cost and failure
localization, with material violations blocking approval.

The strategy's controlled review examples are exercised by inspection: the
four-adapter stale-source addition fails because its semantic owner and parity
already cover the claim and its CI growth has no distinct justification; the
small repeated-CLI-argument/Unicode adapter cases pass the test-delta audit because
they isolate transport boundaries that a core currentness test cannot prove.
Neither outcome purports to grant independent approval to this implementation.
No executable prose classifier, scheduler, policy language, compliance database,
per-test archive or second selection framework was introduced.
