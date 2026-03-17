# Upgrade Playbook

## Purpose

Use this playbook when upgrading an older repository install of the bootstrap system.

## Goals

- preserve repo-specific scope, commands, and guardrails in `AGENTS.md`
- move reusable workflow rules into `memory/system/WORKFLOW.md`
- update core shared files deterministically where safe
- leave customised local files for targeted review when needed

## Upgrade checklist

1. Read `AGENTS.md`, `TODO.md`, `memory/index.md`, and `memory/system/WORKFLOW.md`.
2. Run `agentic-memory-bootstrap doctor --target <repo>`.
3. Run `agentic-memory-bootstrap upgrade --dry-run --target <repo>`.
4. Replace shared repo-agnostic files the upgrade plan marks as safe.
5. Patch `AGENTS.md` only enough to point at `memory/system/WORKFLOW.md`.
6. Review `TODO.md` manually if the shared workflow changed how completed detail should be condensed.
7. Preserve repo-specific scope, commands, and workspace guardrails.
8. Review any manual-review items before applying them.
9. Run the memory freshness audit after the upgrade.

## Typical manual review items

- older `AGENTS.md` files that still embed shared workflow rules
- starter memory notes that have been locally customised
- repos that already have their own planning or contribution workflow files
