# Planning record proof-route replay — 2026-08-31

This is the maintained closure replay for #2280 and #2900 on PR #2902. Measurements were taken on Windows, Python 3.13, from head `530303f1c` plus the review-repair working tree. Commands ran serially and all exited 0.

## Selected-read regression fixtures

Each selector ran five times in a fresh Python subprocess against both empty history and 1,000 closeout records with forced projection refresh. The regression asserts no fallback profile, no historical source load, and omission of archive, finished-work, review-history, and unrelated-backlog builders.

| Selector | Empty-history median | 1,000-history median | Ratio | Maximum output |
| --- | ---: | ---: | ---: | ---: |
| `execution_readiness,planning_revision` | 0.653455 s | 0.685192 s | 1.048568 | 11,402 bytes |
| `continuation_view,execution_readiness,planning_revision` | 0.655893 s | 0.663481 s | 1.011569 | 18,529 bytes |

Both stay below the maintained 2-second clean-process budget and below the 20% history-inflation ceiling.

## PR #2898 four-record route replay

The original run selected seven commands, including `make check-planning-nosync` and the 517-test reconciliation command, and took 676.866 seconds. The repaired public `implement` and `proof` surfaces now expose the same route identity and same five executable commands. The route is `focused`, reason `focused-route-sufficient`, with focused lane `domain:planning_record_surfaces`; the coverage audit has no missing path or maintenance gap.

| Current command | Wall time |
| --- | ---: |
| Workspace summary | 1.216 s |
| Workspace Planning doctor | 23.444 s |
| Planning package doctor | 1.673 s |
| Planning surface checker | 1.368 s |
| Integration-proposal guard tests | 10.024 s |
| **Total** | **37.725 s** |

Delta: 7 to 5 commands and 676.866 to 37.725 seconds. The broad reconciliation command and `make check-planning-nosync` are absent.

## Planning/report route replay

The later report fixture previously selected eight commands and took 716.582 and 744.734 seconds in two runs. Its repaired route composes `domain:planning_record_surfaces` with maintenance-role `domain:maintained_review_records`; all three paths are focused-covered without broad escalation.

| Current command | Wall time |
| --- | ---: |
| Workspace summary | 0.900 s |
| Workspace Planning doctor | 0.908 s |
| Maintainer surfaces | 9.221 s |
| Planning package doctor | 1.591 s |
| Planning surface checker | 1.346 s |
| Integration-proposal guard tests | 11.382 s |
| **Total** | **25.348 s** |

Delta: 8 to 6 commands and 716.582–744.734 to 25.348 seconds. Shared projections were warm for this second replay; the table reports observed wall time rather than extrapolating a cold result.

## Acceptance matrix

- Exact public PR #2898 parity: `test_pr_2898_planning_record_replay_keeps_public_implement_and_proof_routes_identical`.
- Report-only focused composition: `test_report_only_planning_replay_composes_record_and_maintained_review_routes_without_broad_fallback`.
- Planning runtime escalation: `test_repo_planning_runtime_changes_still_escalate_to_runtime_proof`.
- Declared cross-surface escalation and exposed `cross-owner` reason: `test_proof_route_strategy_decision_selects_structured_broad_escalation_for_two_domain_owners`.
- Missing narrow coverage becomes a maintenance gap without broad fallback: `test_proof_changed_selector_reports_missing_focused_route_as_maintenance_gap`.
