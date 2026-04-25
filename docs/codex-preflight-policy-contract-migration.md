# Codex migration: wire in `preflight_policy.json`

## Context

PR #304 extracts declarative command, option, module, policy, and surface metadata into checked-in contract JSON. One remaining gap from review is preflight policy: `HIGH_RISK_COMMANDS`, `PREFLIGHT_TOKEN_PREFIX`, and `DEFAULT_PREFLIGHT_MAX_AGE_SECONDS` still live inline in `src/agentic_workspace/cli.py`.

This branch now includes the missing contract files:

- `src/agentic_workspace/contracts/preflight_policy.json`
- `src/agentic_workspace/contracts/schemas/preflight_policy.schema.json`

The goal is to make preflight policy manifest-backed while preserving current runtime behavior.

## Intended wiring

### 1. Add a manifest accessor

In `src/agentic_workspace/contract_tooling.py`, add:

```python
def preflight_policy_manifest() -> dict[str, Any]:
    return load_contract_json("preflight_policy.json")
```

### 2. Load the manifest in `cli.py`

In `src/agentic_workspace/cli.py`, import the accessor:

```python
from agentic_workspace.contract_tooling import (
    ...,
    preflight_policy_manifest,
)
```

Then load it near the other import-time manifests:

```python
_PREFLIGHT_POLICY = preflight_policy_manifest()
```

Replace the inline preflight constants with manifest-backed values:

```python
HIGH_RISK_COMMANDS = frozenset(str(command) for command in _PREFLIGHT_POLICY["high_risk_commands"])
PREFLIGHT_TOKEN_PREFIX = str(_PREFLIGHT_POLICY["token"]["prefix"])
DEFAULT_PREFLIGHT_MAX_AGE_SECONDS = int(_PREFLIGHT_POLICY["default_max_age_seconds"])
_PREFLIGHT_STRICT_GATE_POLICY = _PREFLIGHT_POLICY["strict_gate"]
```

### 3. Keep parser behavior unchanged

`src/agentic_workspace/contracts/cli_option_groups.json` already uses:

```json
"default_ref": "preflight_policy.default_max_age_seconds"
```

The existing `_resolve_option_default()` implementation may continue returning `DEFAULT_PREFLIGHT_MAX_AGE_SECONDS` for that ref once the constant is manifest-backed.

### 4. Optional: manifest-back error strings

For a smaller first wiring slice, only move the constants above. For fuller extraction, also replace hard-coded preflight error strings in `_enforce_preflight_gate()` with `_PREFLIGHT_STRICT_GATE_POLICY` fields:

- `missing_token_error`
- `invalid_token_error`
- `non_positive_max_age_error`
- `future_token_error`
- `stale_token_error_template`

The stale-token template expects `{age_seconds}` and `{max_age_seconds}`.

### 5. Add contract validation and parity checks

In `scripts/check/check_contract_tooling_surfaces.py`:

1. Import `preflight_policy_manifest`.
2. Add schema validation:

```python
(
    "preflight policy manifest",
    _validate(preflight_policy_manifest(), "preflight_policy.schema.json"),
)
```

3. Add parity checks:

```python
preflight_policy = preflight_policy_manifest()
if sorted(cli.HIGH_RISK_COMMANDS) != sorted(preflight_policy["high_risk_commands"]):
    checks.append(("preflight policy parity", ["high-risk command set drifted from preflight_policy.json"]))
if cli.PREFLIGHT_TOKEN_PREFIX != preflight_policy["token"]["prefix"]:
    checks.append(("preflight policy parity", ["preflight token prefix drifted from preflight_policy.json"]))
if cli.DEFAULT_PREFLIGHT_MAX_AGE_SECONDS != preflight_policy["default_max_age_seconds"]:
    checks.append(("preflight policy parity", ["default preflight max age drifted from preflight_policy.json"]))
```

If error strings are also wired through the manifest, add matching parity checks for `_PREFLIGHT_STRICT_GATE_POLICY`.

### 6. Add inventory entry

In `src/agentic_workspace/contracts/contract_inventory.json`, add an area entry:

```json
{
  "area": "preflight_policy",
  "classification": "declarative",
  "owner_surface": "src/agentic_workspace/contracts/preflight_policy.json",
  "consumers": [
    "agentic_workspace.cli:_enforce_preflight_gate",
    "agentic_workspace.cli:build_parser",
    "scripts/check/check_contract_tooling_surfaces.py"
  ],
  "notes": "High-risk command gating, preflight token format, token freshness defaults, and strict-gate messages are manifest-backed instead of inline Python constants."
}
```

### 7. Run checks

Expected validation commands:

```bash
uv run pytest tests/test_workspace_cli.py -q
uv run pytest tests/test_contract_tooling.py -q
uv run python scripts/check/check_contract_tooling_surfaces.py
uv run ruff check src tests scripts
```

## Expected result

After wiring, the PR should no longer have the review gap where preflight policy is partly declarative only by reference. The CLI behavior should remain unchanged, but the preflight policy values should be owned by `preflight_policy.json` and validated by `preflight_policy.schema.json`.
