# Knowledge Promotion Workflow

This document defines the canonical process for promoting durable interpretive understanding from transient contexts (chat, active plans, local notes) into the repository's permanent memory and documentation.

## Promotion Thresholds

Promote knowledge when it satisfies the **Anti-Concealment** and **Repeated-Evidence** rules in [`.agentic-workspace/docs/signal-hygiene-contract.md`](signal-hygiene-contract.md), specifically:

- **Rediscovery Cost**: Future work would pay a significant cost if the knowledge stayed only in chat residue.
- **Repeatability**: The pattern has appeared in at least two independent contexts.
- **Stability**: The understanding is stable enough to explain to a new contributor without immediate correction.

## Surface Selection Rules

Route knowledge to the strongest home based on its class:

| Knowledge Class | Surface | Purpose |
| --- | --- | --- |
| **Interpretive Hints** | Memory | Subsystem-specific context, recurring gotchas, and "why we do it this way" notes. |
| **Stable Doctrine** | Canonical Docs | High-level philosophy, design principles, and standing repo rules (e.g. `AGENTS.md`). |
| **Enforceable Rules** | Config / Checks | Policy that can be machine-read or verified (e.g. `.agentic-workspace/config.toml`, `scripts/check/`). |

## Workflow Steps

### 1. Capture (During Task)
Record new insights in the `Iterative Follow-Through` or `Discovered implications` section of the active [execplan](TEMPLATE.md).

### 2. Verify (Task Closure)
During the "Proof Report" phase, evaluate which captured insights meet the promotion thresholds.

### 3. Promote (Post-Execution)
- **To Memory**: Add a new note or update an existing one in the relevant memory path.
- **To Docs**: Update the relevant markdown file (e.g. `docs/design-principles.md`).
- **To Config**: Update `.agentic-workspace/config.toml` or equivalent.

### 4. Record Closure
In the `Execution Summary` of the archived plan, record where the knowledge was promoted in the `Knowledge promoted` field.

## Guardrails

- **Do not over-specify**: Keep Memory focused on interpretive value, not a copy of the source code.
- **Do not hide friction**: Knowledge promotion should explain *how* to handle friction, not hide the fact that the friction exists.
- **Prefer Repo-Native**: Always prefer checked-in docs/config over Memory when the knowledge is stable enough to be a hard rule.
