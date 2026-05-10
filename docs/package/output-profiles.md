# CLI Output Selection

Agentic Workspace commands should return the smallest answer that lets an agent take the next correct step.

The default design rule is next-decision first:

- say what action is safe next
- name the files or commands needed for that action
- surface blockers, warnings, or ambiguity that change the action
- hide diagnostics, inventories, provenance, and long explanations unless they change the action

## Default And Drill-Down

The ordinary command output should be small. When an agent needs one or two exact fields, prefer `--select <field.path>` over a broader payload. Use `--verbose` for diagnostic, inventory, provenance, and audit detail.

Do not keep a parallel profile compatibility path. If a command needs more detail, expose an exact selector such as `--select` or `--section`, and reserve `--verbose` for diagnostics.

Healthy or normal data should usually be absent from default output. Examples include normal package identity, normal package boundaries, module inventories, empty obligation counts, inactive closeout policy, and full authority marker records.

Abnormal data should remain visible when it changes the next step. Examples include blocking compatibility drift, path authority warnings, missing changed paths, proof blockers, and active planning state that must be followed before implementation.

## Command Guidance

Use `implement --changed <paths>` before `start` when the user or current context already names the changed paths. Use `start --task "<task>"` for ordinary first contact when the path scope is unknown.

| Command | Smallest ordinary surface | Deeper surface |
| --- | --- | --- |
| `start` | `start --task "<task>" --format json` | `start --verbose --format json` |
| `implement` | `implement --changed <paths> --format json` | `implement --verbose --changed <paths> --format json` |
| `proof` | `proof --changed <paths> --format json` | `proof --verbose --changed <paths> --format json` |
| `summary` | `summary --format json` | `summary --select <field.path> --format json` or `summary --verbose --format json` |
| `config` | `config --format json` | `config --select <field.path> --format json` or `config --verbose --format json` |
| `report` | default router or `--section <name>` | `report --verbose --format json` |

Commands that do not yet expose `--select` should still follow the same rule: the ordinary output should answer the command's immediate question first, then point to a detail command when more context is needed.

## Regression Rule

When adding a new CLI command or expanding an existing payload, add or update tests that protect the default output from becoming a diagnostics dump. A useful test checks both:

- required next-decision fields are present
- inactive diagnostics or provenance fields are absent
