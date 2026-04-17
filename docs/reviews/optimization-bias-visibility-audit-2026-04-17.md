# Optimization Bias Visibility Audit

Date: 2026-04-17

## Question

Where is `optimization_bias` currently visible, where does it already affect behavior, and where is it still absent from ordinary recovery?

## Inventory

### Present Today

- Repo config and effective config:
  - `agentic-workspace.toml`
  - `agentic-workspace config --target ./repo --format json`
- Shipped selector/default contract:
  - `agentic-workspace defaults --section optimization_bias --format json`
  - [`docs/workspace-config-contract.md`](../workspace-config-contract.md)
- Shared workspace reporting:
  - `agentic-workspace report --target ./repo --format json`
  - rendered report text through `output_contract`
- Design/doctrine references:
  - [`docs/design-principles.md`](../design-principles.md)
  - [`docs/reporting-contract.md`](../reporting-contract.md)

### Behavior Already Shaped

- rendered report density
- rendered human-facing report style
- durable residue density or style when canonical truth stays unchanged

### Still Missing In Ordinary Recovery

- The compact recovery contract does not currently surface the effective repo bias directly.
- The front-door route does not yet make the output posture feel like part of normal startup or recovery rather than a secondary config/report detail.
- The allowed-versus-invariant surface boundary still lives mostly across prose rather than one compact surface classification.

## Most Important Gaps

1. Ordinary recovery can miss the effective repo posture unless it separately inspects config or report.
2. The surface boundary is real but scattered.
3. The umbrella integration issue should close only after recovery visibility and the surface boundary are both explicit.

## Recommended Follow-Through

- `#152`: expose effective optimization bias in one compact normal recovery path.
- `#153`: define one compact allowed/invariant surface classification for optimization bias.
- `#148`: after those land, tighten front-door docs so the bias reads as normal repo posture rather than an implemented side setting.

## Decision

Treat this audit as complete once the checked-in review exists and the follow-on work stays owned by the active execplan rather than chat.
