# Maturity Model

This page explains what current maturity labels mean in this ecosystem.

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
| Agentic Planning | alpha | planning contract is real and useful, but still earlier in wording and contract stabilization |
| `agentic-workspace` | internal composition layer | thin workspace composition exists and is useful, but the primary external products are still memory and planning |