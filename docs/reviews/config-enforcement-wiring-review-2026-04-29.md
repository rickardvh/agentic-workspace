# Config Enforcement Wiring Review

Date: 2026-04-29

## Scope

Review `.agentic-workspace/config.toml`, `.agentic-workspace/config.local.toml`, the workspace config schema, and the CLI/report consumers by actual operational enforcement rather than declared intent.

## Current enforcement model

The loader is the real enforcement point. It rejects malformed core structure and invalid enum values, but most workflow and posture fields are intentionally routed as machine-readable guidance for agents and reports.

The JSON schema now mirrors that model: it validates supported field shapes, includes the supported `[system_intent]` section, and treats unsupported fields as warning-tolerated rather than hard-invalid.

## Strongly wired fields

- `schema_version`: hard config contract gate.
- `workspace.default_preset`: validated and used by setup/init/module selection paths.
- `workspace.agent_instructions_file`: validated and used by generated startup adapter selection.
- `workspace.workflow_artifact_profile`: validated and used by adapter and handoff posture.
- `workspace.advanced_features`: validated and used to expose optional advanced surfaces.
- `workspace.cli_invoke` in local config: validated and used for copyable local commands.
- `update.modules.<module>.source_type/source_ref/source_label`: validated and used by lifecycle/source metadata.
- `system_intent.sources/preferred_source`: validated and used by config/report/system-intent routing.

## Weakly wired fields

- `workspace.improvement_latitude`: shapes self-improvement/report posture, but does not directly gate which actions the package recommends or requires.
- `workspace.optimization_bias`: affects report rendering posture, but only lightly influences selector choice or payload size.
- `workflow_obligations.*`: structure is enforced and obligations are surfaced, but matching and command execution remain agent-dependent.
- `update.modules.*.recommended_upgrade_after_days`: validated metadata, but not a strong lifecycle freshness decision.
- Local `runtime`, `handoff`, `safety`, and `delegation_targets`: validated and queryable, but mostly descriptive. They do not yet strongly alter delegation packets, closeout trust, or proof burden.
- `local_memory.enabled/path`: represented clearly as local and advisory, but not yet deeply integrated into relevance-based recall.

## Improvement opportunities

1. Add an enforcement-class field to config/report output.
   Each config field should expose one of `hard`, `operational`, `advisory`, or `local-advisory`, with a short `used_by` list. This would make weak enforcement explicit to agents without requiring schema/code inspection.

2. Route weak fields into existing selectors before adding features.
   `improvement_latitude`, `optimization_bias`, workflow obligations, and local delegation posture should first influence `report`, `proof`, `preflight`, and `skills` outputs, because those are already first-contact machine-readable surfaces.

3. Make workflow obligation matching auditable.
   Reports should explain why an obligation matched or did not match current work, including the observed scope tags and the evidence source. That would reduce agent guesswork without requiring automatic command execution.

4. Use local delegation posture to shape handoff packets and closeout trust.
   Keep local targets advisory, but wire weak/strong target signals into bounded delegation guidance, expected proof burden, and lower-trust closeout recommendations.

5. Let optimization bias select verbosity budgets.
   The field should influence default report selector hints and payload density more directly while preserving the same machine truth behind explicit selectors.

6. Promote freshness metadata into lifecycle recommendations.
   `recommended_upgrade_after_days` should produce a clearer `fresh`, `stale`, or `unknown` lifecycle status that points to existing `upgrade --dry-run` actions.

## Guardrails

- Do not turn local config into shared repo authority.
- Do not make advisory fields silently execute commands.
- Prefer strengthening existing query outputs over adding new commands.
- Keep schema and loader behavior aligned: if runtime accepts with warnings, schema should not claim hard rejection.
- When a field remains advisory, expose that fact directly in machine-readable output.

