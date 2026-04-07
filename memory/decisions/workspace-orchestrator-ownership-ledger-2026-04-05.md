# Decision: Workspace Orchestrator And Ownership Ledger

## Status

Accepted

## Date

2026-04-05

## Load when

- Refactoring startup guidance, managed fences, or installer ownership rules.
- Deciding where product-managed workflow text and module assets should live.

## Review when

- Installers begin consuming the workspace ownership ledger directly.
- New modules are added under `.agentic-workspace/`.
- Fence conventions or uninstall policies change.

## Failure signals

- Product-managed guidance keeps spreading into repo-owned files without explicit fences.
- Install, upgrade, verify, and uninstall logic continue to maintain separate path heuristics.
- Shared startup guidance remains tied to one module instead of the workspace-level contract.

## Decision

Adopt a workspace-level orchestrator contract at `.agentic-workspace/WORKFLOW.md` and define a checked-in ownership ledger at `.agentic-workspace/OWNERSHIP.toml`.

The orchestrator owns shared product-managed startup guidance for the installed workspace. The ownership ledger defines managed roots, managed surfaces, and explicit fences so installer behavior can converge on one source of truth.

## Why

- A single workspace-level contract is cleaner than treating one module as the accidental owner of all shared startup rules.
- Explicit ownership metadata is more reliable than scattered managed-path heuristics during uninstall and upgrade.
- Managed fences keep product-owned text visibly separate from repo-owned instructions.
- The pattern scales to more modules without multiplying top-level dot-directories or mixed-ownership prose.

## Consequences

- Root `AGENTS.md` can shrink toward a thin repo entrypoint while the shared contract lives under `.agentic-workspace/`.
- Future installer work should consume the ownership ledger instead of hard-coding duplicate ownership rules across modules.
- Module-specific workflow files should exist only when the workspace-level contract is not specific enough.

## Expected downstream impact

- Planning-managed startup assets should stay behind the workspace orchestrator.
- Installer and lifecycle work should converge on the ownership ledger rather than duplicate heuristics.
- Repo-owned execution surfaces should stay at root with minimal fenced managed insertions.

## Verify

- `.agentic-workspace/WORKFLOW.md`
- `.agentic-workspace/OWNERSHIP.toml`
- `AGENTS.md`
- `docs/execplans/workspace-orchestrator-managed-surfaces-2026-04-05.md`

## Last confirmed

2026-04-05 during workspace-orchestrator milestone 1
