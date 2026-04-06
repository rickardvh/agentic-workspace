# Init Lifecycle And Adoption Modes

This page captures the root `agentic-workspace init` behavior that is otherwise easy to reconstruct from code and reports.

Use it when you need the canonical mode matrix for clean install, conservative adopt, or high-ambiguity adopt.

## Default Behavior

- `init` defaults to the full preset when module selection is omitted.
- The command bootstraps mechanically, then chooses install or adopt behavior from the detected repository state.
- The root CLI can print or write a handoff prompt when finishing work still needs judgment.

## Mode Matrix

| Mode | When it applies | Prompt requirement |
| --- | --- | --- |
| Clean install | No preserved workflow surfaces are detected and the repo does not need adopt behavior | `none` |
| Conservative adopt | Existing workflow surfaces are present, but the repo is not ambiguous enough to require a full finishing prompt | `recommended` |
| High-ambiguity adopt | Partial module state, placeholders, or heavy overlap make the finishing pass need explicit judgment | `required` |

## High-Ambiguity Signals

- Partial module state for a selected module.
- Placeholder markers or bootstrap markers still present in workflow surfaces.
- Existing workflow surfaces overlap strongly enough that the repo needs reconciliation before normal work continues.
- Managed root state already exists and the overlap suggests the repo should be treated as a finishing pass instead of a fresh install.

## Prompt Semantics

- `none` means the CLI can bootstrap without generating a finishing prompt.
- `recommended` means a prompt is useful but not mandatory.
- `required` means the prompt should be used to finish the handoff before normal work resumes.

## Maintainer Notes

- The root README should stay short and point here instead of duplicating the mode matrix.
- Package-local CLIs still own their own install and adoption behavior; the root layer only centralizes composition and reporting.
- If the behavior changes, update the root README and maintainer guidance together so the prompt semantics stay aligned.