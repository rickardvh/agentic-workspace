# Which Package Should I Install?

Use `agentic-workspace` as the public entrypoint.
Pick the preset that matches the repo problem.

Agentic Workspace is primarily a quiet repo-native capability layer. The lightweight operational profile is memory-first: useful when the repo needs durable knowledge and a small visible surface rather than checked-in active execution.

## Fast Chooser

Use `agentic-workspace defaults --section install_profiles --format json` for the compact preset chooser.

That query surface now owns the first-line answer for which preset fits the repo problem, what each profile is for, and which partial-adoption combinations are supported.

## Compact Operating Map

Use `agentic-workspace defaults --section operating_questions --format json` for the compact question-to-surface map.

That query surface now owns the first-line answers for routine questions such as startup path, active state, combined workspace state, proof or ownership lookup, setup or handoff home, and mixed-agent posture.

Use broader docs or raw files only when that compact surface says you still need them.

## What Stays Secondary

These are real but secondary:

- direct package CLIs
- package-local maintainer workflows
- debugging-oriented lifecycle paths

Use them when you explicitly need module-level control, not for normal adoption.

## Partial Adoption

Supported partial-adoption combinations are also listed in `agentic-workspace defaults --section install_profiles --format json`.

## Lightweight Operational Profile

If you want the smallest useful core, choose `memory`; the compact rationale now lives in `agentic-workspace defaults --section install_profiles --format json`.

## Read Next

- Compact operating map and first question: [`.agentic-workspace/docs/compact-contract-profile.md`](../.agentic-workspace/docs/compact-contract-profile.md)
- Memory path: [`packages/memory/README.md`](../packages/memory/README.md)
- Planning path: [`packages/planning/README.md`](../packages/planning/README.md)
- Architecture: [`docs/architecture.md`](architecture.md)
