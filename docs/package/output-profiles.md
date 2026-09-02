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
| `evaluation status` | lifecycle, coverage, criteria, freshness, owner, blockers, and next action | `evaluation status --evaluation-id <id> --select <field-or-full> --format json` |

Commands that do not yet expose `--select` should still follow the same rule: the ordinary output should answer the command's immediate question first, then point to a detail command when more context is needed.

## Regression Rule

When adding a new CLI command or expanding an existing payload, add or update tests that protect the default output from becoming a diagnostics dump. A useful test checks both:

- required next-decision fields are present
- inactive diagnostics or provenance fields are absent

## Enforced Budgets

Named ordinary profiles declare four limits in the versioned
`workspace-output-profile-budgets/v2` contract exposed by the
`operational_compression` report:

- UTF-8 JSON bytes
- recursive field count
- estimated tokens (`ceil(json_bytes / 4)`, used only as a stable regression estimate)
- non-empty human-render lines

The package tests exercise cold and warm `init` plus ordinary `start`, `report`,
`doctor`, Assignment lifecycle, and Evaluation status fixtures. Assignment lifecycle uses the
`assignment-lifecycle-decision/v1` profile: its required `state` member is a compact decision
projection, while `state_ref` points to complete disposable run state for exact inspection. A
budget increase is a reviewed contract change, not a
side effect of adding another default field. Ordinary `init` JSON uses a
`decision-envelope/v1`; `init --verbose --format json` is the exact expansion
route for module reports, config, effects, provenance, and the full lifecycle
plan.

## Progress Without Log Noise

Compact validation commands buffer successful child output, but emit a
`[progress]` heartbeat to stderr every 30 seconds while a command remains
running. The interval can be shortened with
`--progress-interval-seconds <seconds>` for a known proof environment. The
heartbeat reports only the label and elapsed time; detailed child output stays
in the failure log when the command fails.
