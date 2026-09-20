<!-- GENERATED FILE: edit source_decision_contract.json and rerun `make render-schema-reference`. -->

# Current CLI Catalogue

Generated from the same `native_cli` declaration used by the native executable. The main AW skill is the ordinary agent procedure; this page is tool reference, not a mandatory command loop.

- Contract digest: `sha256:5121fe259c208f2dfd7f937aeb5abbaeb3261f858f22a2a5135fe9884225ab20`
- Program: `agentic-workspace`
- Command count: 4

## Commands

| Command | Requires JSON input | Purpose |
| --- | --- | --- |
| `agentic-workspace worker` | yes | Project bounded worker entry, expand an exact captured input, or assemble unproven return re-entry from a sealed Assignment packet. |
| `agentic-workspace resources` | yes | Propose with a resource request; execute by passing the exact returned action envelope unchanged to --input. Explicit context flags must match; omitted context comes from the envelope. |
| `agentic-workspace start` | no | Resolve the current operating decision. |
| `agentic-workspace invoke` | yes | Invoke the exact operation returned by the current owner. |

## Options

| Flag | Default | Choices | Purpose |
| --- | --- | --- | --- |
| `--target` | . | — | Repository target (default: current directory). |
| `--task` | — | — | Current task text; semantics remain agent-owned. |
| `--changed` | — | — | Changed paths; accepts multiple values and repetition. |
| `--format` | json | json | Output format (json). |
| `--projection` | — | compact, full, carried | Compact executable decision (default), full detail, or view plus disposable exact carriage for a thin host. |
| `--reference` | — | — | Exact immutable reference from carried output; --input supplies the machine-carried object. |
| `--answer` | — | — | JSON bounded answer for an exact carried decision reference; all owner material remains unchanged. |
| `--delivered` | — | — | Exact delivery_refs already held by this continuing consumer; suppress unchanged source prose only, never owner checks or obligations. |
| `--input` | — | — | JSON input file, or - for stdin; start accepts one current owner request or a bounded array; invoke requires an exact action. |

Use `--help` for the installed artefact's actual command boundary. Owner requests returned by `start` expose domain operations without adding domain CLI subcommands.

`start` is current resolution; `invoke` consumes one exact returned action. `resources` and `worker` are bounded dedicated tools. A request, route, packet seal or successful process does not grant mutation, ownership, proof or completion authority. Optional machine-local diagnostics remain distinct from repository mutation.

The older `cli_commands.json` / `cli_option_groups.json` schemas describe retained source-maintenance and historical adapters. Their `init`, `defaults`, `implement`, `proof` and module command families are not native public commands. Do not switch to a former host to bypass native rejection.

See [installation](../agentic-workspace-install.md), [everyday use](../everyday-use.md) and the [shared authority graph](../architecture/shared-rust-core.md).
