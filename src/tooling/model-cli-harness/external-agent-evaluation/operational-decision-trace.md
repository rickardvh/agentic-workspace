# Operational Decision Trace

This protocol makes AW operation observable without asking agents to reveal private chain-of-thought.

Externalize only brief operational decisions:

1. Task interpretation and uncertainty when it changes the next action.
2. AW route or command used, and why that route is the current smallest safe route.
3. Durable context decision: Memory used, dismissed, or not applicable.
4. Active-state decision: Planning used, continued, closed, or not applicable.
5. Verification/proof decision and safe claim boundary.
6. Residue owner, if any.
7. Stop condition: once the next safe action is clear, proceed with work instead of narrating.

Evaluation should score observable decisions through command output, result records, comments, file changes, and final claim boundaries. Do not score exact phrasing or hidden reasoning. The useful evidence is whether the agent left a reviewable operational trace: which route it followed, which owner surfaces it used or dismissed, what proof changed the claim, and who owns residue.
