# Lifecycle, Configuration, and Recovery Contract

This contract defines how the workspace is initialized, configured, and recovered from drift or failure.

## 1. Initialization Lifecycle

### Default Behavior
- `agentic-workspace init`: Bootstraps the repo with selected modules (`memory`, `planning`, or `full`).
- [`.agentic-workspace/docs/installer-behavior.md`](installer-behavior.md) for payload resolution and development mirroring rules.
- [`.agentic-workspace/docs/capability-aware-execution.md`](capability-aware-execution.md) for how the installer configures model-specific execution.
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
- **`.agentic-workspace/config.toml`**: Repo-owned source of truth for module sources, update intent, and shared lifecycle defaults.
- **`.agentic-workspace/config.local.toml`**: Optional local override for machine-local invocation, capability/cost posture, and agent-posture settings.
- **`.agentic-workspace/`**: Product-managed module state. This directory should not be edited directly; use the owning package or CLI.

### Configuration Fields
- `default_preset`: The default module set for `init`.
- `agent_instructions_file`: The filename for the canonical startup entrypoint (default `AGENTS.md`).
- `optimization_bias`: The effective output posture (e.g. `agent-efficiency`, `token-saving`).

---

## 3. Environment Recovery

When normal work is blocked by repo-state ambiguity, interrupted bootstrap, or environment drift:

### Recovery Path
1. **Inspect State**: Run `agentic-workspace status --target ./repo` and `agentic-workspace doctor --target ./repo`.
2. **Reconfirm Defaults**: Query `agentic-workspace defaults` and `agentic-workspace config --target ./repo`.
3. **Refresh Contracts**: Run `agentic-workspace upgrade --target ./repo --dry-run --format json`, resolve review items, then run `agentic-workspace upgrade --target ./repo --format json`.
4. **Verify**: Run `agentic-workspace doctor --target ./repo --format json`.
5. **Package-local fallback**: Use module bootstrap CLIs only for package-local debugging or when the root command cannot run.

### Interrupted Handoff
- **`llms.txt`**: Canonical external-agent entry surface.
- **`.agentic-workspace/bootstrap-handoff.md`**: Post-bootstrap next-action brief when judgment is still needed.
- **`.agentic-workspace/bootstrap-handoff.json`**: Compact structured sibling to the handoff brief.

---

## 4. Relationship to Tooling

- `agentic-workspace config --target ./repo --format json`: Inspect effective posture and configuration; use `--select <field.path>` when one field is needed or `--verbose` for broad diagnostics.
- `agentic-workspace doctor --target ./repo`: Identify and remediate environment drift.
- `agentic-workspace status --target ./repo`: Check module and repo-state health.
- `agentic-workspace upgrade --target ./repo --dry-run --format json`: Ordinary safe first step for host-repo updates.
