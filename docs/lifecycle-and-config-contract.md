# Lifecycle, Configuration, and Recovery Contract

This contract defines how the workspace is initialized, configured, and recovered from drift or failure.

## 1. Initialization Lifecycle

### Default Behavior
- `agentic-workspace init`: Bootstraps the repo with selected modules (`memory`, `planning`, or `full`).
- **User Intent**: The selected preset (`--preset`) determines the initial module set and configuration.
- **Mode Selection**: The CLI automatically chooses a lifecycle mode (Clean install, Conservative adopt, or High-ambiguity adopt) based on existing repo state.

### High-Ambiguity Signals
Reconciliation is required when:
- Multiple root startup files (e.g. `AGENTS.md`, `llms.txt`) overlap or conflict.
- Partial or placeholder state exists in module directories.
- Existing workflow surfaces conflict with product-managed contracts.

---

## 2. Workspace Configuration

### Authority
- **`agentic-workspace.toml`**: Repo-owned source of truth for module sources, update intent, and shared lifecycle defaults.
- **`agentic-workspace.local.toml`**: Optional local override for capability/cost posture and agent-posture settings.
- **`.agentic-workspace/`**: Product-managed module state. This directory should not be edited directly; use the owning package or CLI.

### Configuration Fields
- `default_preset`: The default module set for `init`.
- `agent_instructions_file`: The filename for the canonical startup entrypoint (default `AGENTS.md`).
- `optimization_bias`: The effective output posture (e.g. `agent-efficiency`, `token-saving`).

---

## 3. Environment Recovery

When normal work is blocked by repo-state ambiguity, interrupted bootstrap, or environment drift:

### Recovery Path
1. **Inspect State**: Run `agentic-workspace status` and `agentic-workspace doctor`.
2. **Reconfirm Defaults**: Query `agentic-workspace defaults` and `config`.
3. **Refresh Contracts**: If the issue is package-contract freshness, run `uv run agentic-<module>-bootstrap upgrade`.
4. **Narrow Validation**: Run the narrowest proving lane (e.g. `pytest tests/test_workspace_cli.py`).

### Interrupted Handoff
- **`llms.txt`**: Canonical external-agent entry surface.
- **`.agentic-workspace/bootstrap-handoff.md`**: Post-bootstrap next-action brief when judgment is still needed.
- **`.agentic-workspace/bootstrap-handoff.json`**: Compact structured sibling to the handoff brief.

---

## 4. Relationship to Tooling

- `agentic-workspace config --target ./repo --format json`: Inspect effective posture and configuration.
- `agentic-workspace doctor --target ./repo`: Identify and remediate environment drift.
- `agentic-workspace status --target ./repo`: Check module and repo-state health.
