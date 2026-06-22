# Package-Owned Assumptions Audit

Date: 2026-06-22

Issues: #1670, #1668

## Scope

Reviewed current built-in assumptions that could accidentally remain package-owned host policy, repo-specific routing, or hidden workflow authority.

## Result

- Identified package-owned assumption candidates for direct migration into their proper authority surfaces.
- Split `_emit_workspace_operation_output` into named AW-owned output policy helpers while leaving generated-owned JSON and selected-output mechanics outside the retained package policy boundary.
- Updated Python runtime and operation execution inventories so the remaining hand-owned output dispatcher is justified as a narrowed policy dispatcher, not generic output rendering.

## Agent Judgment

This review note is not runtime routing authority and is not a maintained inventory. It records the audit context only; durable conclusions should move into config, contracts, external intent, planning state, learned Memory, or be removed. The agent owns judgment about whether an identified assumption is still needed and where it belongs.

## Verification Decision

The follow-up migration should prove direct ordinary-loop surfacing from the final authority homes, not from a package-owned assumptions inventory.

Memory routing was checked for this work. The relevant guidance says Memory is for anti-rediscovery knowledge and checked-in docs remain the canonical documentation layer, so this audit is owned by maintainer docs and contracts rather than a new Memory note.
