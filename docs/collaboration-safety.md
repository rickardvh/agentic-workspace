# Working safely with multiple branches and agents

AW stores shared project information in Git rather than hiding it in a separate
service. That makes changes visible and portable, but it does not make concurrent
edits magically conflict-free.

Use normal Git discipline: keep shared files small, isolate task-specific records,
and resolve overlapping edits deliberately.

## What works well

- Checked-in AW files use ordinary branch, diff, review and merge behaviour.
- Planning can keep separate records for separate work items instead of one giant
  shared task file.
- Useful long-term knowledge can live in Memory or project documentation rather
  than in chat history.
- Generated files can be recreated from their source when a merge damages them.
- `agentic-workspace start` can report current restrictions or missing setup
  information before an agent makes a dependent change.

## Where conflicts can still happen

- Two branches editing the same plan, Memory note or configuration file can
  conflict like any other same-file edit.
- Configuration and responsibility changes deserve careful review because they
  can change how later agents work.
- JSON and TOML are reviewable, but a manual merge can still produce invalid or
  contradictory data.

AW is therefore **Git-friendly, not multi-writer safe**.

## Reduce avoidable conflicts

- Keep task-specific Planning records separate.
- Remove or archive completed task state when it no longer helps future work.
- Prefer several focused Memory notes over one broad frequently edited note.
- Edit project documentation directly when it is the real source of a rule.
- Change generated files through their source and regenerate them.
- Use AW's supported operations for package-managed records instead of hand-editing
  files whose format or checks you would otherwise have to reconstruct.
- Keep meaningful follow-up work in Planning, Memory, documentation or an issue
  rather than only in chat.

## Resolve a merge involving AW files

First identify what each file represents.

- A project-owned instruction or configuration change is resolved like other
  project policy: compare the intended rules and choose the correct final text.
- A Planning or Memory record should preserve the useful information from both
  branches without creating duplicate “current” answers.
- A generated file should normally be regenerated from the resolved source rather
  than merged by hand.
- If AW reports that a package-managed file has been edited unexpectedly, follow
  the recovery or refresh instruction it returns instead of overwriting it.

After resolving the source files, run the checks appropriate to the changed files
and inspect the resulting diff.

## Generated files

Treat a generated file as a view of another source, not as a second handbook.

Prefer this order:

1. resolve the source schema, manifest, template or package file;
2. regenerate the derived file using the repository's existing command;
3. review the generated diff.

## Before finishing

Look for shared files that have grown into conflict magnets. Split or remove them
when a more focused record would make future collaboration cheaper.

These are ordinary Git maintenance decisions, not locks or special AW workflow
stages.
