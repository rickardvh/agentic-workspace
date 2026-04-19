# Advanced Routing Contract

Use these rules when standard execution hits an edge case, ambiguity, or requires deep context.

## State Recovery and Setup
- When the question is startup or first-contact routing, prefer `agentic-workspace defaults --section startup --format json` and `agentic-workspace config --target ./repo --format json` before broader prose.
- When the question is active planning state, prefer `agentic-workspace summary --format json` before opening `TODO.md` or execplan prose.
- When the question is combined workspace state, prefer `agentic-workspace report --target ./repo --format json` before reading raw module files.
- Treat `docs/agent-installation.md` as the external install/adopt handoff only; after bootstrap, return to the configured startup entrypoint for normal repo work.

## External Context and Subtrees
- Read `docs/upstream-task-intake.md` when triaging external issues or tasks into checked-in planning.
- Before editing files in a subtree, read the nearest relevant descendant `AGENTS.md` for that subtree only.
- Read `memory/index.md` and `.agentic-workspace/memory/WORKFLOW.md` only when memory is installed and the plan or manifest does not already route the task, or when changing workflow, planning, or memory itself.

## Capability and Ambiguity
- When the task starts from a vague prompt, prefer `agentic-workspace defaults --section intent --format json`, `clarification`, `prompt_routing`, and `relay` before broad rereads, then open `docs/intent-contract.md` only if the compact selectors are not enough.
- When the task is clearly review-shaped, check `agentic-workspace skills --target ./repo --task "<task>" --format json` before falling back to generic reasoning so bundled review skills stay cheaper to use than rediscovery.
- Read `docs/capability-aware-execution.md` when task capability fit, delegation, or escalation is unclear, especially when the question is whether to silently reshape the work instead of prompting for a stronger executor.
- Read `docs/environment-recovery-contract.md` when interruption handling, environment assumptions, or recovery shape is unclear.
