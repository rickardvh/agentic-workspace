<!-- GENERATED FILE: edit source_decision_contract.json and rerun `make render-schema-reference`. -->

# Current CLI Catalogue

Generated from the same `native_cli` declaration used by the native executable. The main AW skill is the ordinary agent procedure; this page is tool reference, not a mandatory command loop.

- Contract digest: `sha256:b3701072538853da4c548aa5fe7f4f2212e1c46e94911bfcab35f525ee9098a7`
- Program: `agentic-workspace`
- Command count: 6

## Commands

| Command | Requires JSON input | Purpose |
| --- | --- | --- |
| `agentic-workspace setup` | no | Add or refresh AW in this repository; show the proposal and ask before writing. |
| `agentic-workspace worker` | yes | Present worker entry or a complete manual snapshot, expand an exact captured input, or wrap new return material with host-held Assignment identity. |
| `agentic-workspace resources` | yes | Propose with a resource request; execute by passing the exact returned action envelope unchanged to --input. Explicit context flags must match; omitted context comes from the envelope. |
| `agentic-workspace start` | no | Resolve the current operating decision. |
| `agentic-workspace invoke` | yes | Invoke an exact action with a complete work envelope or carriage. A bare action requires original --target, --task and --changed. For a current workspace.cli_invoke question, use its exact reference, reentry or carriage, and --answer with the JSON authorize-write scalar to authorize and execute together. |
| `agentic-workspace activation-index` | yes | Check or derive a repository registry activation index from its procedure sources; explicit authoring only. |

## Options

| Flag | Default | Choices | Purpose |
| --- | --- | --- | --- |
| `--target` | . | — | Repository target (default: current directory). |
| `--task` | — | — | Current task text; semantics remain agent-owned. |
| `--changed` | — | — | Changed paths; accepts multiple values and repetition. |
| `--format` | — | json, yaml, text | Output format. Terminal output defaults to YAML, captured output to JSON, and setup to text. Overrides AGENTIC_WORKSPACE_OUTPUT_FORMAT. |
| `--projection` | — | compact, full, carried | Compact executable decision (default), full detail, or view plus disposable exact carriage for a thin host. |
| `--reference` | — | — | Exact immutable reference from carried output; --input supplies the machine-carried object. |
| `--answer` | — | — | JSON answer for an exact decision reference, or an arguments object for an exact owner request reference. Preserves owner identity and prior carried answers; normal owner validation applies. |
| `--delivered` | — | — | Pass individual values from delivery_refs, e.g. --delivered RECEIPT1 --delivered RECEIPT2. Suppresses unchanged source prose for this continuing consumer without changing owner checks or obligations. |
| `--observation` | — | — | Nominate one current finding through start, without a JSON file; use --source for its actual provenance. Mutually exclusive with --need. |
| `--need` | — | — | Nominate one unmet prerequisite through start, without a JSON file; keep the current task. Mutually exclusive with --observation. |
| `--source` | — | — | Actual source reference for --observation or --need; omitted provenance remains unknown. |
| `--source-revision` | — | — | Known source revision for the single finding; an asserted revision is not a checked dependency or authority. |
| `--coverage` | — | bounded, partial, unknown | Actual source coverage for the single finding (default: unknown). |
| `--input` | — | — | JSON input file, or - for stdin; start accepts current owner requests or work context; invoke accepts a complete invocation/work envelope, carriage plus --reference, or a bare exact action with explicit original work context. |
| `--yes` | — | — | Authorise the exact setup proposal (setup only). |
| `--dry-run` | — | — | Show the setup proposal without changes (setup only). |
| `--recover` | — | — | Inspect and authorise an interrupted setup (setup only). |
| `--version` | — | — | Show the version of the invoked native executable. Run it without a command. |

Use `--help` for the installed artefact's actual command boundary. Owner requests returned by `start` expose domain operations without adding domain CLI subcommands.

`start` is current resolution; `invoke` consumes one exact returned action. `resources` and `worker` are bounded dedicated tools. A request, route, packet seal or successful process does not grant mutation, ownership, proof or completion authority. Optional machine-local diagnostics remain distinct from repository mutation.

The retired `init`, `defaults`, `implement`, `proof` and module command families are not native public commands. Owner actions are obtained from the current native decision.

See [installation](../agentic-workspace-install.md), [everyday use](../everyday-use.md) and the [shared authority graph](../architecture/shared-rust-core.md).
