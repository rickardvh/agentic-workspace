# Priority 3: currentness and resource lifetime

This lane under #3207 covers #2981, #2661, #2606, #3220 and #3221. The native core remains the deterministic owner; instructions supply policy and the routed resource skill supplies procedure. No session, cache, worktree or dependency registry was added.

## Reuse and currentness boundaries

| Material | Lifetime and current check | Work avoided / invalidation |
| --- | --- | --- |
| Immutable source input schema | One parsed checked-in schema per native process; no mutable inputs retained | Ten former parse sites share one value; validation still runs on every input |
| Compiled JSON validators | Existing bounded exact-schema cache; current inputs always validated | Compilation reused; changed schema misses and changed data cannot inherit a validation |
| Source reconciliation judgment | Existing Verification receipt; exact work, current scoped postimages, declarations, source/discovery identity, policy, capability and producer implementation | Fresh consumers validate a retained judgment instead of asking for it again; opaque new relevant files and producer changes invalidate it |
| Positive/negative semantic route judgment | Same-work caller carriage; current declared registry set and work identity | A current selected/none answer needs no repeated agent selection; a newly appearing registry invalidates the negative conclusion without an event log |
| Selected proof execution | Existing source/runtime/producer-bound immutable proof receipt | Fresh adapters reuse the exact command result without rerunning it; material source or native producer drift invalidates reuse |
| Planning / Assignment / Memory | Their existing distinct owner identities and bindings | Route, evidence, actor, configuration and advisory lifetimes stay separate; current Workspace answers are composed afresh |
| Already delivered source prose | Optional bounded caller-held `delivery_refs`, bound to work, producing implementation and exact current source row | Compact views omit unchanged large prose after current owner resolution; scope, restrictions, requests, actions and claims remain present |

No rendered operating answer, proof success, mutable source observation or whole owner contribution is cached. Tiny source prose (256 bytes or less) is redelivered because its token is not cheaper. Lost, forged, changed-work or changed-source delivery carriage causes redelivery, never semantic acknowledgment. Full source reads and effect barriers remain current even when the caller holds delivery refs.

The repeatable immutable-schema microbenchmark reduced 20 parses to one: a local debug run measured 19,235 microseconds versus 804 microseconds, including the initial shared parse. This is a component measurement, not a claimed whole-task speedup. The four-surface source-delivery fixture measured 7,510 versus 5,305 model-visible serialized bytes (29% less) with no compensating detail call or added roundtrip. Existing proof counter fixtures establish one execution across fresh consumers, and dependent source changes reject the old action. These are distinct savings; validation is not evidence reproduction.

## Shared resource lifecycle

The routed `workspace/resources/lifecycle` skill is shipped through the ordinary manifest and main skill. Its `resources` tool has native CLI, JSON, Python and TypeScript bindings. Query first, then execute the exact returned action with the same context. JSON/Python/TypeScript pass the complete action context. Native CLI passes its returned target/task/changed context as flags and its exact `request` object to `--input`; it does not reconstruct expected revisions.

`audit` classifies the shallow local namespace from the existing ownership ledger and preserves unknown residue. Scratch operations touch one recognized container below `local/scratch`; creation is exclusive, deletion checks exact current contents and current owner references, and retention requires an explicit reason/disposition. Build caches remain build-tool-owned. Unknown, linked, oversized, retained or changed material is preserved.

Worktree creation requires a concrete isolation need plus judgment over the current instruction consequence. Machine-local `.agentic-workspace/local/instructions/*.md` and checked-in `.agentic-workspace/instructions/*.md` sources use the same instruction parser, discovery and applicability owner. Their source scopes are explicit; local files do not inherit Git-snapshot admission for executable checks. Neither source directory overrides the other. Worktrees are external resources. Git owns registrations; selected-registration metadata supports interrupted unlock recovery, without a second inventory. Clean terminal work removes the exact checkout and registration. Dirty, untracked, unknown ignored, unique-commit or unowned state blocks teardown. Empty tool-output roots explicitly reserved at creation (`target`, `.pytest_cache`, `.venv`) are disposable under their registration lease. The returned build environment routes Cargo/Python/uv output there. Cleanup removes leased output while preserving unleased ignored material, including familiar tool directory names. Missing-directory recovery checks unique commits before removing the exact supported registration. Main HEAD/index, `core.bare` and `core.worktree` are preserved.

The resource owner uses shared invocation admission, operation-result validation and bounded process execution; resource recovery reobserves Git/filesystem state instead of replaying an uncertain mutation. This does not claim the generic irreversible-effect crash guarantees owned by #3000. Review eligibility, proof and task completion authority are unchanged.

Preview verification now reads exact tagged Git objects and requires no isolated checkout. Preview normalization uses the same resource API and always attempts terminal reconciliation; failed or dirty results are preserved with their exact recovery path. Agent implementation and review procedures select the same shipped lifecycle.

## Evidence

- `tests/test_priority3_resources.py`: real native/JSON/Python/TypeScript delivery, negative route reuse and opaque discovery; scratch reentry/retention/owner protection; composed checked-in and real machine-local policy discovery/currentness, necessary isolation, Windows default path, clean teardown, dirty and unique-commit preservation, interrupted unlock, stale registration, main Git integrity, and the preview creation consumer. Real Cargo builds, pytest and virtual-environment creation verify leased output teardown; unknown ignored and unleased tool output remain protected, and tracked output roots cannot be leased.
- `tests/test_native_source_reconciliation.py`: retained positive judgments, source-set negatives, scope coverage, forged/changed sources, independent owner custody and fresh-process repair.
- `tests/test_native_independent_owner.py`: independently linked read-only/effectful modules without core owner-name branches, multiple ready actions, incompatible/revoked/removed modules, configuration repair, foreign authority/state negatives, owner-attributed publication and 80 irrelevant admissions with bounded compact output.
- `tests/test_native_operating_carriage.py`, `tests/test_native_proof_producer.py`, `tests/test_native_former_routes.py`: fresh current continuation, exact effect carriage, proof reuse and producer/source drift, explicit retained route adoption and bounded registry discovery.
- `tests/test_skills_first_interface.py`: shipped procedure derivation and lifecycle, fresh semantic route selection and unaffected constituent preservation.
- Rust workspace tests, Clippy, Python lint and type checks cover implementation and transport contracts. The merge guard includes bounded Priority 3 journeys; platform/release evidence retains its existing gates.

Blocking-review follow-up validation: 68 tests passed across the Priority 3 resource, source reconciliation and preview suites (one release-artifact-only fixture excluded). Full lint/type checks and generated-file checks passed. Shared local discovery does not claim completion of the wider instruction authoring/retention work in #2638.

Independent review must enter externally. The implementation PR remains a draft and does not itself establish reviewer acceptance or close the larger #3207 outcome.
