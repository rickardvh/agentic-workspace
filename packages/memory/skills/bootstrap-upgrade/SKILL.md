---
name: bootstrap-upgrade
description: Upgrade memory for an already bootstrapped repository safely. Use when an agent should let the tool determine the installation source automatically, run the upgrade, and report conservative manual-review items.
---

# Bootstrap Upgrade

Use this skill to upgrade memory without asking the user to choose an installation source.

The skill is intentionally small. It exists to execute the upgrade contract, not to duplicate CLI behaviour or long review choreography.

## Contract

- determine the installation source automatically
- run the upgrade with the packaged tool
- report conservative manual-review items only when the tool leaves local files untouched
- confirm the result with the relevant built-in checks

## Use

Invoke the packaged CLI upgrade path for the target repo. If the packaged skill is not already visible in the runtime, use the no-install CLI runner that the product docs point to.

## Guardrails

- Never assume a shared file should replace a repo-local file with active customisation.
- Treat repo-local workflow notes and customised seed notes as manual-review surfaces.
- Preserve repo-specific scope, commands, and guardrails in `AGENTS.md`.
- If a repo already has an equivalent optional fragment, keep the existing behaviour and avoid duplicate appends.
- Keep the upgrade outcome visible in checked-in files rather than in skill-only state.

## Typical outputs

- shared bootstrap files updated to the new version
- local docs left untouched when they are repo-owned
- a short summary of manual-review items, if any
- verification that the active memory surfaces still look correct
