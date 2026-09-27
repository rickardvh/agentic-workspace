---
name: workspace-resources
description: Create temporary task storage or a necessary isolated checkout, preserve useful work, and clean up through AW.
---

# Task resources

Keep direct work in the existing checkout. Use this method when a task needs
temporary files, an isolated checkout for a concrete conflict, or cleanup after
either. AW records which resource it created and what may be removed; an ignored
directory alone is not disposable. Read current repository policy before choosing
isolation.

Use [the question](procedure.md) or the same sources directly:

- [Decide whether storage or isolation is needed](references/select.md).
- [Create or change the selected resource](references/operation.md).
- [Reserve disposable build output in an isolated checkout](references/build.md).
- [Preserve needed files and remove the temporary resource](references/cleanup.md).
- [Recover after an interrupted resource operation](references/recovery.md).
- [Inspect local files whose ownership is unclear](references/hygiene.md).

Follow [exact owner carriage](../workspace-startup/references/owners.md).
Finish by confirming cleanup or reporting the exact preserved path and the
decision still needed. Reading this skill does not authorise deletion.
