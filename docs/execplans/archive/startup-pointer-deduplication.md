# Startup Pointer Deduplication

Status: completed
Owner: codex
Created: 2026-04-07

## Goal

Reduce redundant startup noise in installed `AGENTS.md` entrypoints by replacing the current two-block workspace-plus-memory workflow pointer pattern with a quieter startup contract that still preserves module-local guidance and ownership boundaries.

## Why

Dogfooding in adopter repositories showed that the current startup surface was mechanically correct but unnecessarily repetitive:

- `AGENTS.md` received both a workspace workflow pointer and a memory workflow pointer.
- Agents were asked to read two adjacent "shared workflow rules" blocks before any repo-owned instructions.
- The distinction between shared workspace startup rules and module-local memory rules is real, but the top-level entrypoint was carrying too much of that structure directly.

This was a product signal, not just a repo-local preference. The package contract now makes the quiet path the default.

## Scope

In scope:

- define the intended startup contract for root `AGENTS.md`
- delegate module-local workflow discovery through `.agentic-workspace/WORKFLOW.md`
- update the relevant workspace and memory package install/upgrade behavior
- update payload surfaces and tests
- validate with clean-room orchestrator install and upgrade paths

Out of scope:

- broader memory hygiene or overlap-audit cleanup
- redesigning package composition beyond startup entrypoint behavior
- collapsing module-local workflow files themselves unless the contract change clearly requires it

## Requirements

1. Installed `AGENTS.md` should avoid adjacent redundant workflow-pointer blocks when a quieter contract can preserve the same routing outcome.
2. Shared workspace startup guidance must remain discoverable from the repo entrypoint.
3. Memory-specific operating rules must remain discoverable without requiring a second top-level pointer block in normal startup.
4. Ownership boundaries must stay explicit: repo-owned entrypoint content remains repo-owned, and managed guidance remains fenced or enclave-owned.
5. Orchestrated installs, including memory-only module selections through `agentic-workspace`, must converge on the same workspace-owned startup contract.
6. Root workspace install, module-local install, upgrade, status, and doctor flows must agree on the new contract.
7. The fix must be verified against an adopter-style repo, not just this monorepo source tree.

## Outcome

- `agentic-workspace` now installs only the shared workspace pointer at the top of `AGENTS.md`.
- `.agentic-workspace/WORKFLOW.md` now explicitly owns delegation to module-local workflow files.
- Workspace `status` and `doctor` flag redundant top-level memory pointer blocks instead of requiring them.
- Memory upgrade logic accepts the shared workspace pointer as the canonical startup contract and can remove stale redundant memory pointer blocks during entrypoint patching.
- Regression tests cover fresh init, memory-only orchestrator init, status drift, and memory-upgrade compatibility.

## Validation

- `uv run pytest tests/test_workspace_cli.py`
- `uv run pytest packages/memory/tests/test_installer.py`
- `uv run ruff check src/agentic_workspace tests/test_workspace_cli.py packages/memory/src/repo_memory_bootstrap packages/memory/tests/test_installer.py`
- clean-room `uv run python -` smoke test for `agentic-workspace init --modules memory`
- `uv run agentic-planning-bootstrap upgrade --target .`
- `uv run agentic-memory-bootstrap upgrade --target .`
