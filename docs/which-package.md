# Which Package Should I Install?

Use `agentic-workspace` as the public entrypoint.
Pick the preset that matches the repo problem.

Agentic Workspace is primarily a quiet repo-native capability layer. If you want the smallest useful core, start by checking whether the `memory` profile is enough.

The adoption question is whether the checked-in operating cost will pay back. Agentic Workspace is probably unnecessary when the repo is cheap to reread, tasks finish in one sitting, existing README notes and tests already carry the important rules, and there is little long-running intent, handoff, proof ambiguity, or recurring friction. It can still be valuable for solo work when the expensive handoff is to a future session, future branch, or future agent.

For the full shipped-package documentation map, use [`docs/index.md`](index.md). For capability status, documentation freshness, and role signals, use [`docs/documentation-status.md`](documentation-status.md). Keep the README as the stable public entrypoint rather than a status dashboard.

## Fast Chooser

Use `agentic-workspace defaults --section install_profiles --format json` for the compact preset chooser.

That query surface now owns the first-line answer for which preset fits the repo problem, what each profile is for, which partial-adoption combinations are supported, and why `memory` is usually the smallest starting point.

Use the thresholds this way:

- Use `memory` when agents repeatedly rediscover repo rules, invariants, traps, operator steps, or non-obvious subsystem boundaries.
- Use `planning` when work spans sessions or branches, proof expectations are non-obvious, agents need bounded handoff, or "done" often means one slice is done while the larger intent remains open.
- Use `full` when durable knowledge and active execution continuity are both recurring bottlenecks.
- Stay with ordinary repo docs and tests when they already make context, intent, and proof cheap enough to reconstruct.

## Compact Operating Map

Use `agentic-workspace defaults --section operating_questions --format json` for the compact question-to-surface map.

That query surface now owns the first-line answers for routine questions such as startup path, active state, combined workspace state, proof or ownership lookup, setup or handoff home, and mixed-agent posture.

For the common combined-state question, prefer `agentic-workspace preflight --target ./repo --format json` before the broader workspace report.

Use broader docs or raw files only when that compact surface says you still need them.

## What Stays Secondary

Direct package CLIs, package-local maintainer workflows, and debugging-oriented lifecycle paths are real but secondary. Use them only when you explicitly need module-level control, not for normal adoption.

## Read Next

- Package overview: [`docs/package/overview.md`](package/overview.md)
- Module responsibilities: [`docs/package/modules.md`](package/modules.md)
- Installed surfaces: [`docs/package/installed-surfaces.md`](package/installed-surfaces.md)
- Compact operating map and first question: [`.agentic-workspace/docs/compact-contract-profile.md`](../.agentic-workspace/docs/compact-contract-profile.md)
- Memory path: [`packages/memory/README.md`](../packages/memory/README.md)
- Planning path: [`packages/planning/README.md`](../packages/planning/README.md)
- Architecture: [`docs/architecture.md`](architecture.md)
