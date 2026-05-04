# Agentic Workspace Workflow

Start from structured local evidence before changing files:

1. Run `agentic-workspace summary --target . --format json` for current work state.
2. Run `agentic-workspace config --target . --profile compact --format json` when repo operating settings, local runtime posture, reporting style, workflow obligations, delegation, or closeout trust can affect the task. Do not read raw config files unless compact output lacks a field needed for the current decision.
3. For direct wording edits, keep overhead minimal and do not create Planning state.
4. For bounded, lane, or epic-shaped work, use the Planning surfaces routed by summary before implementation.
5. Before closeout, report which configured settings affected your action, proof, delegation decision, or final response.

This file routes startup only. Durable task state belongs in Planning, Memory, issue, proof, or report surfaces routed by the CLI.
