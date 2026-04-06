# Source, Payload, And Root Operational Install

This page defines the maintainer workflow boundary between package source, shipped payload, and the monorepo's live installed systems.

Use it whenever a task touches a package workspace and the root planning or memory install in the same change.

## The Three Layers

Agentic Workspace uses three distinct layers in this monorepo:

- **package source** under `packages/*/src/`, `tests/`, `skills/`, and helper logic
- **package payload** under `packages/*/bootstrap/`, which describes what a package installs into a target repository
- **root operational install** at repo root, which is the live dogfooded memory and planning system for this monorepo

These layers are related, but they are not interchangeable.

## Canonical Maintainer Workflow

When a task affects a shipped package:

1. implement behavior in **package source**
2. update or verify the **package payload** when installed contract surfaces change
3. refresh the **root operational install** through the canonical package or workspace lifecycle workflow
4. validate the **root operational install** as the real dogfooding target

In short:

- implement in source
- package or render into payload
- apply canonically to root
- verify root as the real install

## Rules

- Do not treat `packages/*/bootstrap/` as the live system for this monorepo.
- Do not patch the root operational install as a substitute for fixing package source.
- Do not leave installed workflow surfaces under `packages/*/`; they are accidental state in this repo.
- If source, payload, and root install disagree, treat **source** as the implementation authority and refresh the other layers from it.
- Use `make maintainer-surfaces` to catch accidental package-local installs, generated-surface drift, and incomplete root installs.

## Repair Strategy

If package source, package payload, and root operational install diverge:

1. fix package source
2. refresh or verify package payload
3. reapply the canonical lifecycle workflow to the root operational install
4. validate the root operational install
5. remove any accidental package-local installed state

Do not repair divergence by editing the nearest copy in place.

## Anti-Patterns

Avoid these mistakes:

- creating `.agentic-workspace/` installs under `packages/*/`
- leaving `TODO.md`, `ROADMAP.md`, `docs/execplans/`, or generated maintainer mirrors under a package root
- treating payload templates as repo-owned live workflow files
- validating package behavior only against payload or package-local copies instead of the refreshed root install

## Validation

Use these commands when the task touches the boundary:

- `make maintainer-surfaces`
- the narrowest package-local test or lint lane that proves the source change
- the owning package or workspace lifecycle refresh command for the root install

The package is not fully proven until the refreshed root operational install also passes its relevant checks.
