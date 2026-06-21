# Workspace Report and Context Runtime Disposition

Date: 2026-06-21

Issues: #1655, #1649, #1659

## Purpose

This review narrows the workspace report/context/output part of the runtime-boundary decomposition lane. It uses the current exact-symbol inventory instead of recounting from source code by hand.

Source command:

```powershell
uv run python scripts/check/check_generated_command_packages.py --python-completion-blockers --format json
```

Current baseline:

- 75 accepted runtime symbols.
- 19 workspace package runtime boundaries.
- 1 accepted output-emission symbol: `agentic_workspace.workspace_runtime_primitives._emit_workspace_operation_output`.
- The high-confidence #1655 symbols `_emit_workspace_operation_output` and `_select_workspace_operation_fields` are still accepted hand-owned boundaries.

## Disposition Table

| Symbol | Current audit classification | Proposed next owner | Semantic owner after split | Exact proof/update required | Remaining hand-owned rationale |
| --- | --- | --- | --- | --- | --- |
| `_emit_workspace_operation_output` | `generic-cg-control` | split | AW owns prompt/system-intent/config/defaults text policy until it is declared as view metadata. CG can own JSON emission and generic selected/tiny/compact answer rendering. | Add a host-neutral output/view primitive or declarative view spec in CG, consume it from AW IR, regenerate, then remove the accepted boundary entry. | Current generated code already handles JSON and several generic packet shapes, but falls back to AW for prompt, system-intent, config, defaults, and text emission policy. |
| `_select_workspace_operation_fields` | `generic-cg-control` | split | AW owns config payload construction and tiny/compact config view policy until those views are declared. CG can own selector projection once the payload exists. | Add declared view policy for config tiny/compact/select or a generic projection operation that consumes host-provided payload and view metadata; regenerate and remove boundary entry. | It currently mixes payload construction from `WorkspaceConfig` with projection/view shaping. |
| `_run_report_combined_adapter` | `declarative-policy` | split | AW owns report section payload semantics; CG may own section dispatch and selector routing. | Declare section routing/view metadata and prove report CLI parity before moving. | Current function assembles multiple AW semantic report packets and live module state. |
| `_run_summary_report_adapter` | `declarative-policy` | split | AW/Planning owns closeout, active state, residue, and intent-satisfaction semantics; CG may own selected output and section projection. | Add section/view metadata and focused summary CLI tests. | Summary is an operating-loop semantic surface, not only a renderer. |
| `_run_lifecycle_report_adapter` | `declarative-policy` | split | AW owns module lifecycle/readiness interpretation; CG may own generic report envelope and output projection. | Add lifecycle report view metadata and prove module status parity. | It reads live module reports and readiness facts. |
| `_load_workspace_operation_config` | `declarative-policy` | declared AW policy plus semantic primitive | AW owns config layering and compatibility semantics; CG may own generic load-step wiring. | Separate config load primitive from view projection and keep config semantics inventoried. | Config layering is product policy, not generic data loading. |
| `_render_workspace_operation_prompt` | `declarative-policy` | declared AW policy plus semantic primitive | AW owns prompt/adopt/uninstall/upgrade semantics; CG may own generic template dispatch when prompt policy is declared. | Declare prompt template routing and prove prompt command parity. | Prompt output is package workflow policy. |
| `_resolve_workspace_operation_selection` | `declarative-policy` | declared AW policy plus semantic primitive | AW owns module selection/default semantics; CG may own argument-to-selection step wiring. | Declare selection enum/default policy or keep as exact semantic primitive. | Selection affects installed modules and command safety. |
| `_run_start_context_adapter` | `mixed-policy-plus-kernel` | AW semantic primitive | AW owns next-safe-action, issue grounding, memory packet, proof posture, and startup judgment. | Only split after named smaller semantic payload functions exist with parity tests. | Startup is the main AW operating-loop judgment surface. |
| `_run_implement_context_adapter` | `mixed-policy-plus-kernel` | AW semantic primitive with possible projection split | AW owns changed-path interpretation, proof selection, memory/capture pressure, and workflow sufficiency. | Split only projection/output after semantic payload remains named and exact. | Implementation context affects action safety. |
| `_run_setup_guidance_adapter` | `mixed-policy-plus-kernel` | AW semantic primitive with possible projection split | AW owns setup guidance semantics; CG may own generic output projection later. | Add setup guidance view metadata and focused tests. | Setup guidance is repo/product interpretation rather than pure rendering. |

## #1659 CG Support Needed

The current CG/AW support already includes `function_call`, `conditional_function_call`, `runtime_emit`, generated local overrides, `sectioned_payload_select`, and `json_output_with_source_fallback`. That is enough for simple wrappers but not enough to honestly retire the two #1655 high-confidence workspace symbols.

The smallest generic additions worth considering are:

- `record.project` or `payload.project` over declared dot-path selectors.
- `view.render` over host-owned view specs for tiny/compact/text forms.
- `output.emit` extension that can use declared view renderers without importing host runtime code.

Each primitive needs a host-neutral CG fixture and an AW pressure example. CG must not contain AW command names, issue terms, filenames, or policy language.

## Implementation Decision

No runtime boundary is removed by this review alone. The useful implementation in this slice is the #1663 guardrail: new keyword/string-table routing policy cannot silently enter the runtime while #1659/#1655 design work proceeds.

Closing #1655 from this document alone would be premature. A later implementation PR should either:

1. add the missing generic CG projection/view primitive and consume it from AW IR, or
2. prove that an existing CG primitive can retire `_emit_workspace_operation_output` or `_select_workspace_operation_fields` without hiding AW semantics.

## Proof

Required checks for this artifact:

```powershell
uv run python scripts/check/check_contract_tooling_surfaces.py --quiet-success
uv run python scripts/check/check_generated_command_packages.py --python-completion-blockers --format json
```
