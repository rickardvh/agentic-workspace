# Issue #2722 default analyzer replay

Captured 2026-08-26 from the same ignored Codex logical-session artifact set (more than 100 live-agent commands). Only the sequential measurement/replay commands were appended between captures.

Command: `uv run --frozen --active --no-sync python scripts/run_agentic_workspace.py session-log --target . analyze --origin agent --format json`

| Measurement | Merged master | Repair branch |
| --- | ---: | ---: |
| Head | `f12025f324c71592e5347d01d79c9569fa72f277` | `fec7e9573c2b7a07cea14f7a97e7cbf771d5161c` |
| Wall time | 1235 ms | 1238 ms |
| Result bytes | 81,398 | 14,476 |
| Recursive fields | 1,688 | 277 |

The repair removes 66,922 bytes (82.2%) and 1,411 recursive fields (83.6%). The default shape is now compact counts plus material current findings and exact paged routes for entries, segments, episodes, contexts, and candidates.

`test_session_log_default_analysis_stays_bounded_for_long_multitask_session` proves the construction boundary: the default route constructs at most one entry brief, stays below 16,384 bytes, and four 25-entry detail pages reconstruct the complete 80-entry fixture. The focused session-logging suite passes all 88 tests.
