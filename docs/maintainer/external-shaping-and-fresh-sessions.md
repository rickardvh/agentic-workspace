# External Shaping And Fresh Sessions

Long shaping material should live in durable repo or provider artifacts, not in an indefinitely continuing chat thread.

Use this pattern for new lanes, major PRs, or large design inputs:

- Put detailed shaping in GitHub issues, issue comments, checked-in docs, or review artifacts.
- Paste only short pointers, decisions, or corrections into chat.
- Start a fresh session for each new lane or major stacked PR group.
- Begin the fresh session from `AGENTS.md`, `agentic-workspace start`, and the lane or issue refs.
- Use a short lane/session digest for handoff context instead of replaying long prior chat.

One-off paste is acceptable when it is the cheapest way to transfer small current-turn context.
Durable shaping material should be linked or summarized, then stored outside chat so future agents can reload it without carrying old thread state.

This guidance does not excuse AW from reducing its own output, proof, and routing cost. It is an operator pattern for avoiding durable context bloat while the product continues to compress ordinary workflow surfaces.
