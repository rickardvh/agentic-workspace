# Design Principles

These principles describe how this ecosystem should evolve.

- Agent-first maintainer contract: optimize for agents that need explicit startup order, narrow validation, and cheap handoff.
- Repo-native state over chat-only residue: durable state should live in checked-in planning, memory, or canonical docs.
- Thin workspace composition: keep cross-module orchestration at the workspace layer, not domain logic.
- Explicit boundaries: planning, memory, routing, checks, and workspace composition should remain distinct concerns.
- Selective adoption: memory and planning must remain useful independently.
- Narrow validation: run the smallest check that proves the change locally; leave broad suites to CI when appropriate.
- Dogfood the shipped contract: internal use here should reveal product issues, not justify repo-local hacks.
- Fix the product before adding workarounds: when dogfooding reveals repeated friction, prefer improving the shipped package or contract over layering on repo-specific guidance.
- Generate repeated guidance from canonical sources when drift risk is high.
- Avoid new top-level concepts until real reuse pressure requires them.