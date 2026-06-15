# Testing Strategy

Use this guide before adding or pruning tests in this repository. The goal is to preserve behavior contracts with fewer one-off regressions and less implementation-shape lock-in.

## Current Inventory

The June 15, 2026 inventory for #1521 was refreshed after the first reduction slices with:

- root workspace: 1,140 collected tests / 39 files
- planning package: 345 collected tests
- memory package: 246 collected tests
- verification package: 6 collected tests
- total: 1,737 collected tests / 60 files

Collection is fast, so the immediate problem is not raw collection time. A full root duration pass exceeded 10 minutes during #1521 measurement, so the current pressure is both runtime hotspots and a growing pile of narrow regression tests around broad workflow surfaces.

The largest clusters by test count are:

- `tests/test_model_cli_harness.py`
- `tests/test_workspace_report_cli.py`
- `tests/test_workspace_start_preflight_cli.py`
- `packages/planning/tests/test_summary.py`
- `tests/test_contract_tooling.py`
- `tests/test_generated_command_package_proof_runner.py`
- `tests/test_workspace_lifecycle_cli.py`
- `packages/planning/tests/test_archive.py`
- `tests/test_workspace_implement_cli.py`
- `packages/memory/tests/test_install.py`
- `tests/test_workspace_proof_cli.py`

These clusters are not automatically bad. Treat them as the first places to look for scenario consolidation, table-driven structure, or contract-owned conformance cases when related work changes them.

The first #1521 reduction slice consolidated repeated packaging builds in `tests/test_workspace_packaging.py`, `packages/memory/tests/test_packaging.py`, and `packages/planning/tests/test_packaging.py`. Those tests now reuse module-scoped wheel and sdist artifacts while preserving the same inventory, import, workflow, and install assertions. The packaging subset passes in about 20 seconds on the local Windows checkout.

The #1524 workflow-cluster slice merged the live-checkout active-only and verbose preflight mode checks in `tests/test_workspace_start_preflight_cli.py` into one scenario-matrix test. The affected `tests/test_workspace_report_cli.py` plus `tests/test_workspace_start_preflight_cli.py` subset moved from 234 collected tests / 139.18 seconds to 233 collected tests / 133.93 seconds while retaining the active-state, full-takeover, startup-guidance, and resolved-config assertions.

The #1526 ownership slice reviewed root lifecycle/module orchestration against Memory and Planning package-local install/current-state tests. The package-local install/current-memory subset moved from 143 tests / 3.33 seconds to 142 tests / 2.98 seconds by merging duplicate generated `current show` JSON/text view tests in `packages/memory/tests/test_current_memory.py`; the remaining current-memory tests are retained as explicit Memory residue, migration, and stale-active-state guard coverage.

Use this compact inventory when changing these clusters:

| Category | Current examples | Policy |
| --- | --- | --- |
| Keep ordinary | Report closeout trust, startup/preflight routing, proof selection, lifecycle mutation safety, package install behavior | Keep standalone when the behavior is high-risk semantic workflow coverage or transport-specific adapter behavior. |
| Merge | Repeated mode, section, or branch-shape checks with shared setup | Prefer scenario matrices or shared fixtures when assertions prove the same contract. |
| Convert | Stable generated command output, deterministic primitive behavior, reusable operation output examples | Move to conformance only when the replacement case names the owner and Python/TypeScript generated target proof runs it. |
| Delete | Obsolete compatibility fallbacks, duplicate generated-output assertions, dead fixture-shape regressions | Delete only after equivalent coverage is recorded in the replacement inventory. |

## Root Versus Package Ownership

Root workspace tests prove AW product orchestration: root lifecycle front doors, module selection, report/start/doctor routing, installed-state compatibility, cross-module integration, generated-target proof routing, and user-visible adapter behavior.

Package-local tests prove module-owned behavior: install/update/remove mechanics, package payload boundaries, module state mutation, schema/report primitives, package-local doctor/status behavior, and migration or residue checks that belong to that module. Do not duplicate module internals in root tests except through one representative orchestration path.

When root and package tests appear to cover the same behavior, keep the lower-level package test for module internals and keep only the smallest root test that proves integration through the AW front door. If both are retained, name the reason as one of: root orchestration, package boundary, high-risk workflow, migration residue, or adapter compatibility.

## Contract Ladder

Prefer testing behavior at the lowest level that proves the intended contract without preserving accidental implementation shape:

- Primitive conformance: deterministic execution units and target parity.
- Fragment or subflow behavior: reusable workflow patterns such as lifecycle mutation, validation, report shaping, and output rendering.
- Operation composition: command-facing contracts assembled from primitives and fragments.
- Representative command black-box behavior: user-visible compatibility, high-risk workflows, and transport behavior.

When a bug belongs to a reusable fragment, add or extend a fragment or operation case before adding several command-specific regressions. When the behavior is transport-specific, keep the target adapter test small and point behavior truth back to the operation contract.

## Contract-Owned Cases

The preferred long-term direction is contract-owned conformance:

- Operational contracts own canonical input/output or input/error cases.
- Python owns the single authoritative conformance runner.
- CLI, generated package, MCP, and future targets provide thin adapters.
- Adapters normalize invocation, result extraction, exit or error shape, and capability reporting.

The runner should remain simple: load contract cases, select a target adapter, run the declared operation with declared input and fixtures, normalize the result, and compare it with expected output or expected error.

## Add, Merge, Convert, Or Prune

Add a new test when the behavior is new, the failure mode is not already represented, and the right contract surface does not yet have an equivalent case.

Merge tests when several narrow regressions assert the same contract through slightly different fixtures. Prefer table-driven scenarios when the setup is shared and the expected behavior is easy to compare.

Convert tests when a command-level regression really belongs to a primitive, fragment, operation, or contract-owned conformance case. Keep one representative command black-box test if user-visible behavior or transport compatibility is the risk.

Prune only when stronger or equivalent coverage remains and the removed test preserves implementation detail, duplicate fixture shape, or obsolete behavior rather than a meaningful contract.

Do not prune coverage for historically fragile lifecycle, planning, archive, proof, generated-package freshness, or report/closeout behavior until an equivalent contract-owned case or scenario matrix exists.

## No-Prune Areas

Treat these areas as high-risk until a stronger replacement exists:

- Planning archive, closeout, and active-state mutation safety.
- Startup, preflight, implementation, proof, and report routing.
- Generated command package freshness, conformance, and target parity.
- Schema/reference docs and structured inventory checks.
- Package install and payload boundary behavior.

High-risk does not mean "add another one-off test by default." It means the replacement must be explicit, equivalent or stronger, and easy to review.

## Future Work

#1373 owns the plan for replacing existing regressions with contract-owned conformance cases after the migration shape is stable. Use [Contract-owned test replacement plan](contract-test-replacement-plan.md) for the current sequencing, inventory, and handoff rules.

#1374 owns replacing AW generated-command behavior tests with contract-owned conformance cases. Use [AW contract test replacement inventory](aw-contract-test-replacement-inventory.md) for the current AW-side conversion and ordinary-test retention record.

rickardvh/command-generation#9 owns the matching replacement work in the command-generation repository.
