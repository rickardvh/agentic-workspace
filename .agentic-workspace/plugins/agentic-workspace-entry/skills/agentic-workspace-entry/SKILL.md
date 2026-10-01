---
name: agentic-workspace-entry
description: Enter the current repository's AW procedure when doing repository work with agentic-workspace present. Use only for that repository, including subdirectory or linked-worktree tasks.
---

# Enter the target repository's procedure

Identify the working tree being worked on from the task's repository context.
For a subdirectory, use the existing Git working-tree context when needed (for
example, `git -C <task-directory> rev-parse --show-toplevel`). A linked worktree
has its own root; `.git` need not be a directory. Do not select the plugin cache,
package directory, process home, another checkout or an enclosing repository.
Do not scan repositories to find an AW installation.

At that root, read `.agentic-workspace/skills/workspace-startup/SKILL.md` and
follow its current contents. Resolve its relative references from that skill's
directory. The repository's procedure owns everything after this handoff.

If `.agentic-workspace/` is absent and the current repository instructions do
not identify AW, finish this entry quietly. Do not install, set up, contact a
service or probe a runtime. If the repository is known to use AW but its entry
cannot be read, report that exact path and gap; do not claim successful entry
or invent repair authority.

When another entry already supplied the same current repository procedure,
reuse it under that procedure's context and currentness boundary. Do not repeat
entry merely because this bridge is also installed, or create a session marker.
