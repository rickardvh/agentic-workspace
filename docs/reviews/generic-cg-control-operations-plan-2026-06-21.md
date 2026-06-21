# Generic CG Control Operations Plan

Date: 2026-06-21

Issues: #1659, #1649, #1655

## Boundary

Command-generation should own generic renderers, primitive machinery, conformance runners, and host-neutral operation control/dataflow. Agentic Workspace should own product-specific operation contracts, runtime primitive implementations, integration seams, proof routing, and generated output ownership.

This plan does not move AW semantics into CG. It identifies the next generic shapes needed before more accepted runtime boundaries can be removed.

## Current CG Support

Existing CG support already covers the simple cases:

- `runtime_handler`
- `function_call`
- `conditional_function_call`
- `generated_target_root_resolve`
- `runtime_emit`
- `sectioned_payload_select`
- `json_resource_load`
- `json_output_with_source_fallback`
- `payload.assemble`
- `output.emit`

This explains why the simple front-door/wrapper family was exhausted by earlier work. The remaining #1649 boundaries need host-neutral projection/view mechanics, not more AW-specific adapters.

## Candidate Generic Shapes

| Candidate | CG owns | Host owns | AW pressure example | Host-neutral fixture requirement |
| --- | --- | --- | --- | --- |
| `record.project` or `payload.project` | Dot-path projection from declared input payloads; missing-path reporting. | Which payload exists and which selectors matter. | `_select_workspace_operation_fields` after AW constructs a config payload. | A synthetic package projects fields from a generic inventory payload. |
| `view.render` | Rendering JSON/text from a declared view spec. | View spec contents, labels, ordering, and domain meaning. | `_emit_workspace_operation_output` text cases for selected/compact/tiny packets. | A synthetic package renders a product-neutral status payload. |
| `output.emit` view extension | Format dispatch and serialization using host-provided view specs. | Semantic payload construction and view policy. | Workspace config/defaults/prompt/system-intent output paths. | A synthetic command emits JSON and text from one host-neutral operation. |
| `control.switch` | Branch over declared enum/status values. | Enum definitions and semantic consequences. | Summary/report section routing after AW declares section ids. | A synthetic operation switches over neutral mode labels. |
| `transaction.envelope` | Plan/apply/dry-run scaffolding and provenance hook slots. | Mutation safety, conflict policy, and provider/domain semantics. | Lifecycle mutation adapters in #1656, not #1655 first slice. | A synthetic filesystem plan with host-owned safety hook. |

## Forbidden Shortcuts

- No arbitrary expressions.
- No embedded Python or JavaScript.
- No unbounded loops.
- No AW command names, filenames, issue ids, or policy language in CG primitive definitions or CG tests.
- No runtime imports of `command_generation` into generated AW packages.

## Next Implementation Slice

The first useful CG implementation should be `record.project` or a small `view.render` primitive, because it directly targets #1655 without touching mutation/provider semantics.

Acceptance for that CG slice:

- One host-neutral synthetic fixture in CG.
- One AW pressure mapping in this repo.
- Generated runtimes remain self-contained.
- AW consumes the primitive only through declared IR metadata and regenerated artifacts.
- The accepted runtime boundary count drops only after the generated operation consumes the new source of truth.

## Current Decision

No CG code change is made in this AW PR because the current branch can enforce the non-enum keyword routing guardrail and record the exact #1655/#1659 disposition without requiring a partially designed CG primitive. The next implementation PR should start in `command-generation` if it attempts to retire `_emit_workspace_operation_output` or `_select_workspace_operation_fields`.
