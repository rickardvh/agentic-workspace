# Machine-Readable Over Prose Audit

## Goal

- Check whether the remaining front-door operating questions that agents ask repeatedly are now answered through structured surfaces first, with prose serving as boundary guidance rather than the only source of truth.

## Scope

- Workspace module and skill discovery surfaces.
- New default-route contract.
- Front-door docs that reference those surfaces.

## Non-Goals

- Full registry coverage review for every internal surface.
- New automatic routing or classification features.

## Review Mode

- Mode: `generated-surface-trust`
- Review question: Where was the repo still compensating with prose for information that should be available structurally, and has this tranche corrected the main front-door gap?
- Default finding cap: 2 findings
- Inputs inspected first: `src/agentic_workspace/cli.py`, `README.md`, `docs/default-path-contract.md`, `docs/module-capability-contract.md`

## Review Method

- Commands used:
  - `uv run pytest tests/test_workspace_cli.py`
  - `make maintainer-surfaces`
- Evidence sources:
  - workspace CLI output contract
  - root docs links
  - existing module and skill registries

## Findings

### Finding: Default-route guidance had remained prose-only longer than necessary

- Summary: The repo already had machine-readable module and skill surfaces, but the normal route for startup, lifecycle, validation, and combined-install use still depended on explanatory prose spread across multiple docs.
- Evidence: The new `defaults` command adds a stable JSON/text contract covering those recurring questions, and the front-door docs now point to that command instead of answering every route choice inline.
- Risk if unchanged: The repo would keep growing operational prose faster than direct operability, especially for smaller agents.
- Suggested action: Keep adding structured answers when recurring route questions stabilize, and shorten prose once the structured surface exists.
- Confidence: high
- Source: mixed
- Promotion target: canonical docs
- Promotion trigger: Implemented in this tranche.
- Post-remediation note shape: delete

### Finding: Structured defaults need to stay clearly scoped to stable route questions

- Summary: Machine-readable structure is cheaper than prose only when the surface stays narrow and trustworthy; it should answer stable route questions rather than becoming a second policy narrative.
- Evidence: The new defaults payload is limited to startup, lifecycle, skill discovery, validation, and combined-install behavior, while architectural nuance remains in `docs/default-path-contract.md` and related canonical docs.
- Risk if unchanged: A too-broad defaults surface would recreate the same interpretation cost in JSON form.
- Suggested action: Keep `agentic-workspace defaults` focused on stable operational answers and resist turning it into a general architecture dump.
- Confidence: medium
- Source: static-analysis
- Promotion target: none
- Promotion trigger: none
- Post-remediation note shape: retain

## Recommendation

- Promote: none
- Defer: none
- Dismiss: broad prose-to-structure conversion without repeated evidence that the question is recurring and stable

## Validation / Inspection Commands

- `uv run pytest tests/test_workspace_cli.py`
- `make maintainer-surfaces`

## Drift Log

- 2026-04-09: Review created alongside the front-door defaults tranche.
