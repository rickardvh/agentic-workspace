# Issues #2748 and #2750 current-master triage

Captured 2026-08-26 on merged master `f12025f324c71592e5347d01d79c9569fa72f277`.

## #2748 structural authority gap

The exact PR #2746 task-context mismatch is absorbed on current master and is not used as the new failing fixture. A current structural audit still finds a split authority: `workspace_runtime_core.py::_execute_selected_proof_payload` reaches `run_trusted_shell` without first calling `proof_command_admission`, `proof_receipt_admission`, or `_selected_proof_command_for_receipt` for the selected command. Canonical selection binding and receipt admission are entered only by the separate receipt writer/reconciliation path.

Relevant merged-master locations:

- executor entry: `src/agentic_workspace/workspace_runtime_core.py:50426`
- process launch: `src/agentic_workspace/workspace_runtime_core.py:50542`
- receipt selection binding: `src/agentic_workspace/workspace_runtime_core.py:50015`
- receipt admission: `src/agentic_workspace/workspace_runtime_core.py:50067`

The repair calls those canonical owners before launch and records through the same receipt authority after runtime completion. `test_selected_proof_execution_reconciles_and_reuses_local_receipts` exercises the ordinary valid executor end to end: four admitted commands launch, write canonical receipts, and reconcile as accepted. The zero-launch counterexample proves a deterministic binding rejection starts no process.

## #2750 second current publication class

On merged master, a proof subject with stable `src/app.py`, command `make test`, and a not-yet-published `.agentic-workspace/planning/closeout-evidence/lane.json` changed from fingerprint `b832400ecf65d30a22adbe64ed1d0620989321969644cc41fd19029b5bbde83c` to `95c5359e2d4312e74d8a0f4cba459cd2b4e1e1feedfb80ec3bafc7e358e53e72` when that closeout-evidence file was published. The fallback also changed from `whole-state-required` to `not-required`. This is a live second evidence class outside the repaired PR #2746 receipt fixture.

The repair classifies canonical receipts, recovery manifests, and Planning closeout evidence by dependency role. They remain non-semantic publication outputs unless the claim explicitly declares them as inputs. Source edits still stale the subject, and an evidence artifact explicitly used by another claim remains invalidating.

This triage establishes current structural and executable gaps after #2746; it does not rely on the historical mismatch alone or introduce a second admission/freshness authority.
