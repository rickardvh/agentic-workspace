# Selected-proof execution replay — 2026-08-31

This is the maintained closure replay for #2727 and #2901 on PR #2903. It was captured on Windows, Python 3.13, after rebasing the proof-execution layer onto the repaired PR #2902 head. All commands exited 0.

## PR #2898 subject

The original operation selected seven commands, took 676.866 seconds, and required a tracked receipt-only commit containing the index plus seven receipt files and 882 inserted lines.

The repaired ordinary operation was invoked once as `proof --execute-selected` for the same four Planning record paths. The route now contains five commands because PR #2902 narrows the subject before execution.

| Observation | Repaired result |
| --- | --- |
| Outer wall time | 28.209 s |
| Run identity | `e958bd0912ae0a116711` |
| Commands | 5 required, 5 passed |
| Canonical admission | 1 aggregate accepted, 0 rejected |
| Owner coverage | `planning_surfaces`, `subsystem:planning-records`, and `domain:planning_record_surfaces` satisfied |
| Tracked file delta | 0 files |
| Tracked inserted lines/bytes | 0 / 0 |
| Repository residue | `false` |
| Aggregate receipt | `.agentic-workspace/local/proof-receipts/last.json` |
| Per-command detail | 5 exact JSON references under `.agentic-workspace/local/proof-receipts/runs/e958bd0912ae0a116711/` |
| Claim boundary | selected proof executed; completion still requires intent and closeout reconciliation |

An unchanged second invocation completed in 2.454 seconds with status `reused-fresh-evidence`, reused the same run identity, launched no proof commands, left tracked status empty, and left local receipt-history size unchanged at 3,031,265 bytes.

## Planning/report subject

The original report-only reproduction selected eight commands, took 716.582–744.734 seconds, and produced eight tracked receipt files plus an index update, 816 inserted lines, and 30,881 receipt-document bytes.

The repaired one-operation replay selected six focused commands and completed in 38.086 seconds:

- run identity `2f700889f489cab6ba39`;
- 6 required and 6 passed;
- one accepted aggregate admission and six exact local command references;
- all five selected owners satisfied, including `domain:maintained_review_records` and `domain:planning_record_surfaces`;
- 0 tracked files, 0 inserted tracked lines, 0 inserted tracked bytes, and `repository_residue=false`.

This second subject proves the persistence result is not specific to the four-record fixture.

## Ordinary continuation replays

The #1891 semantic scope (`reporting_support.py`, `workspace_runtime_core.py`, `tests/test_workspace_cli.py`, and its release fragment) selects 12 commands. Its compact ordinary result now has:

- `kind=proof-next-decision/v1`;
- `next.action=execute-selected-proof`;
- one exact `proof --execute-selected` command carrying all four changed paths;
- no `--record-receipt` in the primary continuation;
- explicit manual interoperability availability behind `proof_receipt_bridge`.

This replay also guards the discovered template boundary: the selected set contains a supported `<paths>` command, and ordinary guidance now materializes it before admission just as the executor does.

A materially different `README.md` proof lane selects one command and also returns `next.action=execute-selected-proof`, with manual recording absent from the primary continuation and retained only as explicit detail/recovery.

## Executable acceptance matrix

- Success, aggregate persistence, exact per-command detail, and Git-residue invariance: `test_selected_proof_execution_leaves_tracked_receipt_store_unchanged`.
- Changed-path template admission: `test_ordinary_proof_guidance_materializes_changed_path_templates_before_admission` and `test_selected_proof_execution_materializes_changed_path_templates_before_admission`.
- Failure, partial resume, and stale subject: `test_selected_proof_execution_resumes_failure_and_blocks_stale_subject`.
- Cancel and timeout outcomes: `test_selected_proof_execution_records_cancel_and_timeout_outcomes`.
- Route-refinement claim blocking: `test_selected_proof_execution_keeps_route_refinement_claim_blocked`.
- Fresh reuse and local receipt reconciliation: `test_selected_proof_execution_reconciles_and_reuses_local_receipts`.
- Manual `--record-receipt` interoperability publication remains covered by the explicit receipt-recording tests; it is not the ordinary next action.
