# Post-Generation CLI and Lifecycle Boundary Review

Date: 2026-04-26

Issue: #370

Purpose: verify the current command-authority boundary after the generated-adapter and lifecycle-readiness lanes. This is evidence/history, not ordinary startup input.

## Summary

The generated-adapter lane now has two generated read-only command surfaces:

- root `agentic-workspace defaults`
- package `agentic-planning-bootstrap status`

Those generated surfaces are backed by `src/agentic_workspace/contracts/command_adapter_generation.json`, generated output files, no-direct-edit headers, freshness checks, and black-box conformance checks. Runtime primitive behavior remains hand-owned.

Most command/interface truth is still hand-authored or manifest-backed but not generated. That is acceptable for the current migration stage, but it means the next product-compression work should reduce visible startup and authoring burden rather than start broad lifecycle generation.

## Generated Or Mechanically Assembled Surfaces

| Surface | State | Authority |
| --- | --- | --- |
| `agentic-workspace defaults` | generated root adapter | `command_adapter_generation.json` plus `operations/defaults.report.json` |
| `agentic-planning-bootstrap status` | generated package adapter dispatch | `command_adapter_generation.json` plus `operations/planning.status.report.json` |
| root `agentic-workspace` parser | manifest-backed, not fully generated | `cli_commands.json` and `cli_option_groups.json` own visible command shape |
| generated adapter files | derived output | `scripts/generate/generate_command_adapters.py`; direct edits are forbidden |

The check path is already present: `scripts/check/check_contract_tooling_surfaces.py` validates generated output freshness, contract parity, and generated adapter metadata.

## Remaining Hand-Authored Interface Authority

| Surface | Remaining authority |
| --- | --- |
| root command dispatch outside `defaults` | hand-authored runtime dispatch in `src/agentic_workspace/cli.py` |
| root lifecycle commands | manifest/operation contracts exist, but lifecycle generation is deferred |
| planning package commands other than `status` | argparse shape remains hand-authored in `packages/planning/src/repo_planning_bootstrap/cli.py` |
| memory package commands | argparse shape and handler routing remain hand-authored in `packages/memory/src/repo_memory_bootstrap/cli.py` |

This is not drift by itself. The current contract boundary says generated adapters own parser/usage/dispatch wiring for selected surfaces; runtime primitives and live inspection stay implementation-owned.

## Lifecycle Eligibility

`src/agentic_workspace/contracts/lifecycle_generation_readiness.json` admits read-only `doctor`/`status` style lifecycle surfaces as future generation candidates and defers mutation/destructive commands.

| Lifecycle surface | Decision |
| --- | --- |
| `doctor`, `status` | eligible read-only candidates after output contracts are explicit |
| `install`, `init`, `adopt`, `upgrade` | deferred mutation surfaces |
| `uninstall` | deferred destructive surface |

Dry-run/apply planning, deletion safeguards, verification, local-only preservation, and ownership refusal remain runtime primitive concerns.

## Runtime Primitive Ownership

Runtime implementation remains intentionally hand-owned for:

- live workspace and module inspection
- lifecycle planning and application
- filesystem mutation and deletion safeguards
- local-only state preservation
- payload assembly and detailed diagnostics
- planning archive/promote mutation workflows
- memory sync, routing, and search behavior

Generated adapters may route to these primitives; they should not embed the behavior.

## Next Simplification Target

Next concrete target: #371, first-contact adapter compression.

Reason: the ordinary startup path is the visible product shape most likely to affect new-agent entry cost. `llms.txt`, `tools/AGENT_QUICKSTART.md`, and `tools/AGENT_ROUTING.md` are already thin, but #371 should verify renderer coverage and compress or demote at least one remaining duplicated adapter path while preserving weak-agent compatibility.

Do not start lifecycle adapter generation next. The lifecycle readiness baseline is useful, but product compression currently benefits more from reducing first-contact surfaces than from adding generated lifecycle machinery.
