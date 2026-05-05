---
name: workspace-work-shape
description: Classify work shape and route direct, bounded, lane, or epic work before implementation.
---

# Workspace Work Shape

Use this skill before implementation when task size, proof cost, or handoff needs are unclear.

## Route

1. Run `agentic-workspace preflight --target . --format json`.
2. If changed paths are known, run `agentic-workspace implement --target . --changed <paths> --format json`.
3. Classify the request as `direct`, `bounded`, `lane`, or `epic`.
4. For `direct` work, keep workspace overhead minimal and prove with the obvious narrow command.
5. For `bounded` work, use compact planning or proof output when continuation, risk, or non-obvious validation matters.
6. For `lane` or `epic` work, stop before coding and create or continue checked-in Planning state.

## Output

Report the shape, why that shape fits, the required next command, and whether Planning state is optional, recommended, or required.
