# Summary Status Preflight Action-Shape Audit

## Purpose

This note records the bounded #1761 review of summary, status-like, and preflight caution outputs after #1759.

## Disposition

| Caution class | Surface | Disposition | Action effect |
| --- | --- | --- | --- |
| Closeout trust inspection | `summary --select closeout_trust_inspection` and completion/status summary projections | action-shaped and selector-backed | `closeout_trust_inspection.action_effect` distinguishes required-before-claim closeout residue from advisory clear status and names the report command that resolves the condition. |
| Planning surface health warnings | `summary` planning surface health | retained as status-like diagnostics | Warning classes already include concrete repair detail; future slices should move individual warnings behind action effects only when they change action or closure permission. |
| Strict preflight token gate | strict preflight enforcement | retained as hard action gate | Token failures block guarded commands before execution; this is an action blocker, not a claim-only caution. |
| Lifecycle/status setup warnings | `status` / `doctor` lifecycle summaries | leave for local/installed-state tranche | These warnings overlap #1762 and should be tightened with invocation and installed-state compatibility semantics instead of mixed into #1761. |

## Follow-up Boundary

This audit does not add a warning dashboard. Summary closeout trust is the changed emitted caution in this slice; future summary/status/preflight slices should keep the minimum contract visible: force, allowed action, blocked claim/action, claim boundary, and resolution selector or command.
