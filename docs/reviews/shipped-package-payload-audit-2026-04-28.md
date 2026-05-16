# Shipped Package Payload Audit - 2026-04-28

## Surface Value

This is evidence/history for #460, not ordinary operating input. It exists to make the shipped/default footprint reviewable without asking agents to scan package build metadata, bootstrap payload trees, and installer tests.

## Classification

| Surface | Necessity class | Shipped shape | Decision |
| --- | --- | --- | --- |
| Root Python package code under `src/agentic_workspace/` | daily operation required | root wheel/sdist | Keep; this is the command runtime and contract reader. |
| Root contracts under `src/agentic_workspace/contracts/` | lifecycle required | root wheel/sdist | Keep; commands use them as machine-readable authority rather than prose adapters. |
| Root managed payload under `src/agentic_workspace/_payload/` | lifecycle required | root wheel/sdist/install target | Keep small; currently limited to workspace ownership, workflow, and system-intent workflow surfaces. |
| Root generated command adapter metadata | generated/proof-only | `generated/workspace/python/generated_command_adapters.json` in source/sdist | Keep out of package-local runtime modules; checks and conformance load generated JSON. |
| Root `generated_cli_package/` | generated/proof-only | source checkout plus wheel private implementation bridge | Keep source bridge small; installed CLIs import bundled private generated package data. |
| Planning required payload | daily operation required | planning package payload/install target | Keep; smallest safe core is AGENTS adapter, execution/routing/config/system-intent docs, execplan template/readmes, upgrade source, and agent manifest. |
| Planning optional payload | optional advanced feature | planning package payload, installed only with optional payload selection | Keep as optional while #450 continues; review/intake/external/reconciliation surfaces should not become default startup input. |
| Planning bundled skills | optional advanced feature / maintainer workflow | planning package payload | Keep behind skill discovery; not required for generic package use. |
| Planning generated command adapter metadata | generated/proof-only | `generated/planning/python/generated_command_adapters.json` in source tree | Keep out of package-local runtime modules; checks and conformance load generated JSON. |
| Planning `generated_cli_package/` | generated/proof-only | source checkout plus wheel private implementation bridge | Keep source bridge small; installed CLIs import bundled private generated package data. |
| Memory required payload | daily operation / lifecycle required | memory package payload/install target | Keep; repo memory index, manifest, workflow, metadata docs, upgrade source, seed directories, and lifecycle skills support install and recovery. |
| Memory current-memory baseline | obsolete as required payload | no required current baseline | Keep empty; packaging tests now assert no required shipped current-memory baseline. |
| Memory routing-feedback seed | optional advanced calibration | opt-in repo-created note | #472 removed it from ordinary package/install payload; keep route-review and hygiene support when a repo creates the note. |
| Memory bootstrap helper skills | lifecycle required | memory package payload | Keep for install/adopt/upgrade/uninstall recovery. |
| Memory optional fragments | optional advanced feature | memory package sdist/source payload, applied only by optional paths | Keep optional; not daily startup input. |
| Memory generated command adapter metadata | generated/proof-only | `generated/memory/python/generated_command_adapters.json` in source tree | Keep out of package-local runtime modules; checks and conformance load generated JSON. |
| Memory `generated_cli_package/` | generated/proof-only | source checkout plus wheel private implementation bridge | Keep source bridge small; installed CLIs import bundled private generated package data. |

## Implemented In This Slice

- Added an explicit packaging assertion that memory has no required shipped current-memory baseline.
- Removed the optional `routing-feedback.md` seed from the memory packaging test's required core payload set.
- Kept #459's generated CLI package metadata boundary and later moved command adapter metadata out of package-local generated Python modules into generated JSON artifacts.

## Follow-Up Candidates

| Candidate | Why not finished in #460 | Owner |
| --- | --- | --- |
| Unship or opt-in install of memory `routing-feedback.md` | Implemented by #472; ordinary installs no longer seed the note, while route-review and hygiene still support repos that create it. | #472 |
| Planning optional payload shrinkage | Existing classification already names optional docs, review/intake, and skills as candidates; #450 should continue through #467/#469/#471 before larger removal decisions. | #450 and existing follow-ups |
| Historical audit noise while continuing parent lanes | Dogfooding still sees archived child slices as promotion candidates until the active continuation is clear. | #470 |

## Proof Surfaces

- `tests/test_packaging.py`
- `tests/test_workspace_packaging.py`
- `packages/planning/tests/test_packaging.py`
- `packages/memory/tests/test_packaging.py`
- `packages/memory/tests/test_installer.py`
- `pyproject.toml`
- `packages/planning/pyproject.toml`
- `packages/memory/pyproject.toml`

