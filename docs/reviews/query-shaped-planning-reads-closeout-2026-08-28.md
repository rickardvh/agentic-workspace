# Query-shaped Planning reads closeout — 2026-08-28

## Conclusion

Issue #2280 is implemented and remains current on `master`. Compact and selected Planning reads resolve only their declared live dependencies; archive, finished-work, review-history, and unrelated external-backlog sources stay off the ordinary path. Historical audit remains available through an explicit paginated route.

The retained canonical closeout is `.agentic-workspace/planning/closeout-evidence/issue-2280-query-shaped-planning-reads.closeout.json`. This review refreshes its acceptance proof before host-side issue closure; it does not add a second Planning authority or cache.

## Acceptance mapping

| Requirement | Current evidence |
| --- | --- |
| Explicit dependency plans; omitted fields not computed | Selected summary output reports `profile_loaded=query-shaped-direct`, its per-field dependency plan, `fallback_profile_loaded=false`, and omitted historical sources. Tests replace broad/history builders with failures to prove they are not invoked. |
| Current owner/routes independent of archives | Selected-owner and workspace-summary tests create 1,000 closeouts, assert `historical_sources_loaded=false`, and complete under the two-second clean-call budget. |
| Default bounded reads and packet | Tiny report exposes only integrity, selection, continuity, external reconciliation, and proof readiness. The quiet default summary packet is enforced at 4 KiB. |
| Historical audit explicit and paginated | Verbose Planning report accepts an audit page size/cursor and returns `loaded_record_count`, `has_more`, and `next_cursor`; ordinary tiny report omits finished-work inspection. |
| History scaling | Seven-sample empty-history versus 1,000-closeout medians are enforced at no more than 20% regression, with a 10 ms noise floor, for both selected-owner resolution and reconciliation preview. |
| Cache correctness and invalidation | Process-local derived-view hits preserve the authoritative payload; owner changes produce a miss and expose exact Planning/state/selection/owner hash provenance. |
| Doctor and reconcile boundedness | Health dimensions report that historical sources were not loaded. Reconcile preview rejects closeout-history traversal and broad summary compilation. |
| Generated and external parity | Generated command-package static proof passes from the same command and operation contracts. |

## Fresh proof

On 2026-08-28, the two exact reopened regression commands were promoted to maintained clean-process fixtures through the normal workspace CLI:

| Exact selector | Empty-history median | 1,000-closeout median | Scale | Max JSON bytes | Actual direct resolvers |
| --- | ---: | ---: | ---: | ---: | --- |
| `summary --select decomposition,planning_surface_health,planning_revision` | ≤2 s enforced | ≤2 s enforced | ≤1.20x enforced | <65,536 enforced | `direct-decomposition`, `tiny-health`, `planning_revision` |
| `summary --select planning_record,execplans,continuation_view,planning_revision` | ≤2 s enforced | ≤2 s enforced | ≤1.20x enforced | <65,536 enforced | `selected-owner-query`, `direct-live-execplans`, `planning_revision` |

Each result reports `profile_loaded=query-shaped-direct`, `fallback_profile_loaded=false`, its exact per-field dependency plan, and `historical_sources_loaded=false`. The fixture contains a two-lane decomposition and two live execplans; direct results are compared with the corresponding broad-summary fields before the broad summary, archive count, finished-work, and ownership/history builders are replaced by fail-fast sentinels. This proves semantic equivalence and actual isolation rather than trusting declared omissions alone. Five fresh processes per history size enforce the two-second median and 20% scaling limit with the existing 10 ms noise floor. After the semantic repair, five clean current-repository calls measured 1.049 s and 1.109 s medians respectively, with 41,137-byte and 27,140-byte responses. The decomposition result is now the current authoritative record projection, not a `not-evaluated` placeholder, and the execplan result includes every current live execplan without loading completed or archived plans.

The prior eight focused regressions still pass: three selected-owner/archive/cache tests, three tiny-report/pagination/reconcile tests, and two workspace packet/current-owner CLI tests. Generated command-package freshness and static proof also passed.

The performance assertions are executable budgets, not prose measurements: any resolver exceeding two seconds or the 1,000-closeout 20% median bound reports the responsible query in the failing assertion.

## Subtraction boundary

The implementation did not retain broad Planning construction behind a smaller serializer. Ordinary selection uses direct resolvers and a non-authoritative revision-keyed cache. Historical evidence is neither deleted nor precomputed at startup; it is reached only by explicit bounded audit detail.
