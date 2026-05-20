# Routing Feedback

## Status

Active calibration note

## Scope

Compact record of ordinary AW routing friction that should influence future memory, planning, or startup behavior.

## Current Signals

- 2026-05-18: The repo memory index routed "calibrating routing quality" to this file, but the file was missing. The fix is to keep this note present so agents can capture routing friction without falling back to chat-only reporting.
- 2026-05-18: PR #1057 review-comment handling exposed planning-gate friction: `start` allowed a bounded direct fix, but `implement --changed` later required creating an active execplan, and the scaffold introduced placeholders that needed cleanup before closeout. #1058 implemented the direct proof-only path for bounded routine PR review-comment repairs; use normal execplans only when scope grows or parent intent changes.
- 2026-05-18: Treat "question every decision and ask whether there is a better way" as a routine dogfooding posture, not a one-off chat correction. Apply it to implementation choices, workflow routing, validation scope, delegation, Memory capture, and closeout; route repeated improvement pressure upstream instead of only noting it in chat.
- 2026-05-20: `planning closeout` can partially write normalized archive fields before reporting a closeout blocker when the supplied intent status and residue route conflict. Prefer transactional validation or clearer rerun guidance so agents do not need to inspect and repair contradictory closeout residue manually.

## Review Trigger

Review when routing feedback grows beyond compact calibration notes or when repeated entries should be promoted to a runbook, issue, planning candidate, or durable decision.
