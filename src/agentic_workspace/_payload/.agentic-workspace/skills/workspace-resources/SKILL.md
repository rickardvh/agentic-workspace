---
name: workspace-resources
description: Manage task scratch and necessary checkout isolation through one current-policy-aware native resource lifecycle, including terminal cleanup and interrupted recovery.
---

# Task resources

Keep direct work in the existing checkout. Use bounded scratch or necessary
isolation only for a concrete task need; owners retain policy and lifecycle custody.

Use [the question](procedure.md) or the same sources directly:

- [Choose the smallest resource](references/select.md).
- [Propose and carry an exact resource operation](references/operation.md).
- [Reserve reproducible build output](references/build.md).
- [Reconcile lifetime and clean up](references/cleanup.md).
- [Recover bounded or interrupted resources](references/recovery.md).
- [Interpret local hygiene](references/hygiene.md).

Follow [exact owner carriage](../workspace-startup/references/owners.md).
Procedure selection grants no effect, proof, claim or review authority.
