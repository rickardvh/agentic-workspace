# Init Lifecycle, Repo State, And Handoff

This page captures the root `agentic-workspace init` behavior that is otherwise easy to reconstruct from code and reports.

Use it when you need the canonical intent, repo-state, policy, and handoff contract for `init`.

## Default Behavior

- `init` defaults to the full preset when module selection is omitted.
- If `agentic-workspace.toml` exists, `workspace.default_preset` becomes the default preset when the user omits `--preset` and `--modules`.
- If `agentic-workspace.toml` exists, `workspace.agent_instructions_file` becomes the canonical root startup-entrypoint filename.
- The user intent is the selected preset: `memory`, `planning`, or `full`.
- The command bootstraps mechanically, classifies repo state, then chooses the safest lifecycle mode automatically.
- The root workspace layer is part of that bootstrap contract, not an incidental repo file copy.
- Clean installs should seed `.agentic-workspace/WORKFLOW.md`, `.agentic-workspace/OWNERSHIP.toml`, and a coherent root startup entrypoint for the selected modules.
- The root CLI also keeps one checked-in external-agent handoff surface at `llms.txt`.
- Post-bootstrap jumpstart is separate from `init` and uses [`docs/jumpstart-contract.md`](docs/jumpstart-contract.md) plus `agentic-workspace defaults --section jumpstart --format json` for the bounded follow-through phase.
- When bootstrap still needs judgment, the CLI writes the next-action brief to `.agentic-workspace/bootstrap-handoff.md`.
- When bootstrap still needs judgment, the CLI also writes the compact structured sibling artifact to `.agentic-workspace/bootstrap-handoff.json`.

## Intent Contract

| User intent | Command shape |
| --- | --- |
| Set up this repo for Agentic Memory | `agentic-workspace init --preset memory` |
| Set up this repo for Agentic Planning | `agentic-workspace init --preset planning` |
| Set up this repo for both | `agentic-workspace init --preset full` |

## Mode Matrix

| Repo state | Inferred policy | Lifecycle mode | Prompt requirement |
| --- | --- | --- | --- |
| `blank_or_unmanaged_repo` | `install_direct` | Clean install | `none` |
| `light_existing_workflow` | `preserve_existing_and_adopt` | Conservative adopt | `recommended` |
| `docs_heavy_existing_repo` | `require_explicit_handoff` | High-ambiguity adopt | `required` |
| `partial_or_placeholder_state` | `require_explicit_handoff` | High-ambiguity adopt | `required` |

## High-Ambiguity Signals

- More than one supported root startup-entrypoint filename is already present.
- Partial module state for a selected module.
- Placeholder markers or bootstrap markers still present in workflow surfaces.
- Existing canonical handoff surfaces overlap with workflow surfaces and need reconciliation before normal work continues.
- Existing workflow surfaces overlap strongly enough that the repo needs reconciliation before normal work continues.
- Managed root state already exists and the overlap suggests the repo should be treated as a finishing pass instead of a fresh install.

## Handoff Surfaces

- `llms.txt` is the canonical external-agent handoff file for the repo.
- `docs/jumpstart-contract.md` is the canonical post-bootstrap jumpstart contract, and `agentic-workspace defaults --section jumpstart --format json` is its compact machine-readable sibling.
- `.agentic-workspace/bootstrap-handoff.md` is the canonical post-bootstrap next-action brief when `prompt_requirement` is not `none`.
- `.agentic-workspace/bootstrap-handoff.json` is the compact structured sibling artifact for the same bootstrap handoff when `prompt_requirement` is not `none`.
- `none` means bootstrap can finish without a handoff brief.
- `recommended` means the brief is useful but not mandatory.
- `required` means the brief should be followed before normal work resumes.

## Maintainer Notes

- Recovery after interrupted bootstrap or lifecycle ambiguity should follow `docs/environment-recovery-contract.md` so the ordered remediation path stays centralized.
- The root README should stay short and point here instead of duplicating the mode matrix.
- Package-local CLIs still own their own install and adoption behavior; the root layer only centralizes composition and reporting.
- Repo-owned lifecycle defaults and update intent belong in `agentic-workspace.toml`, not under `.agentic-workspace/`.
- `upgrade` should treat `agentic-workspace.toml` as the repo-owned source of update intent and keep module `UPGRADE-SOURCE.toml` metadata aligned with it.
- `status` and `doctor` should treat missing shared workspace-layer files or missing workspace pointer fences as first-class warnings.
- If the behavior changes, update the root README and maintainer guidance together so the prompt semantics stay aligned.
