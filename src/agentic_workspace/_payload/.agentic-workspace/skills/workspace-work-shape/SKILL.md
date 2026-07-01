---
name: workspace-work-shape
description: Reference the direct, bounded, lane, and epic vocabulary only when workspace-intent-discovery or compact routing needs work-shape details interpreted.
---

# Workspace Work Shape Reference

Do not use this as an independently invoked subskill. `workspace-intent-discovery` owns the merged intent/shape procedure after the main AW operating skill routes there.
When AW is enabled, this reference preserves the same routed workflow boundary as the main skill; it does not make work-shape judgment a bypass around startup, planning or proof gates.

This reference exists so compact output, reviews, or issue discussions can name the work-shape vocabulary without reloading the full intent protocol.

## Vocabulary

- `direct`: target and proof are obvious; answer or edit with the narrowest proof and no durable artifact unless routed.
- `bounded`: finite implementation with meaningful proof, continuation, or issue-linkage risk; use compact implement/proof routing.
- `lane`: multi-slice or issue-lane work; checked-in Planning state owns sequencing before implementation.
- `epic`: multiple lanes, high assurance, or unclear decomposition; shape before implementation.

## Reference Output

When this reference is explicitly requested, report the inferred intended outcome, work shape, why that shape fits, the first repo-visible surface to inspect or update, satisfaction evidence, required next route, and whether Planning state is optional, recommended, or required.
