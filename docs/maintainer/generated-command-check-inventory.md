# Generated Command Check Inventory

The checked source is `src/agentic_workspace/contracts/generated_command_check_inventory.json`.

This inventory complements the `command-generation` target matrix. It does not redefine generic Python or TypeScript target behavior. AW keeps checks for AW-owned operation contracts, host runtime boundaries, generated artifact freshness, release/pinning posture, and transitional host semantics.

## Owner Split

| Owner | Keep in AW | Delegate or demote |
| --- | --- | --- |
| Agentic Workspace | Operation input projection, host runtime inventory, generated artifact freshness, release provenance, operation conformance parity, transitional host primitive usage | None |
| command-generation | None | Generic target-extension contracts, primitive executor baseline, generic TypeScript target baseline, retired AW duplicate target regressions |

## Required Guardrails

- Generic target-baseline checks must not be marked `keep-in-aw`.
- AW-specific checks must remain `keep-in-aw`.
- Obsolete generic duplicate checks must stay `remove-from-aw`.
- Primitive conformance remains invokable from AW proof commands, but the cases are owned by `command-generation`.
- Stable AW generated behavior belongs in operation conformance or an AW host/runtime inventory, not in one-off ordinary regressions.

## Report Surface

Use:

```powershell
uv run python scripts/check/check_generated_command_packages.py --python-completion-blockers --format json
```

The payload includes `generated_command_check_inventory`, with counts by class and disposition plus the AW-kept and delegated check ids.
