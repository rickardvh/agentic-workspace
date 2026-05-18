# Routing Feedback

## Status

Active calibration note

## Scope

Compact record of ordinary AW routing friction that should influence future memory, planning, or startup behavior.

## Current Signals

- 2026-05-18: The repo memory index routed "calibrating routing quality" to this file, but the file was missing. The fix is to keep this note present so agents can capture routing friction without falling back to chat-only reporting.
- 2026-05-18: PR #1057 review-comment handling exposed planning-gate friction: `start` allowed a bounded direct fix, but `implement --changed` later required creating an active execplan, and the scaffold introduced placeholders that needed cleanup before closeout. Tracked as #1058; future routing should prefer a one-command filled checkpoint or direct proof-only path for routine PR-comment fixes.

## Review Trigger

Review when routing feedback grows beyond compact calibration notes or when repeated entries should be promoted to a runbook, issue, planning candidate, or durable decision.
