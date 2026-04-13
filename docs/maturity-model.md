# Maturity Model

Last doctrinal review: 2026-04-10

This page explains what current maturity labels mean in this ecosystem.

## Role Boundary

This page owns maturity labels and the rationale for the current label of each shipped surface.

It does not own:

- the full capability map
- ecosystem packaging stance
- bounded future work

Route those concerns to:

- `docs/agent-os-capabilities.md` for capability taxonomy and architectural role
- `docs/ecosystem-roadmap.md` for ecosystem stance and extraction discipline
- `ROADMAP.md` for bounded follow-on work revealed by maturity review

## Refresh Triggers

Update this page directly when any of the following happens:

- a shipped surface changes maturity
- the reason for the current maturity label is materially different after recent dogfooding
- a maturity explanation starts depending on stale historical wording instead of current blockers
- another doctrine page starts carrying maturity rationale that belongs here instead

## Alpha

Use `alpha` when the product contract is real and dogfooded, but naming, schema shape, or guidance may still change noticeably as maintainers learn from adoption.

Alpha implies:

- early-adopter use is welcome
- conservative upgrade paths exist where practical
- breaking guidance or schema refinements are still plausible

## Beta

Use `beta` when the product contract is expected to be broadly usable, selective adoption works, and future change should mostly refine rather than redefine the surface.

Beta implies:

- stronger continuity expectations
- more stable installation and upgrade guidance
- remaining changes should be incremental, not a conceptual reset

## Current Status

| Surface | Current maturity | Meaning here |
| --- | --- | --- |
| Agentic Memory | beta | durable repo-memory contract is usable and should evolve incrementally |
| Agentic Planning | beta | planning now has explicit capability-fit, delegated-judgment, execution-summary, and environment-recovery contracts, so remaining changes should mostly refine the execution surface rather than define missing core behavior |
| `agentic-workspace` | internal composition layer | thin workspace composition exists and is useful, but the primary external products are still memory and planning |

Refresh this page through a doctrine-refresh review when major shipped contracts change what “alpha”, “beta”, or “internal composition layer” mean in practice.
