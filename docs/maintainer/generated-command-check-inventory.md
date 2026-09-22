# Generated Command Check Inventory

The checked source is `src/tooling/contracts/generated_command_check_inventory.json`.

This inventory complements the `command-generation` target matrix. It does not redefine generic Python or TypeScript target behaviour. AW keeps checks for AW-owned operation contracts, host runtime boundaries, temporary runtime semantic exceptions, generated artefact freshness, release/pinning posture, and transitional host semantics.

## Owner Split

| Owner | Keep in AW | Delegate or demote |
| --- | --- | --- |
| Agentic Workspace | Operation input projection, host runtime inventory, runtime semantic exception registry, generated artefact freshness, release provenance, operation conformance parity, transitional host primitive usage | None |
| command-generation | None | Generic target-extension contracts, primitive executor baseline, generic TypeScript target baseline, retired AW duplicate target regressions |

## Required Guardrails

- Generic target-baseline checks must not be marked `keep-in-aw`.
- AW-specific checks must remain `keep-in-aw`.
- Obsolete generic duplicate checks must stay `remove-from-aw`, must list the exact retired ordinary check symbols, and must be rejected by static proof if those symbols reappear under AW-owned ordinary `tests/` or `src/tooling/check/` paths.
- Primitive conformance remains invokable from AW proof commands, but the cases are owned by `command-generation`.
- Stable AW generated behaviour belongs in operation conformance or an AW host/runtime inventory, not in one-off ordinary regressions.

## Report Surface

Use:

```powershell
uv run python src/tooling/check/check_generated_command_packages.py --python-completion-blockers --format json
```

The payload includes `generated_command_check_inventory`, with counts by class and disposition, AW-kept and delegated check ids, and the retired ordinary check ids that must remain absent. For `remove-from-aw`, the disposition means removed from AW-owned ordinary checks, not merely inventoried as removable. Delegated conformance commands remain valid proof lanes.
