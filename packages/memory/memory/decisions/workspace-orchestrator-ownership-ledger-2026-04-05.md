# Decision: Workspace Orchestrator And Ownership Ledger

## Status

Accepted

## Date

2026-04-05

## Load when

Read this note when changing startup guidance, managed fences, installer ownership rules, or the question of where product-managed workflow text should live.

## Review when

Review this note if installers begin reading the ownership ledger directly, if new modules are added under `.agentic-workspace/`, or if fence and uninstall conventions materially change.

## Failure signals

Failure looks like product-managed guidance spreading into repo-owned files without explicit fences, lifecycle tools drifting back to duplicated heuristics, or shared startup guidance becoming module-specific again.

## Decision

The workspace-level orchestrator contract lives at `.agentic-workspace/WORKFLOW.md` and the ownership ledger lives at `.agentic-workspace/OWNERSHIP.toml`. Shared product-managed startup guidance belongs there, while repo-owned execution surfaces stay outside that managed area unless they use explicit fences.

## Why

A single workspace-level contract is clearer than treating one module as the accidental owner of shared startup rules, and explicit ownership metadata is more reliable than scattered path heuristics during install, upgrade, verify, and uninstall.

## Consequences

Root `AGENTS.md` can stay thin, lifecycle behavior should converge on the ownership ledger, and module-specific workflow files should exist only when the workspace contract is not specific enough.

## Expected downstream impact

Planning-managed startup assets should remain behind the workspace orchestrator, installer behavior should continue converging on the ledger, and repo-owned execution surfaces should stay at root with minimal fenced insertions. Use [ownership-ledger-check](../../tools/skills/ownership-ledger-check/SKILL.md) for the repeatable validation workflow.

## Verify

Confirm that `.agentic-workspace/WORKFLOW.md`, `.agentic-workspace/OWNERSHIP.toml`, `AGENTS.md`, and installer behavior still reflect this ownership split.

## Last confirmed

2026-04-05 during workspace-orchestrator milestone 1
