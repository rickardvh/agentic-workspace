# Package-Owned Assumptions Audit

Date: 2026-06-22

Issues: #1670, #1668

## Scope

Reviewed current built-in assumptions that could accidentally remain package-owned host policy, repo-specific routing, or hidden workflow authority. The checked-in inventory is a migration ledger at `docs/maintainer/package-owned-assumptions-inventory.json`.

## Result

- Created a typed maintainer inventory for current built-in assumptions and registered it in the structured file inventory.
- Added a contract-tooling check that fails on incomplete migration rows, unknown migration status labels, missing evidence, or unresolved `remove` entries.
- Split `_emit_workspace_operation_output` into named AW-owned output policy helpers while leaving generated-owned JSON and selected-output mechanics outside the retained package policy boundary.
- Updated Python runtime and operation execution inventories so the remaining hand-owned output dispatcher is justified as a narrowed policy dispatcher, not generic output rendering.

## Agent Judgment

The inventory is not runtime routing authority and is not the desired end state. It names assumptions currently built into code, repo-local aids, manifests, or maintainer fixtures so future work can move them to config, contracts, external intent, planning state, learned Memory, or remove them. The agent owns judgment about whether the listed assumption is still needed and where it belongs.

## Verification Decision

The added tests prove the new inventory validator accepts classified entries and rejects unclassified or unauthorised entries. They are narrow contract-tooling tests rather than broad workflow regressions. They should remain until the inventory contract is either replaced by a schema-backed contract or absorbed into a broader maintainer-surface conformance check.

Memory routing was checked for this work. The relevant guidance says Memory is for anti-rediscovery knowledge and checked-in docs remain the canonical documentation layer, so this audit is owned by maintainer docs and contracts rather than a new Memory note.
