---
name: package-context-inspection
description: Check a repository package-context note against current module sources when maintaining Planning or Memory boundaries.
---

# Check a package-context note

Use this procedure when a note about Planning or Memory conflicts with the module
being edited. Start with the note's current manifest disposition. A retired note
is historical evidence; do not restore its former package paths or revive it merely
because current code differs.

1. Identify the affected module in `src/core/src/modules/planning/` or
   `src/core/src/modules/memory/` and read its relevant source, declared payload and
   focused tests. Use [repository layout](../../../../../docs/maintainer/repository-layout.md)
   for the current locations.
2. Compare the note's durable ownership claims with those sources and the
   repository ownership ledger. Keep repeatable steps in a skill, rather than
   copying a workflow into the note.
3. If active advice is wrong, use the [correction procedure](../../../../skills/workspace-instruction-correction/SKILL.md)
   to choose its authorized destination. This checklist does not grant note-write
   or disposition authority.
4. Stop when the conflict is explained or the receiving component has verified
   the correction. Report an unsupported repair path instead of claiming retention.
