# Agent instructions

This file is the local bootstrap contract for agents working in this repository.

Keep it short, stable, and repo-specific.

<!-- agentic-memory:workflow:start -->
Read `memory/system/WORKFLOW.md` for shared workflow rules.
<!-- agentic-memory:workflow:end -->

## Before doing any work

1. Read `memory/index.md`.
2. Use the user's request to determine what to work on next.
3. Read only the memory files routed by `memory/index.md` that are relevant to the subsystem you will touch.
4. Read `memory/system/WORKFLOW.md` only when the policy boundary is unclear.
5. Read repo docs only when routed memory points to them.
6. Prefer targeted tool checks over broad re-reading when they answer the question faster.
7. Use local scratch notes only when they help; they are optional support, not part of the system.

Do not rely on transient chat context when the same knowledge should exist in checked-in files.

`memory/index.md` is the routing layer for task-relevant durable knowledge.  
`memory/system/WORKFLOW.md` is a compact policy shim for the shared operating model.

For this repo, prefer command-targeted checks like `agentic-memory-bootstrap current`, `route`, `sync-memory`, `doctor`, and `verify-payload` when they reduce file reading.

## Repo scope

This repository produces and maintains a reusable bootstrap system that adds durable repository memory and overview-note conventions to other repositories.

- `bootstrap/` is the repo-agnostic installed payload.
- `src/repo_memory_bootstrap/` is the CLI and installer.
- `skills/` is the bundled product skill catalogue.
- Treat this repo as both the product source and the reference implementation it ships.

## Workspace guardrails

- Execute commands from this repo root.
- Do not edit sibling repos unless explicitly requested.
- When changing the bootstrap payload, preserve repo-agnostic behaviour unless the task explicitly asks for source-repo-specific customisation.
- Avoid leaking source-repo-specific details into generic bootstrap files.

## Design constraints

- Keep the payload repo-agnostic, conservative, and easy to inspect as plain files.
- Keep the installer conservative, repeatable, and explicit about overwrites.
- Prefer the simplest design that is safe to apply repeatedly to existing repositories.
- Local scratch is optional only; durable lessons belong in `/memory`.

## Runtime and tooling

- Use the project's existing Python tooling and packaging conventions.
- Prefer simple, standard-library-heavy implementations unless a dependency clearly earns its cost.
- For the installer, prefer straightforward file operations and text-based merge logic over elaborate abstractions.
- Use `pathlib` for filesystem work.
- Keep CLI behaviour compact and predictable.

## Style

- Use British English for agent-authored English text unless reproducing a source verbatim.
- Keep user-facing templates concise and practical.
- Prefer explicit placeholders over vague prose in bootstrap files.
- Keep bootstrap files self-contained so they can be copied by script with minimal extra logic.

## Installer guidance

- Treat packaged `bootstrap/` as the source of truth for installed payload files.
- Avoid guessing in ambiguous repo-root situations; prefer explicit `--target`.
- Keep dry-run output clear and trustworthy.

## Tool feedback loop

When developing this bootstrap tool in this repository:

- continuously evaluate whether the current task exposed friction, ambiguity, or unnecessary manual review in the install, doctor, adopt, or upgrade workflow
- continuously evaluate whether a repeatable procedure is stretching `AGENTS.md`, `WORKFLOW.md`, or repo docs beyond what should stay in checked-in guidance
- if you spot a meaningful improvement, suggest it explicitly and, when in scope, implement it in the tool or docs
- treat your own use of the bootstrap system here as product feedback, not just local task execution
- prefer small improvements that make future repo adoption, upgrade review, or maintainer use clearer and safer
- prefer promoting bounded repeatable procedures into skills rather than growing core workflow prose
- treat `skills/` in this repo as the source of truth for product skills during development
- do not assume a bundled installed copy matches the repo; reinstall the package only when intentionally testing the packaged skill path
- validate and edit skills from the repo paths first, and treat bundled installed copies as potentially stale test artefacts
- when a change affects the repo's installed memory or workflow contract, update this repo's own `memory/system/VERSION.md` as part of the change rather than leaving the source repo behind the payload
- after changing the installed payload contract, exercise the installed behavior against this repo itself with the bootstrap tool, not just by editing checked-in source files directly
- treat `agentic-memory-bootstrap doctor --target .` and the relevant install or upgrade path on this repo as required production testing when the payload or installer behavior changes
- do not assume editing `bootstrap/` or this repo's checked-in `memory/` files is equivalent to verifying the installed tool path

## Before ending a task

1. Update any affected memory or overview notes.
2. Check whether your changes affected any existing memory notes or workflow docs.
3. Update, deprecate, or remove those notes as needed.
4. Keep durable notes concise, factual, and de-duplicated.
5. When a change affects the repo's installed memory or workflow contract, update this repo's own `memory/system/VERSION.md` in the same change.
6. When the payload or installer behavior changed, run the bootstrap tool against this repo itself as part of verification rather than relying only on direct source-file edits.
