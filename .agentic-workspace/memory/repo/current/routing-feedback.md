# Routing Feedback

## Status

Active calibration note

## Scope

- Optional, agent-only routing calibration for concrete missed-note or over-routing cases.
- Keep this file compact; promote repeated or durable learnings to a runbook, issue, planning candidate, or decision note.

## Load when

- Calibrating memory, planning, startup, or closeout routing against a concrete missed-note or over-routing case.
- Reviewing whether existing routing feedback still reproduces after route, doctor, or workflow changes.

## Review when

- A recorded case is tuned, rejected, no longer reproduces, or grows beyond compact calibration.
- Doctor reports routing-feedback structure drift or the note starts accumulating chronological task-log entries.

## Missed-note entries

- Memory index routed routing-quality calibration here before the note existed. Keep the file available only when repo-local calibration is active so agents have a narrow capture target instead of leaving routing friction in chat.

## Over-routing entries

- PR #1057 review-comment handling exposed planning-gate friction: `start` allowed a bounded direct fix, but `implement --changed` later required an active execplan and scaffold cleanup. PR #1058 implemented the direct proof-only path for bounded routine PR review-comment repairs; use normal execplans only when scope grows or parent intent changes.
- Treat "question every decision and ask whether there is a better way" as ongoing dogfooding posture rather than a one-off chat correction. Apply it to implementation choices, workflow routing, validation scope, delegation, memory capture, and closeout; route repeated improvement pressure upstream instead of expanding this note.
- `planning closeout` could partially write normalized archive fields before reporting a blocker when intent status and residue route conflicted. Prefer transactional validation or clearer rerun guidance so agents do not need manual residue repair.
- `planning close-item` / `archive-plan` made completed execplan closeout feel manual when retained archive evidence exceeded the structured-file inventory guardrail. PR #1099 addressed the `close-item` cleanup path by skipping oversized retained archive evidence; keep watching explicit `archive-plan --retain-archive` cases for clearer rerun guidance.

## Synthesis

- Keep only compact, concrete calibration cases here.
- Promote repeated workflow lessons out of this note once a runbook, issue, test, or contract owns the behavior.

## Last confirmed

2026-06-29
