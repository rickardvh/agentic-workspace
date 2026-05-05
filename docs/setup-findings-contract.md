# Setup Findings Contract

Setup findings are optional agent-produced input from post-bootstrap discovery. They let setup, review, validation friction, and memory-improvement signals enter one improvement-intake path without making setup a repo analyzer.

## Artifact

The optional artifact is `tools/setup-findings.json` with kind `workspace-setup-findings/v1`. It is validated against `src/agentic_workspace/contracts/schemas/setup_findings.schema.json`.

Use:

```bash
agentic-workspace setup --target . --format json
agentic-workspace defaults --section improvement_intake --format json
```

## Accepted Classes

`repo_friction_evidence` is for concrete repeated friction that can become a durable improvement issue, check, doc, memory note, contract, or workflow change.

`planning_candidate` is for bounded future work that has a clear owner, next action, and reason it should not be handled inside current setup.

## Promotion Rule

Preserve a setup finding only when it has enough evidence to reduce future rediscovery or route bounded follow-up. Prefer findings with concrete paths, commands, symptoms, reproduction notes, confidence, and a durable owner.

Dismiss or keep transient any finding that is speculative, generic, broad, missing a next action, or only useful to the current chat.

## Boundaries

Do not build a workspace-owned analyzer. Do not auto-write Planning or Memory state from setup input. Do not preserve findings that have no durable owner or bounded next action.
