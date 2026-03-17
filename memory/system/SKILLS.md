# Skills Model

## Purpose

This document defines how skills fit into `agentic-memory-bootstrap`.

## Layer boundary

Use three layers:

- bootstrap contract = always-on, minimal, repo-local structure
- checked-in memory = durable repo knowledge and continuity
- skills = optional specialised executable playbooks

## Keep in checked-in docs

Keep these in `AGENTS.md`, the repo's chosen task system, or `/memory`:

- repo purpose
- local constraints and guardrails
- architecture facts and invariants
- milestone or task state
- lightweight current-task context that should stay visible in checked-in memory

The core operating model must remain visible and useful even when skills are unavailable.

## Promote into skills

Use a skill when the behaviour is:

- reusable across tasks or repos
- optional rather than mandatory
- triggerable from a clear request
- procedural or operational
- too detailed for the core repo contract

Good fits:

- memory hygiene
- bootstrap adoption
- bootstrap upgrade
- docs alignment
- release or packaging checks

## Avoid first

Do not start with fuzzy skills that overlap heavily with built-in agent behaviour, such as:

- generic planning
- generic coding
- vague "use memory better" instructions

## Distribution stance

For now:

- keep starter skills in this repository under `skills/`
- do not install skills into target repos by default
- treat a separate companion package as a later option only if these skills prove reusable beyond this repo
