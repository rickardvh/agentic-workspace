# Workspace Runtime and Generated Surface Boundary

## Scope

- `src/agentic_workspace/` owns hand-maintained runtime decisions and contracts.
- `src/agentic_workspace/contracts/command_package_ir.json` owns command-package projection input.
- `generated/` contains generated Python and TypeScript projections; do not hand-edit it.

## Boundary

- Change a command surface or operation contract at its source, then regenerate the affected package projections.
- Root runtime code may consume generated contracts, but generated targets must not reconstruct routing or ownership from command strings.
- Package bootstrap payloads and the root operational install are separate layers; a source edit is not proof that an installed payload changed.

## Load when

- A task touches `src/agentic_workspace/`, command contracts, generated targets, package payloads, or installed-workspace behavior.

## Review when

- Runtime ownership, command IR, generation scripts, or source/payload/install boundaries change.

## Failure signals

- A generated target is edited directly.
- A command behavior change bypasses its operation/IR source.
- A source test pass is presented as installed-payload evidence.

## Verify

- Run the focused generated-command check after projection changes.
- Use the source-payload-operational-install check when package source, payload, and root install boundaries are involved.

## Last confirmed

2026-07-25
