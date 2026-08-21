# Which AW Module Should I Enable?

Use `agentic-workspace` as the public entrypoint. Enable only the modules whose specialized capability pays back for this repository.

AW itself is the dynamic operating-context/control layer. Modules are optional peer extensions of what the generic `resolve -> act -> reconcile` loop can know and do. There is no privileged first module that every repo should start with.

AW may be unnecessary when the repo is cheap to reread, tasks finish in one sitting, existing docs/tests already carry the important rules, and there is little recurring context, handoff, proof, or control friction. A routing-only install can also be enough when the repo benefits from dynamic instructions/control but no specialized module justifies durable state.

For the product model, use [`docs/package/overview.md`](package/overview.md). For module boundaries, use [`docs/package/modules.md`](package/modules.md).

## Fast chooser

Use `agentic-workspace defaults --section module_selection --format json` for the current compact selection guidance.

Choose by the bottleneck you actually have:

- Use **Memory** when agents repeatedly rediscover durable repo lessons, invariants, traps, runbooks, or subsystem orientation that is expensive to reconstruct.
- Use **Planning** when active work itself must survive interruption: bounded intent, sequencing, handoff, continuation, or non-obvious completion boundaries.
- Use **Verification** when reusable manual/semi-automated verification protocols, bounded evidence, or known verification gaps need a repo-visible owner.
- Combine modules when more than one capability independently saves enough future work to justify its state.
- Use **routing-only / no modules** when AW's dynamic control, repo customization, ownership, skills, or compact routing are useful but none of the current specialized domains justify installation.
- Stay with ordinary repo docs/tests alone when even the core AW layer would cost more than it saves.

The current first-party modules are examples, not the limit of the architecture. Future modules may add delegation, deployment, richer repository retrieval, security, or other functions through the same generic contribution model.

## Progressive discovery

Module selection should not enlarge the ordinary mental model.

After installation, agents should still start from the same compact current operating contract. A module becomes visible when it is relevant to the current decision; an irrelevant installed module should remain out of first-line context.

Do not teach agents a module command sequence as the normal workflow. Follow the current routed operation, skill, selector, or owner.

## What stays secondary

Direct module CLIs, module-local lifecycle commands, internal manifests, and debugging workflows are real but secondary. Use them when the current route or maintainer task explicitly requires module-level control.

Exact installed surfaces and current command details belong in generated/reference owners rather than this chooser.

## Read next

- Package overview: [`docs/package/overview.md`](package/overview.md)
- Module contribution model: [`docs/package/modules.md`](package/modules.md)
- Extensibility boundary: [`docs/extension-boundary.md`](extension-boundary.md)
- Installed surfaces: [`docs/package/installed-surfaces.md`](package/installed-surfaces.md)
- Memory module: [`packages/memory/README.md`](../packages/memory/README.md)
- Planning module: [`packages/planning/README.md`](../packages/planning/README.md)
- Verification module: [`packages/verification/README.md`](../packages/verification/README.md)
- Architecture: [`docs/architecture.md`](architecture.md)