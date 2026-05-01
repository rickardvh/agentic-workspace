# Generated CLI Adapter High-Assurance Dogfooding Report

## Report Header

- Host repo: `agentic-workspace`
- Report date: `2026-05-01`
- Reporter / agent runtime: `agent`
- Package source: `source checkout on codex/issue-641-generated-cli-adapters`
- Installed preset/modules: `full; workspace, planning, memory`
- Run goal: `Implement #641 and child issues #642, #643, and #644 through the progressive generated-adapter maturity model.`
- Slice type: `active execplan`
- Assurance level: `high; active execplan .agentic-workspace/planning/execplans/generated-cli-progressive-maturity-issue-641.plan.json`

## Run Summary

- Requested outcome: Finish the single-source generated executable adapter migration foundation, implement child issues through progressive maturity, commit, push, and create a PR.
- What landed: Runtime-backed generated Python parser/dispatch for root `defaults`, Planning `status`, and Memory `status`; generated IR/schema support for parser `interface`; static checks that require generated Python routing before handwritten parsers; review documentation for the progressive maturity matrix.
- What did not land: Mutation-capable lifecycle adapters and full root read-only command expansion. Those remain intentionally below higher maturity because #642 and #643 require additional conformance before promotion.
- Closure decision: `routed follow-up`
- Residue destination: `planning, issue, docs`

## Assurance And Proof

- Required refs: `#641`, `#642`, `#643`, `#644`, `docs/reference/command-package-ir.md`, `.agentic-workspace/planning/execplans/generated-cli-progressive-maturity-issue-641.plan.json`
- Control gates or blockers: Generated files fresh, generated parser before handwritten parser, black-box conformance, full `make check`.
- Proof profiles selected: focused contract tooling, generated command package conformance, schema reference freshness, full package check, dogfooding closeout.
- Proof commands selected: `uv run pytest tests/test_contract_tooling.py -q`; `uv run python scripts/check/check_generated_command_packages.py --conformance --require-node`; `uv run python scripts/generate/generate_schema_reference.py --check`; `make check`; dogfooding closeout selectors.
- Proof commands executed: all selected commands passed.
- Waivers, skips, or unavailable proof: no waiver for required proof; Docker-specific generated package proof was not required because the active gate used local Node with `--require-node`.
- Missing evidence: CI result after PR creation.
- Trust state after proof: `usable`

## Touched Surfaces

| Surface | Owner | Why it changed | Host-private? |
| --- | --- | --- | --- |
| `src/agentic_workspace/contracts/command_package_ir.json` | workspace | Declare Python runtime-backed maturity and generated parser interface | no |
| `packages/command-generation/src/agentic_command_generation/generator.py` | workspace | Generate runtime-backed Python adapter packages | no |
| `src/agentic_workspace/cli.py` | workspace | Route generated parser/dispatch before handwritten parser for promoted commands | no |
| `packages/planning/src/repo_planning_bootstrap/cli.py` | planning | Route generated parser/dispatch for promoted package status command | no |
| `packages/memory/src/repo_memory_bootstrap/cli.py` | memory | Route generated parser/dispatch for promoted package status command | no |
| `scripts/check/check_generated_command_packages.py` | workspace | Enforce progressive maturity and generated-routing checks | no |
| `docs/reviews/generated-cli-progressive-maturity-2026-05-01.md` | docs | Record maturity matrix and remaining command lanes | no |
| `.agentic-workspace/planning/execplans/generated-cli-progressive-maturity-issue-641.plan.json` | planning | Active high-assurance execution authority | no |

## Friction Items

| Observation | Evidence | Likely owner | Product should absorb? | Recommendation | Follow-up target |
| --- | --- | --- | --- | --- | --- |
| High-assurance work initially began without an active execplan. | User interruption; summary later reported `active_count: 0` before plan creation. | product-general | yes | issue | `#645` |
| The package caught malformed execplan fields only after the plan was written. | `planning_record_schema_drift` warnings for `control_gates`, `threat_failure_aids`, and `durable_residue`. | successful behavior | no | preserve | none |
| Formatter drift exposed that generated Python output must itself be ruff-stable. | `make check` failed on `src/agentic_workspace/generated_cli_package/__init__.py`; fixed generator quoting. | product-general | yes | fix now | fixed in this branch |

## Operating-Cost Review

| Work shape | Required fields | Inferred or optional fields | Default output impact | Decision |
| --- | --- | --- | --- | --- |
| Low-risk direct task | No execplan unless scope widens. | Dogfooding note can stay compact. | none | keep |
| Medium-risk planned task | Active execplan with touched scope, proof commands, continuation owner. | Detailed control gates can remain selector-owned. | small | keep |
| High/critical task | Active execplan, adaptive assurance, control gates, proof report, closeout trust, reconcile, and dogfooding report. | Historical audit detail remains in full summary/report selectors. | small | keep |

## Privacy And Sensitivity

- Omitted host details: none; this is the package source checkout.
- Redactions or anonymization: none.
- Evidence that should stay in the host repo: command logs under `scratch/command-logs/`.

## Conversion To Focused Issues

- Created/used #642 for lifecycle dry-run and mutation generated-adapter migration.
- Created/used #643 for remaining root read-only command generated-adapter migration.
- Created/used #644 for Planning and Memory read-only command expansion.
- Created #645 for a guard or stronger route so broad high-assurance package work enters checked-in planning before implementation.
