# Testing Strategy

Use this guide before adding or pruning tests in this repository. The goal is to preserve behavior contracts with fewer one-off regressions and less implementation-shape lock-in.

## Current Inventory

The June 15, 2026 inventory for #1521 was refreshed after the first reduction slices with:

- root workspace: 613 collected tests / 34 files
- planning package: 248 collected tests
- memory package: 246 collected tests
- verification package: 11 collected tests
- total: 1,118 collected tests / 57 files

Collection is fast, so the immediate problem is not raw collection time. A full root duration pass exceeded 10 minutes during #1521 measurement, so the current pressure is both runtime hotspots and a growing pile of narrow regression tests around broad workflow surfaces.

The largest current executable clusters by collected test count are:

- `tests/test_generated_tool_conformance.py` (91)
- `packages/memory/tests/test_install.py` (79)
- `packages/planning/tests/test_archive.py` (64)
- `tests/test_workspace_implement_cli.py` (61)
- `tests/test_workspace_proof_cli.py` (56)
- `tests/test_generated_command_package_proof_runner.py` (56)
- `tests/test_workspace_config_cli.py` (50)
- `packages/planning/tests/test_install.py` (47)
- `packages/memory/tests/test_doctor.py` (45)
- `packages/memory/tests/test_routing.py` (44)
- `packages/planning/tests/test_check_planning_surfaces.py` (43)

These current clusters are not automatically bad. Treat them as the first places to look for scenario consolidation, table-driven structure, or contract-owned conformance cases when related work changes them.

Retired legacy clusters from the #1536/#1537/#1538/#1539/#1540/#1541 finish-lane slice are no longer current executable hotspots: `tests/test_model_cli_harness.py`, `tests/test_workspace_report_cli.py`, `tests/test_workspace_start_preflight_cli.py`, `packages/planning/tests/test_summary.py`, `tests/test_contract_tooling.py`, and `tests/test_workspace_lifecycle_cli.py`. Their migration records live in `docs/maintainer/test-knowledge-inventory.md`; new work should use focused current evidence rather than reviving those broad files.

The first #1521 reduction slice consolidated repeated packaging builds in `tests/test_workspace_packaging.py`, `packages/memory/tests/test_packaging.py`, and `packages/planning/tests/test_packaging.py`. Those tests now reuse module-scoped wheel and sdist artifacts while preserving the same inventory, import, workflow, and install assertions. The packaging subset passes in about 20 seconds on the local Windows checkout.

The #1524 workflow-cluster slice merged the live-checkout active-only and verbose preflight mode checks in `tests/test_workspace_start_preflight_cli.py` into one scenario-matrix test. The affected `tests/test_workspace_report_cli.py` plus `tests/test_workspace_start_preflight_cli.py` subset moved from 234 collected tests / 139.18 seconds to 233 collected tests / 133.93 seconds while retaining the active-state, full-takeover, startup-guidance, and resolved-config assertions.

The #1526 ownership slice reviewed root lifecycle/module orchestration against Memory and Planning package-local install/current-state tests. The package-local install/current-memory subset moved from 143 tests / 3.33 seconds to 142 tests / 2.98 seconds by merging duplicate generated `current show` JSON/text view tests in `packages/memory/tests/test_current_memory.py`; the remaining current-memory tests are retained as explicit Memory residue, migration, and stale-active-state guard coverage.

The #1531/#1532/#1533 follow-up slice merged narrow duplicate scenario groups in the largest remaining root clusters: report section aliases, model CLI harness raw-read warning variants, and static generated-package completion-gate evidence checks. The affected report/start-preflight, model harness, and generated proof-runner subset moved from 433 collected tests to 428 collected tests while retaining high-risk workflow, scorer-warning, and proof/checker coverage.

The #1535 Verification dogfood slice added the host-neutral `evidence_strategy` diagnostic report and used it to classify #1534 hotspot files before further reduction. The dogfood pass found 7 high-confidence merge candidates across 710 hotspot tests under the conservative exact-prefix heuristic, then merged the clearest model-harness, generated proof-runner, implement-context, and planning cleanup/routing groups. A follow-up reduction pass broadened that same scenario-matrix approach to adapter rendering, quality-signal, execution-warning, and generated-proof acceptance variants. The review fix tightened the Verification authority boundary so strategy prose is surfaced for agent judgment rather than interpreted by string matching.

The #1536/#1537/#1538/#1539/#1540/#1541 finish-lane slice added the `test-knowledge-inventory.md` migration record, extended Verification with inventory review questions, and consolidated more ordinary regressions into behavior-class matrices. A first pass moved the full `tests packages` inventory from 1,710 collected tests to 1,698 collected tests while adding durable knowledge records and keeping scenario labels for generated proof-runner static-surface failures, generated operation CLI input proof, model-harness native-plan bridge failures, and planning archive cleanup pointer variants.

The follow-through pass then removed the largest legacy regression clusters after recording compact migration entries in `docs/maintainer/test-knowledge-inventory.md`: report CLI, model CLI harness, start/preflight CLI, planning summary, contract tooling, and workspace lifecycle. Those files no longer define permanent executable proof and are not retained as source archives. The executable suite now sits inside the advisory target range at 1,118 collected tests, and `make test-workspace` passed in 103.37 seconds on the local Windows checkout.

## Suite Budgets

These budgets are advisory until a maintainer chooses enforcement. Use them as closeout pressure against casual permanent regression growth:

| Surface | Current count | Target range | Runtime budget |
| --- | ---: | ---: | --- |
| Total `tests packages` suite | 1,118 | 900-1,200 | `make test-workspace` passed in 103.37 seconds after retiring legacy clusters. |
| Root workspace tests | 613 | 500-700 | Prefer root tests only for product orchestration, user-visible adapter behavior, and high-risk workflow semantics. |
| Planning package tests | 248 | 250-325 | Slightly under target after retiring planning summary regressions; add package tests only for durable module contracts. |
| Memory package tests | 246 | 200-250 | Near target; avoid adding one-off migration regressions unless they cannot be represented as scenario rows. |
| Verification package tests | 11 | 40-80 | Expected to grow as Verification takes on evidence surfaces, but new cases should cover report contracts rather than host policy decisions. |

Before adding a permanent ordinary test, PR closeout should answer whether the evidence is behavior-class coverage, temporary characterization, conformance evidence, or historical regression residue. If it is historical residue, preserve the failure mode in `test-knowledge-inventory.md`, Memory, Verification evidence, or an issue/PR note before deleting the executable test.

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

## Current Follow-Through

The #1373/#1374 migration lanes established the contract-owned conformance
direction and the AW-side generated-command inventory. Treat
[Contract-owned test replacement plan](contract-test-replacement-plan.md) and
[AW contract test replacement inventory](aw-contract-test-replacement-inventory.md)
as retained records, not open ownership claims.

New reductions should use the current owner map: keep high-risk root workflow
proof where it is the narrowest evidence, move stable generated behavior to
contract-owned conformance when both Python and TypeScript generated targets can
consume it, and use Verification proof decisions or dispositions when changing
ordinary tests would otherwise leave the reasoning in chat or PR prose.
