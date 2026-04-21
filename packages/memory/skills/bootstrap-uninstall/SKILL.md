---
name: bootstrap-uninstall
description: Finish bootstrap removal conservatively after the CLI has removed the safe bootstrap-managed files. Use when uninstall leaves manual-review items such as customised notes or repo-local memory additions.
---

# Bootstrap Uninstall

Use this skill after `agentic-memory-bootstrap uninstall`.

It handles the manual-review part of uninstall without deleting repo-local content blindly.

## Workflow

1. Read the uninstall output and separate:
   - safe removals already applied
   - repo-local memory files left for manual review
   - customised bootstrap-managed files that differ from payload
2. Review the remaining memory surface:
   - `AGENTS.md` if it still exists
   - remaining files under `.agentic-workspace/memory/repo/`
   - remaining `scripts/check/` files related to bootstrap
3. Remove repo-local memory files only when the repository should no longer keep that knowledge.
4. Preserve anything that the repo still intentionally wants, even if the bootstrap is otherwise being removed.
5. Confirm the final steady state:
   - no unwanted bootstrap-managed files remain
   - any intentionally retained repo-local files are explicit

## Guardrails

- Do not delete customised files blindly.
- Treat repo-local added notes and skills as manual-review content.
- Prefer explicit reporting over guessing whether a remaining file should stay.

## Typical outputs

- a concise uninstall review
- remaining manual-review items called out clearly
- a final statement of what was removed and what was intentionally left
