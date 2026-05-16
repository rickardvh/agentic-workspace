# Generated Reference

These pages, except this index, are generated from JSON schemata under `src/agentic_workspace/contracts/schemas/`. Use them for exact field names, required fields, defaults, enum values, and structured-result shapes after the conceptual package docs have explained the behavior.

Do not hand-edit generated pages. Update the source schema and regenerate the reference docs instead.

## Host-Repo Runtime Outputs

- [Startup context](startup-context.md): `agentic-workspace start --task "<task>" --format json` for first contact when changed paths are not yet known; use `--select` for exact fields or `--verbose` for broad diagnostics.
- [Implementer context](implementer-context.md): `agentic-workspace implement --changed <paths> --format json` for path-scoped work when changed paths are already known; use `--verbose` for broad diagnostics.
- [Workspace report](workspace-report.md): `agentic-workspace report --format json`.
- [Compact contract answer](compact-contract-answer.md): shared compact selector answer envelope.
- [Setup findings](setup-findings.md): setup and follow-through findings.
- [Agent feedback](agent-feedback.md): optional agent feedback artifact.

## Configuration And Ownership

- [Workspace config](workspace-config.md): `.agentic-workspace/config.toml`.
- [Workspace local override](workspace-local-override.md): `.agentic-workspace/config.local.toml`.
- [Authority markers](authority-markers.md): authority marker policy.
- [Workspace surfaces manifest](workspace-surfaces-manifest.md): workspace surface inventory contract.
- [Structured file inventory](structured-file-inventory.md): structured file inventory contract.

## CLI, Modules, And Lifecycle

- [CLI commands](cli-commands.md): declared root CLI command surface.
- [CLI option groups](cli-option-groups.md): shared option group contract.
- [SkillSpec contract](skill-spec.md): package-owned skill semantics for CLI-assisted agent behavior.
- [Module registry](module-registry.md): module profiles, components, and package footprint metadata.
- [Module capability](module-capability.md): module capability descriptor shape.
- [Lifecycle generation readiness](lifecycle-generation-readiness.md): lifecycle generation readiness contract.

## Proof, Reporting, And Selection

- [Proof selection rules](proof-selection-rules.md): changed-path proof routing.
- [Proof routes manifest](proof-routes-manifest.md): proof route registry.
- [Report contract manifest](report-contract-manifest.md): report contract registry.
- [Selector contracts manifest](selector-contracts-manifest.md): selector contract registry.
- [Preflight policy](preflight-policy.md): preflight policy shape.

## Operations And Generated Adapters

- [Operation](operation.md): individual operation contract.
- [Operation contracts](operation-contracts.md): operation contract registry.
- [Operation primitives](operation-primitives.md): operation primitive registry.
- [Command adapter generation](command-adapter-generation.md): workspace command adapter generation contract.
- [Command package IR](command-package-ir.md): generated command package intermediate representation.
- [Conformance](conformance.md): conformance fixture contract.
- [Conformance contracts](conformance-contracts.md): conformance contract registry.

## Policy And Improvement Contracts

- [Improvement latitude policy](improvement-latitude-policy.md): improvement latitude policy.
- [Improvement signal contract](improvement-signal-contract.md): improvement signal artifact.
- [Optimization bias policy](optimization-bias-policy.md): optimization bias policy.
- [Repo friction policy](repo-friction-policy.md): repo friction policy.
- [Setup findings policy](setup-findings-policy.md): setup findings promotion policy.
- [Delegation outcomes](delegation-outcomes.md): local delegation outcomes.

## Python And Workflow Contracts

- [Python contract consumption](python-contract-consumption.md): Python contract consumption policy.
- [Python extraction map](python-extraction-map.md): Python-owned extraction map.
- [Python runtime boundary](python-runtime-boundary.md): Python runtime boundary.
- [Workflow artifact profiles](workflow-artifact-profiles.md): workflow artifact profiles.
- [Workflow definition format](workflow-definition-format.md): workflow definition format.
- [Context templates](context-templates.md): context template contract.
