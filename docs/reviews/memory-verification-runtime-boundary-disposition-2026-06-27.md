# Memory and Verification Runtime Boundary Disposition

Date: 2026-06-27
Issues: #1658, parent #1649
Lane: P2 runtime boundary decomposition audits

## Summary

#1658 audited the Memory and Verification accepted runtime boundaries that
remain in `python_runtime_projection_inventory.json`.

Baseline after this slice:

- accepted runtime symbols: 75
- Memory package runtime boundaries: 19
- Verification package runtime boundaries: 1

This slice implements the safe local decomposition available now: Memory compact
action/result shaping is isolated behind `_compact_memory_actions` and
`_memory_action_count`, then reused by compact result and promotion-report
payloads. It does not move Memory route/search/capture/review/sync judgment or
Verification proof interpretation into command-generation.

The remaining hand-owned count is unchanged. Further movement needs narrower
command-generation support:

- rickardvh/command-generation#74: declared view/resource/payload scaffolding
- rickardvh/command-generation#75: generic transaction safety contracts for
  mutation scaffolding

## Disposition Table

| Symbol | Group | Safe split now | Semantic owner after split | Retained reason |
| --- | --- | --- | --- | --- |
| `adopt_bootstrap` | mutation scaffolding | Existing dry-run/dataflow split; no new semantic move | Memory lifecycle mutation safety/provenance | Adopt policy and managed-surface safety stay package-owned until CG #75 |
| `cleanup_bootstrap_workspace` | mutation scaffolding | None beyond disposition | Memory cleanup safety/provenance | Cleanup applies destructive workspace changes and requires package safety proof |
| `create_memory_note` | mutation scaffolding | None beyond disposition | Memory note mutation safety/provenance | Note creation writes durable knowledge and provenance |
| `install_bootstrap` (`memory.init.lifecycle`) | mutation scaffolding | Existing dry-run/dataflow split; no new semantic move | Memory lifecycle mutation safety/provenance | Init/install payload mutation remains package-owned until CG #75 |
| `install_bootstrap` (`memory.install.lifecycle`) | mutation scaffolding | Existing dry-run/dataflow split; no new semantic move | Memory lifecycle mutation safety/provenance | Init/install payload mutation remains package-owned until CG #75 |
| `migrate_layout` | mutation scaffolding | None beyond disposition | Memory migration safety/provenance | Migration changes durable layout and residue handling |
| `uninstall_bootstrap` | mutation scaffolding | None beyond disposition | Memory lifecycle mutation safety/provenance | Uninstall safety and manual-review behavior stay package-owned |
| `upgrade_bootstrap` | mutation scaffolding | None beyond disposition | Memory lifecycle mutation safety/provenance | Upgrade source, payload, and safety behavior stay package-owned |
| `_load_memory_bootstrap_doctor` | view/payload scaffolding | Shared compact action view policy reused | Memory status/doctor view and strict-policy fallback | Tiny view scaffolding can move after CG #74; strict/verbose policy remains Memory |
| `_load_memory_current` | view/payload scaffolding | None beyond disposition | Memory current-memory view policy | Check/show semantics reflect Memory state and compatibility policy |
| `_load_memory_prompt` | view/payload scaffolding | None beyond disposition | Memory prompt/template policy | Prompt wording and upgrade-source guidance are Memory-owned |
| `_load_memory_report` | view/payload scaffolding | Shared compact action view policy supports tiny views | Memory report view policy | Tiny report scaffolding can move after CG #74; verbose report remains Memory |
| `_load_memory_route_report` | view/payload scaffolding | None beyond disposition | Memory route-report view policy | Tiny route snapshot can move after CG #74; route evaluation stays Memory |
| `_load_memory_promotion_report` | view/payload scaffolding | Shared compact action view policy reused | Memory promotion policy/view | Promotion candidates encode durable-knowledge policy |
| `suggest_memory_note_capture` | durable-knowledge judgment | None | Memory capture-vs-route judgment | Capture advice encodes relevance and durability judgment |
| `review_routes` | durable-knowledge judgment | None | Memory route quality judgment | Route review evaluates route quality and remediation |
| `route_memory` | durable-knowledge judgment | None | Memory route ranking judgment | Routing ranks relevance and read-first advice |
| `search_memory` | durable-knowledge judgment | None | Memory search relevance judgment | Search semantics are durable-knowledge relevance policy |
| `sync_memory` | durable-knowledge judgment | None | Memory sync/remediation judgment | Sync records and remediates Memory state |
| `verification_report_payload` | mixed report/view boundary | None beyond disposition | Verification evidence/proof interpretation | Report wiring can move after CG #74, but protocol activation, freshness, and bounded-evidence projection remain Verification |

## Implemented Safe Decomposition

Implemented now:

- introduced `MEMORY_COMPACT_ACTION_KEYS`
- introduced `_memory_action_count`
- introduced `_compact_memory_actions`
- refactored `_compact_result_dict` and `_compact_promotion_report` through the
  shared compact action view helper
- added focused tests for compact result and promotion-report action shaping
- updated runtime projection and operation execution inventories with #1658
  grouping and semantic-owner-after-split language

Runtime source edit classification:

- changed path:
  `packages/memory/src/repo_memory_bootstrap/runtime_primitives.py`
- edit reason: `new-primitive-implementation`
- owner: Memory package runtime boundary owner
- source symbols:
  `MEMORY_COMPACT_ACTION_KEYS`, `_memory_action_count`,
  `_compact_memory_actions`, `_compact_result_dict`,
  `_compact_promotion_report`
- focused proof:
  `uv run pytest packages/memory/tests/test_report.py::test_memory_compact_result_uses_shared_action_view_policy packages/memory/tests/test_report.py::test_memory_promotion_report_uses_shared_action_view_policy -q`
- residual owner: command-generation owns generic view/payload scaffolding through
  command-generation#74 and mutation transaction scaffolding through
  command-generation#75; Memory and Verification keep semantic judgment explicit

## Remaining Boundary Count

Remaining accepted Memory package runtime boundaries: 19.
Remaining accepted Verification package runtime boundaries: 1.

Why retained:

- Memory route/search/capture/review/sync behavior owns durable-knowledge
  relevance, durability, route quality, and capture-vs-route judgment
- Memory lifecycle/create/migrate/cleanup/uninstall/upgrade behavior owns
  mutation safety and provenance until CG #75 exists
- Memory view/prompt/report scaffolding can shrink later, but Memory view policy
  remains explicit until CG #74 exists
- Verification report wiring may shrink later, but Verification evidence and
  proof interpretation remain explicit package semantics

This slice completes the #1658 lane item and advances #1649, but does not by
itself close the whole parent issue.
