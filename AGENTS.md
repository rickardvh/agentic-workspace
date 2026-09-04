# Agent Instructions

Resolve the current source-owned decision before non-trivial work:

```text
uv run --frozen --active --no-sync python scripts/run_agentic_workspace.py start --target . --task "<task>"
```

When the decision is actionable, execute its `primary_action` unchanged through
`agentic-workspace invoke`. Treat the returned `next_decision` as the current
answer; do not poll another status or continuation surface. Direct decisions do
not require durable Workspace state. Preserve unrelated and unknown repo-owned
content during every lifecycle operation.
