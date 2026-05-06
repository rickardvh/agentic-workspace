# CLI Output Profiles

Agentic Workspace commands should return the smallest answer that lets an agent take the next correct step.

The default design rule is next-decision first:

- say what action is safe next
- name the files or commands needed for that action
- surface blockers, warnings, or ambiguity that change the action
- hide diagnostics, inventories, provenance, and long explanations unless they change the action

## Profiles

Use these profiles consistently when a command has more than one useful output shape.

| Profile | Purpose |
| --- | --- |
| `tiny` | A next-decision card for cold start, weak agents, or narrow execution. |
| `compact` | Bounded operational context that may include current state and routing detail. |
| `full` | Diagnostic, inventory, provenance, and contract detail for review or debugging. |

Healthy or normal data should usually be absent from `tiny`. Examples include normal package identity, normal package boundaries, module inventories, empty obligation counts, inactive closeout policy, and full authority marker records.

Abnormal data should remain visible when it changes the next step. Examples include blocking compatibility drift, path authority warnings, missing changed paths, proof blockers, and active planning state that must be followed before implementation.

## Command Guidance

Use `implement --profile tiny --changed <paths>` before `start` when the user or current context already names the changed paths. Use `start --profile tiny --task "<task>"` for ordinary first contact when the path scope is unknown.

| Command | Smallest ordinary surface | Deeper surface |
| --- | --- | --- |
| `start` | `start --profile tiny --task "<task>" --format json` | `start --profile full --format json` |
| `implement` | `implement --profile tiny --changed <paths> --format json` | `implement --profile full --changed <paths> --format json` |
| `proof` | `proof --profile tiny --changed <paths> --format json` | `proof --profile full --changed <paths> --format json` |
| `summary` | `summary --profile compact --format json` | `summary --profile full --format json` |
| `config` | `config --profile tiny --format json` | `config --profile compact --format json`, then `config --profile full --format json` |
| `report` | default router profile or `--section <name>` | `report --profile full --format json` |

Commands that do not yet expose a `tiny` profile should still follow the same rule: the ordinary output should answer the command's immediate question first, then point to a detail command when more context is needed.

## Regression Rule

When adding a new CLI command or expanding an existing payload, add or update tests that protect the smallest profile from becoming a diagnostics dump. A useful test checks both:

- required next-decision fields are present
- inactive diagnostics or provenance fields are absent
