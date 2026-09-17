<!-- GENERATED FILE: edit workspace_surfaces.json and rerun `make render-schema-reference`. -->
# Current Installed-Surface Catalogue

The public v1 host footprint is one Configuration-owned contract. Adoption, refresh, and removal use the same file set. Optional domain state is never established by adoption.

- Contract digest: `sha256:5ad14a52ecb9fa7569f03c68065fab7f293e23fc64a12b7e1366e5e036733b96`

| Surface | Ownership | Lifetime | Establish / refresh / remove | Consumer |
| --- | --- | --- | --- | --- |
| `.agentic-workspace/READING.json` | package-managed | adopted-host | `configuration.repository-adoption` | Repository-only source orientation bound to the ownership ledger |
| `.agentic-workspace/OWNERSHIP.toml` | package-managed | adopted-host | `configuration.repository-adoption` | Current source/lifetime declarations for runtime and repository-only readers |
| `.agentic-workspace/skills/REGISTRY.json` | package-managed | adopted-host | `configuration.repository-adoption` | Passive route and executable procedure declarations |
| `.agentic-workspace/skills/workspace-startup/SKILL.md` | package-managed | adopted-host | `configuration.repository-adoption` | Repository-local selected procedure or its declared executable dependency |
| `.agentic-workspace/skills/workspace-intent-discovery/SKILL.md` | package-managed | adopted-host | `configuration.repository-adoption` | Repository-local selected procedure or its declared executable dependency |
| `.agentic-workspace/skills/workspace-work-shape/SKILL.md` | package-managed | adopted-host | `configuration.repository-adoption` | Repository-local selected procedure or its declared executable dependency |
| `.agentic-workspace/skills/workspace-proof-selection/SKILL.md` | package-managed | adopted-host | `configuration.repository-adoption` | Repository-local selected procedure or its declared executable dependency |
| `.agentic-workspace/skills/workspace-transition-gates/SKILL.md` | package-managed | adopted-host | `configuration.repository-adoption` | Repository-local selected procedure or its declared executable dependency |
| `.agentic-workspace/skills/workspace-setup-jumpstart/SKILL.md` | package-managed | adopted-host | `configuration.repository-adoption` | Repository-local selected procedure or its declared executable dependency |
| `.agentic-workspace/skills/workspace-resources/SKILL.md` | package-managed | adopted-host | `configuration.repository-adoption` | Repository-local selected procedure or its declared executable dependency |
| `.agentic-workspace/skills/workspace-instruction-correction/SKILL.md` | package-managed | adopted-host | `configuration.repository-adoption` | Repository-local selected procedure or its declared executable dependency |
| `.agentic-workspace/skills/workspace-intent-discovery/prepare.py` | package-managed | adopted-host | `configuration.repository-adoption` | Repository-local selected procedure or its declared executable dependency |
| `.agentic-workspace/skills/workspace-setup-jumpstart/prepare.py` | package-managed | adopted-host | `configuration.repository-adoption` | Repository-local selected procedure or its declared executable dependency |

Adoption identity: `.agentic-workspace/adoption.json`. Payload provenance: `.agentic-workspace/payload-provenance.json`. Both are package integration records with the same lifecycle.

Only the declared workflow fence in `AGENTS.md` is managed. Text outside it remains repository-owned. Edited, unowned, or unsafe destinations are preserved and reported by Configuration.

## Preserved classes

- repo-owned: `.agentic-workspace/config.toml`, `.agentic-workspace/config.local.toml`, `AGENTS.md`
- module-owned: `.agentic-workspace/planning`, `.agentic-workspace/memory`, `.agentic-workspace/verification`
- local-only: `.agentic-workspace/local`
- promoted-output: `docs/decisions`
- Local diagnostic ignore rule: `.agentic-workspace/local/.gitignore`; created only when absent and preserved with local state on removal.

Unknown paths are preserved. Skill-discovery links are removed through their authenticated Configuration exposure owner before removing their canonical targets.

## Retired package surfaces

Convergence removes only these exact source-contract preimages; edited or unknown content is preserved. These paths are not installed into new hosts.

- `.agentic-workspace/WORKFLOW.md` -- `sha256:75162f6469347e428ab284a7e1478a0fdd62ab4f61897a8e913f5a5f6600afa7`
- `.agentic-workspace/docs/jumpstart-contract.md` -- `sha256:f37d653f52fdb3616758d8c5f31123f5d65d704e4c2cb971edd45f9729abbd4e`
- `.agentic-workspace/docs/module-map.md` -- `sha256:e87c87007f08021c0a9af478e758a784782c543cc427d1e07db9ea2e9ce869df`
- `.agentic-workspace/docs/setup-findings-contract.md` -- `sha256:33f5d6f2097ab9b1b8f4e0f32c2ea11b35c17afc9912df7815cb90c20bf7a698`
- `.agentic-workspace/docs/workspace-config-contract.md` -- `sha256:29a2e9f78f096a0c0be094d2970eebec6aeb99ca6755cb08b4568488fc2f4bc0`
- `.agentic-workspace/fallback/no-cli-policy.json` -- `sha256:a3e845b82cb0cd9d8a7fc3acdc7dcc7c416c2a47c5f37fa19a829634f8d9a450`
- `.agentic-workspace/fallback/no_cli_startup.py` -- `sha256:b22d032e2c3c40512f41e3b9091e105a7f800a001dfaba6f2ca3ee77d48d919c`
- `.agentic-workspace/system-intent/WORKFLOW.md` -- `sha256:93fab856c88682d958fdf817e15a8262e6a5a624b70fd7b6ef883cb6301f2d70`

Historical profiles and executable fallback maintenance live in the separate [source-maintenance inventory](source-maintenance-surface-catalogue.md). They are not public host profiles or CLI commands.
