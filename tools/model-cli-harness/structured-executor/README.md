# Structured Executor reference kernel

This directory contains the maintainer-only phase-1a reference kernel for
GitHub issue #2822. It is evaluation infrastructure under the model CLI
harness, not a shipped Agentic Workspace command, public contract, or durable
repository state owner.

The kernel has three boundaries:

- `kernel.py` is a pure reducer over bounded referential state.
- `store.py` owns atomic scratch persistence, content-addressed artifacts,
  journal recovery, and restart re-observation.
- `replay.py` reconstructs semantic identities without invoking models, AW,
  subprocesses, the network, or repository mutation.

Large packets, patches, results, and future model responses belong in separate
content-addressed artifacts. The state keeps references only. A restart is a
committed deterministic transition and forces authoritative domain
re-observation before any action candidate can be selected.

Maintainer entrypoints:

```text
python tools/model-cli-harness/structured-executor/structured_executor.py validate --state <state.json>
python tools/model-cli-harness/structured-executor/structured_executor.py replay --initial-state <state.json> --transitions <inputs.json>
```

Local run state belongs below the ignored
`.agentic-workspace/local/scratch/runs/<run-id>/` owner. Checked-in fixtures are
compact conformance evidence; transition logs are never the working context or
repository authority.
