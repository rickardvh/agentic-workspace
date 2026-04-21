# Proof Surfaces Contract

## Purpose

This document records the normal proof lanes for the repository.

Use it when the question is not "what should I edit?" but "what proves that this contract still holds?"

## Rule

Use the narrowest proof lane that answers the current trust question.

Do not widen routine proof into a broad repo check when a surface-specific lane is enough.

## Default Proof Surface

Use:

```bash
agentic-workspace proof --target ./repo --format json
```

That command is the workspace-level query surface for:

- the canonical proof contract
- the normal proof routes
- the currently installed modules
- the current `status` and `doctor` health summary
- current warnings, manual-review signals, and stale generated-surface signals

It reports existing proof lanes. It does not replace them.

When the question is which proof lane is enough, use the proof-selection section in the machine-readable defaults contract:

```bash
agentic-workspace defaults --section proof_selection --format json
```

When the question is which proof lane should absorb a vague prompt, use the prompt-routing section:

```bash
agentic-workspace defaults --section prompt_routing --format json
```

When the question is already narrow, prefer the compact selector path:

```bash
agentic-workspace proof --target ./repo --route workspace_proof --format json
agentic-workspace proof --target ./repo --current --format json
```

Those forms return the compact contract answer profile from [`.agentic-workspace/docs/compact-contract-profile.md`](.agentic-workspace/docs/compact-contract-profile.md) instead of the full proof surface.

## Default Routes

| Trust question | Default route | Why |
| --- | --- | --- |
| What proves the workspace contract here? | `agentic-workspace proof --target ./repo --format json` | One queryable answer for the normal proof lanes plus current workspace proof state |
| What is the current workspace health? | `agentic-workspace status --target ./repo` | Cheap current-state summary |
| What drift or ambiguity needs remediation? | `agentic-workspace doctor --target ./repo` | Targeted drift and warning lane |
| Are planning surfaces coherent? | `uv run python scripts/check/check_planning_surfaces.py` | Canonical planning-surface proof |
| Do maintainer and generated surfaces still agree? | `make maintainer-surfaces` | Cross-surface contract proof |
| Does source, payload, and root install still line up? | `uv run pytest tests/test_source_payload_operational_install.py` | Explicit boundary proof |
| Is the root repo on the latest checked-in planning payload? | `uv run agentic-planning-bootstrap upgrade --target .` | Final payload freshness proof |
| Is the root repo on the latest checked-in memory payload? | `uv run agentic-memory-bootstrap upgrade --target .` | Final payload freshness proof |

## Boundaries

- Keep proof surfaces queryable and compact.
- Preserve package-local ownership of package-local tests and validation.
- Do not treat the workspace proof surface as a new source of truth over the underlying checks.
- Do not turn proof into monitoring, scoring, or long-running health infrastructure.

## Relationship To Other Docs

- Use [`.agentic-workspace/docs/compact-contract-profile.md`](.agentic-workspace/docs/compact-contract-profile.md) when you want the one-answer query shape instead of the full proof object.
- Use [`docs/default-path-contract.md`](docs/default-path-contract.md) for the front-door route selection contract.
- Use [`docs/environment-recovery-contract.md`](docs/environment-recovery-contract.md) when the repo is already in a broken or ambiguous state and you need a recovery sequence.
- Use [`.agentic-workspace/docs/generated-surface-trust.md`](.agentic-workspace/docs/generated-surface-trust.md) when the trust question is specifically about generated mirrors and their canonical sources.
