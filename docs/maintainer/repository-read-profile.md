# Repository-only reading and architecture boundaries

The canonical startup skill supports a consumer that can fetch repository files
and tree/blob identities but cannot run AW or a fallback renderer. Its first
optional read is `.agentic-workspace/READING.json`. The profile is generated from
`read` metadata on existing `OWNERSHIP.toml` authority declarations. It contains
no Planning records, Memory notes, evidence inventory, installed capabilities or
task selection. Historical accumulation therefore does not enlarge the profile.

The profile identifies the exact Git blob of its source ledger. A reader uses a
single repository revision, verifies that source identity through its repository
provider, and records the selected files' blob identities and relevant fields.
If the provider lacks immutable identities, currentness remains unverified.
Changed selected dependencies require reconsideration; unrelated file changes
do not invalidate unchanged blobs. Blob identity establishes bytes, not truth,
proof admission or authorization.

The same generated metadata ships in the root package. Installation derives the
profile from the generic host ledger, including its preserved subsystem overlay;
it does not copy this repository's Planning or Memory state. The existing agent
interface generator checks source/payload drift. The serializer only projects
declared metadata at build/install time. It is not called by `start` or `invoke`,
and no no-runtime consumer executes it.

## Selective reading

| Question | Existing owner route and what remains unknown |
| --- | --- |
| Intent and policy | Read the config's intent refs and repository bootstrap. Effective local overrides and provider readiness remain unknown. |
| Planning/shaping | Prefer an explicit owner ref; otherwise use optional `active.execplans.surface` or immediate active-plan filenames. Read intent, scope, proof refs, blockers, next action and continuation from the selected record. Recorded progress is not fresh proof; local active selection/custody remains unknown. |
| Review | Follow relevant scoped instruction metadata and the Verification manifest's exact refs. A check requirement or retained receipt cannot grant new review, issue-close or completion authority. |
| Advisory knowledge | Use the existing Memory manifest to select relevant notes, then read their declared dependencies. Unrelated notes stay unread. Historical `canonical`/`decision` labels do not turn Memory into a governing decision. |
| Procedure | Select relevant declared semantic routes and follow their procedure refs. This supplies procedure, not runtime applicability or mutation admission. |

Absent, malformed, incompatible or stale profiles fall back to directly observed
repository facts and the matching existing ledger entry. Missing owner files
remain missing; consumers do not fabricate an active plan or broaden their scan.
A runtime-capable maintainer restores the generated profile through installation
or reconciles the exact named source. Runtime/local/live external/effect facts
remain unknown. There is no read-only `start`, planner/reviewer controller,
generated task snapshot, return admission or correction retention in this path.

## Evidence and owner graph

`test_skills_first_interface.py` now covers a fetch-only tree consumer following
the shipped profile into selected Planning, instructions, Memory and Verification
sources, with exact blob/dependency drift and unrelated-history controls. The
harness supplies repository blob identities; it does not execute AW on behalf
of the consumer. Semantic selection is explicit fixture judgment, not a product
classifier. This tests available references and boundaries, not a promise that
every external model obeys instructions. Existing install/payload tests cover
host derivation and incompatible/malformed source rejection. The ordinary
four-surface journey remains independent of a damaged static profile.

The architecture remains:

| Responsibility | Current owner |
| --- | --- |
| Deterministic resolution, action/currentness/admission, publication/recovery | Rust core and admitted Rust domain owners |
| Native/Python/TypeScript/JSON ingress and exact carriage | Thin transports over the same core |
| Durable intent, constraints, Planning, Memory and proof sources | Their existing repository/domain owners |
| Procedure and semantic selection | Canonical skill plus agent/human judgment |
| Static read-profile bytes | Mechanical build/install projection of ownership metadata |

The existing wrapper guard (`test_target_bindings_cannot_hide_reducer_semantics`)
and independent-native-owner fixture remain the architecture evidence owners.
Legacy Python source-maintenance code is not a supported ordinary domain runtime;
no fallback is introduced here. P0 safety/effect dispositions, P1 execution and
P2 retained-knowledge implementations retain their own independent acceptance.
This P3 implementation does not approve those PRs or declare #3020/#2983 closed.

The promotion ledger must reflect the actual integrated reconstruction identity
and open stack. Only independent final-owner acceptance can change its delayed
closures. #2929, #3191, #3192 and research P3 remain later evidence unless a
concrete defect is promoted. #2909/#3059 exact-candidate aggregate acceptance,
#2616 final public truth, #3077/#2990 artifact review and #3014 promotion remain
separate gates. An unmerged stack is not C54.
