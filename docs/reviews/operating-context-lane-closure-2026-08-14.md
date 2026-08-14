# Operating-context lane closure review

Date: 2026-08-14

Issues reviewed: #2296, #2302, #2307, #2308, #2363, #2365, and #2371.

## Decision

The repository-context and one-step compilation intent is satisfied for the supported AW runtime. The final dogfood gaps found during closure were fixed in this change: compact commands now use the shortest valid active target, proof commands preserve configured `uv run --active` posture, repo-owned Memory manifests survive payload upgrades, an exact current task reuses the plan created for that task, and final-response admission can admit only an explicitly authorized bounded claim while still rejecting broader completion.

This decision does not claim that historical reviews or arbitrary repository prose are runtime authorities. Current routing remains contract-, manifest-, operation-, Planning-, Memory-, ownership-, and proof-driven. Historical material is evidence only.

## Acceptance mapping

| Concern | Canonical evidence | Result |
| --- | --- | --- |
| One executable action and compatibility projection | `src/agentic_workspace/operating_decision.py`, `src/agentic_workspace/composed_operation_scenarios.py`, `tests/test_operating_decision.py`, `tests/test_composed_operation_scenarios.py` | The compiled decision owns the primary operation identity; compatibility fields are projections tested for agreement. |
| Relevant repo-context selection and exclusion | `tests/test_external_agent_evaluation_lane.py`, `tests/test_workspace_evaluation.py`, `tests/test_workspace_cli.py`, `tests/test_workspace_implement_cli.py` | Cold-start, stale-source, direct-work, ownership, proof, closeout, and degraded cases assert selected and excluded context plus completion-cost metrics. |
| Authority and lifecycle inventory | `src/agentic_workspace/contracts/`, `.agentic-workspace/config.toml`, module manifests, generated-command checks, and structured-file inventory tests | Runtime-consumed surfaces have explicit owners, generation rules, lifecycle or freshness checks, and proof routes. Unsupported or historical surfaces are not admitted as current authority. |
| Compact command target validity (#2363) | `tests/test_workspace_cli.py::test_closeout_claim_boundary_returns_fast_claim_packet`, `tests/test_workspace_skills_cli.py::test_skills_inventory_detail_uses_short_relative_target` | Report, skills, and proof projections use the shortest valid target derived from the active root; they avoid invalid `./repo` and broad absolute paths. |
| Active environment posture (#2365) | `tests/test_workspace_proof_cli.py::test_proof_changed_preserves_configured_active_uv_posture` | Selected `uv run` proof commands inherit configured `--active`; non-uv and already-active commands expose an explicit posture reason. |
| Upgrade stability and repo ownership (#2371) | `packages/memory/tests/test_install.py::test_upgrade_keeps_current_generated_memory_skills_byte_stable`, `packages/memory/tests/test_install.py::test_upgrade_preserves_repo_owned_memory_manifest` | Current generated skill files remain byte-stable and clean at EOF; the repo-owned Memory manifest is no longer overwritten as shared replaceable payload. |
| Same-task plan correlation (#2371) | `tests/test_workspace_implement_cli.py::test_implement_reuses_active_plan_created_for_exact_current_task` | Exact normalized task/plan-intent identity is typed continuation evidence and allows bounded implementation without generic scope-inspection churn. |
| Proof receipt to closeout (#2371) | proof receipt tests in `tests/test_workspace_proof_cli.py` and Planning `--proof-from last` closeout coverage | Live proof has a command-owned receipt route consumable by closeout without a retroactive hand-authored plan transcript. |
| Bounded reporting with routed residue (#2371) | `tests/test_workspace_cli.py::test_final_response_admit_accepts_only_authorized_bounded_report_during_continue` | `partial_progress` and `slice_complete` are admitted during `CONTINUE` only when the closeout contract authorizes that exact class. Terminal custody, lane, parent, full-intent, and issue-closure claims remain blocked. |

## Cost and safety boundary

The external-agent evaluation pack measures AW commands, selected sections, rereads, retries, proof churn, route reversals, wrong-source behavior, closure errors, and direct-work ceremony. The new fixes reduce avoidable command repair, environment warnings, upgrade diffs, plan reconciliation, and admission retries. They do not weaken mutation authority, proof freshness, issue-closure authorization, or terminal-custody enforcement.

## Residue

No repo-only prompt workaround is required for these issues. Vendor-specific or future-host behavior remains outside this lane unless it violates the public operation and adapter contracts; such a failure should be opened as a new narrow product issue with a reproducible fixture.
