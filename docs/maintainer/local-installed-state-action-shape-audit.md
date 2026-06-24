# Local Installed-State Action-Shape Audit

## Purpose

This note records the bounded #1762 review of local state and installed-state compatibility cautions after #1759.

## Disposition

| Caution class | Surface | Disposition | Action effect |
| --- | --- | --- | --- |
| Installed-state compatibility | `start --select installed_state_compatibility` and report installed-state sections | action-shaped and selector-backed | `installed_state_compatibility.action_effect` distinguishes execution-blocking CLI drift from claim-only payload freshness drift and clean advisory compatibility. |
| Invoked CLI identity | `invoked_cli_identity` selectors | retained as evidence | The identity packet remains an input to compatibility decisions; it should not independently block work without the compatibility packet. |
| Payload provenance drift | installed-state compatibility payload | claim blocker | Missing, invalid, stale, or older payload provenance blocks installed-state freshness claims until the upgrade dry-run/sync check is run, while bounded work may continue with the repo-local invocation. |
| Stale installed selector risk | AGENTS adapter and CLI compatibility remediation | retained as hard safety rule | Agents must keep using the effective repo-local invocation; stale bare commands remain actionable through compatibility remediation rather than generic warnings. |
| Adapter/generated-surface trust facts | generated-surface trust and installed-state packets | covered by stronger packets | Generated freshness stays behind `generated_surface_trust` when changed paths are generated; installed-state only carries repo payload freshness and adapter compatibility boundaries. |

## Follow-up Boundary

This audit does not replace install, update, or doctor lifecycle models. Future local-state slices should keep the minimum contract visible: force, allowed action, blocked claim/action, claim boundary, and resolution selector or command.
