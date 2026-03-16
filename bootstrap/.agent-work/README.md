# Agent Work

This directory is disposable working context for the current task.

Rules:

- `.agent-work/` should be git-ignored in the target repository.
- Use `.agent-work/` for temporary planning, findings, and handoff notes.
- Do not treat `.agent-work/` as durable technical memory.
- Durable knowledge belongs in `memory/`.
- Milestone state belongs in `TODO.md`.
- Before implementation, update `current-task.md` with:
  - task type
  - likely touched files
  - memory to load
  - memory to review
- Prune or overwrite stale `.agent-work/` content freely.
