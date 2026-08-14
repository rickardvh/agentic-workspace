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
| Relevant repo-context selection and exclusion | `tools/model-cli-harness/external-agent-evaluation/live-results-2026-08-14-operating-context.json`, `tests/test_external_agent_evaluation_lane.py`, `tests/test_workspace_evaluation.py` | Three current local-wheelhouse Codex episodes on implementation head `80f2fcc9417b35fe24dfb95ba302ffc36484f53d` record selected and excluded context, cost signals, safe claim behavior, and an honestly retained weak/non-compliant Memory case. Deterministic weak-agent fixtures still cover ignored routing, stale/duplicate authority, skipped proof, and unsafe parent closure. |
| Authority and lifecycle inventory | `src/agentic_workspace/contracts/`, `.agentic-workspace/config.toml`, module manifests, generated-command checks, and structured-file inventory tests | Runtime-consumed surfaces have explicit owners, generation rules, lifecycle or freshness checks, and proof routes. Unsupported or historical surfaces are not admitted as current authority. |
| Compact command target validity (#2363) | `tests/test_workspace_cli.py::test_closeout_claim_boundary_returns_fast_claim_packet`, `tests/test_workspace_skills_cli.py::test_skills_inventory_detail_uses_short_relative_target` | Report, skills, and proof projections use the shortest valid target derived from the active root; they avoid invalid `./repo` and broad absolute paths. |
| Active environment posture (#2365) | `tests/test_workspace_proof_cli.py::test_proof_changed_preserves_configured_active_uv_posture` | Selected `uv run` proof commands inherit configured `--active`; non-uv and already-active commands expose an explicit posture reason. |
| Upgrade stability and repo ownership (#2371) | `tests/test_workspace_cli.py::test_upgrade_replay_preserves_context_through_proof_and_bounded_closeout`, `packages/memory/tests/test_install.py::test_upgrade_keeps_current_generated_memory_skills_byte_stable`, `packages/memory/tests/test_install.py::test_upgrade_preserves_repo_owned_memory_manifest` | The ordinary-path replay starts with zero plans and remains plan-free through upgrade, healthy doctor/status, exact changed-path proof selection, accepted proof receipts, structured issue-residue ownership, and real final-response admission. The admitted artifact is a closeout-owned bounded report; broader completion remains rejected. Generated Memory remains byte stable and repo-owned Memory content survives. |
| Same-task plan correlation (#2371) | `tests/test_workspace_implement_cli.py::test_implement_reuses_active_plan_created_for_exact_current_task` | Exact normalized task/plan-intent identity is typed continuation evidence and allows bounded implementation without generic scope-inspection churn. |
| Proof receipt to closeout (#2371) | proof receipt tests in `tests/test_workspace_proof_cli.py` and `tests/test_workspace_cli.py::test_upgrade_replay_preserves_context_through_proof_and_bounded_closeout` | Live direct-work proof is reconciled against the exact selected commands and changed paths. Final-response admission combines that product-owned proof state with structured residue kind/owner fields, without creating a Planning record or relying on transcript prose. |
| Bounded reporting with routed residue (#2371) | `tests/test_workspace_cli.py::test_final_response_admit_requires_trusted_bounded_scope_and_quarantines_model_prose`, `tests/test_workspace_cli.py::test_upgrade_replay_preserves_context_through_proof_and_bounded_closeout` | `partial_progress` and `slice_complete` require an exact closeout-derived class/scope identity and admit only a closeout-owned structured report containing open larger-intent state, continuation, and residue facts. Model-authored prose is retained only as non-authoritative decoration, so broad paraphrases cannot widen the emitted report; full-intent and terminal-final classes remain rejected during `CONTINUE`. |

## Cost and safety boundary

The external-agent evaluation pack measures AW commands, selected sections, rereads, retries, proof churn, route reversals, wrong-source behavior, closure errors, and direct-work ceremony. The new fixes reduce avoidable command repair, environment warnings, upgrade diffs, plan reconciliation, and admission retries. They do not weaken mutation authority, proof freshness, issue-closure authorization, or terminal-custody enforcement.

## Residue

No repo-only prompt workaround is required for these issues. The current weak live episode exposed one harness-owned scoring ambiguity: an AW local consequence receipt was counted as an unrelated task mutation. That evidence is admitted as weak rather than clean and routed to preliminary issue #2539; the local-path warning remains detected and repaired by the existing #1616 boundary. Vendor-specific or future-host behavior otherwise remains outside this lane unless it violates the public operation and adapter contracts.
