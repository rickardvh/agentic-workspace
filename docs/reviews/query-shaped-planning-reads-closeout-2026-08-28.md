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

On 2026-08-28, eight focused regression tests passed: three selected-owner/archive/cache tests, three tiny-report/pagination/reconcile tests, and two workspace packet/current-owner CLI tests. Generated command-package freshness and static proof also passed.

The performance assertions are executable budgets, not prose measurements: any resolver exceeding two seconds or the 1,000-closeout 20% median bound reports the responsible query in the failing assertion.

## Subtraction boundary

The implementation did not retain broad Planning construction behind a smaller serializer. Ordinary selection uses direct resolvers and a non-authoritative revision-keyed cache. Historical evidence is neither deleted nor precomputed at startup; it is reached only by explicit bounded audit detail.
