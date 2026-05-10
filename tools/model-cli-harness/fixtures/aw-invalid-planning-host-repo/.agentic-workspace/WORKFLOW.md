# Agentic Workspace Workflow

Use this compact fallback only when CLI or JSON surfaces are unavailable.

1. Read the repo startup file and this file.
2. Decide whether the work is direct, bounded, lane, or epic.
3. If changed paths are already known and CLI is available, prefer `uv run agentic-workspace implement --changed <paths> --format json` for the smallest implementer context.
4. If the CLI is unavailable and the request is startup-only, orientation-only, or asks you not to implement yet, stop after reporting the intended command, the work-shape assumption, and that validation commands are unavailable until the command can run. Do not invent substitute validation commands. Do not search planning directories, templates, schemas, or unrelated repo files to reconstruct command output.
5. If the request is startup-only, orientation-only, or asks you not to implement yet without asking for durable handoff, stay read-only: report the command you would have run, the work shape, and the next safe action. Do not create planning files.
6. For direct or bounded work, proceed with the smallest local reasoning and validation that fits the change; create Planning state only when restart cost or durable handoff is actually part of the request.
7. For lane or epic work, use package-owned scaffolds first; edit checked-in planning files directly only as bounded fallback.
8. Run the narrowest validation that proves the changed surface.

This file is startup/router guidance, not task state. Do not edit it to record task-specific plans, progress, decisions, or handoff notes.
