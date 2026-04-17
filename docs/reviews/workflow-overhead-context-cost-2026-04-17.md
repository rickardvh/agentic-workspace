# Workflow Overhead Context-Cost Review

## Goal

- Check whether the repo's own startup and handoff guidance imposes unnecessary rereads or dead-end workflow steps on routine agent work.

## Scope

- `AGENTS.md`
- `.agentic-workspace/WORKFLOW.md`
- `docs/contributor-playbook.md`
- `docs/reviews/README.md`

## Non-Goals

- Package-level workflow guidance
- Validation-lane correctness outside startup and handoff reading cost
- General roadmap reprioritization

## Review Mode

- Mode: `context-cost`
- Review question: Do the repo-defined startup and handoff docs add duplicated or stale workflow overhead for routine agent use?
- Default finding cap: 2 findings
- Inputs inspected first: `AGENTS.md`, `.agentic-workspace/WORKFLOW.md`, `docs/contributor-playbook.md`, `docs/reviews/README.md`

## Review Method

- Commands used:
  - `Get-Content AGENTS.md`
  - `Get-Content .agentic-workspace/WORKFLOW.md`
  - `Get-Content docs/contributor-playbook.md`
  - `Get-Content docs/reviews/README.md`
  - `Select-String -Path docs/contributor-playbook.md -Pattern "Agent Maintainer Path|Start Here|ordinary-use-pull"`
- Evidence sources:
  - Repo startup contract
  - Contributor playbook startup and routing guidance
  - Review-mode catalog

## Findings

### Finding: Contributor playbook duplicates the startup path internally

- Summary: `docs/contributor-playbook.md` carries two startup sections, `Agent Maintainer Path` and `Start Here`, that repeat the same early-read and compact-summary guidance with only minor wording differences.
- Evidence: Both sections tell maintainers to read `AGENTS.md`, then `TODO.md`, then prefer `agentic-planning-bootstrap summary --format json` before opening raw planning files; each section also controls when to read active execplans and package-local docs.
- Risk if unchanged: Agents pay extra reading and comparison cost to determine which startup path is canonical, and the duplicated sections can drift apart as the workflow evolves.
- Suggested action: Collapse the startup guidance into one canonical section in `docs/contributor-playbook.md` that extends `AGENTS.md` instead of restating the same sequence twice.
- Confidence: high
- Source: static-analysis
- Promotion target: canonical docs
- Promotion trigger: Next maintainer-doc cleanup or contributor playbook edit
- Post-remediation note shape: delete

### Finding: Contributor playbook points to a removed review mode

- Summary: `docs/contributor-playbook.md` still tells maintainers to use `docs/reviews/README.md` `ordinary-use-pull` mode, but that review mode no longer exists in the current review portfolio.
- Evidence: The playbook says `Use docs/reviews/README.md ordinary-use-pull mode...`, while `docs/reviews/README.md` currently defines `context-cost` for startup and handoff reading-cost audits and contains no `ordinary-use-pull` mode.
- Risk if unchanged: A maintainer following the documented path hits a dead end and either spends extra tokens reinterpreting the intended mode or skips the review path entirely.
- Suggested action: Replace the stale review-mode reference with the current `context-cost` route, or remove the sentence if the contributor playbook should no longer route this workflow through review artifacts.
- Confidence: high
- Source: static-analysis
- Promotion target: canonical docs
- Promotion trigger: Next contributor playbook edit
- Post-remediation note shape: delete

## Recommendation

- Promote: both findings to canonical docs cleanup
- Defer: none
- Dismiss: none

## Validation / Inspection Commands

- `Get-Content AGENTS.md`
- `Get-Content .agentic-workspace/WORKFLOW.md`
- `Get-Content docs/contributor-playbook.md`
- `Get-Content docs/reviews/README.md`
- `Select-String -Path docs/contributor-playbook.md -Pattern "Agent Maintainer Path|Start Here|ordinary-use-pull"`

## Drift Log

- 2026-04-17: Review created.
