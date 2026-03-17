---
name: bootstrap-upgrade
description: Upgrade an already bootstrapped repository safely. Use when a repo has an installed bootstrap version and needs `doctor` plus `upgrade` review, replacement of shared repo-agnostic files, manual handling of local workflow docs, or verification that optional fragments and starter notes were treated conservatively.
---

# Bootstrap Upgrade

Use this skill to move an existing repo to the current bootstrap version without flattening local customisation.

## Workflow

1. Read the target repo's local contract:
   - `AGENTS.md`
   - `memory/index.md`
   - `memory/system/WORKFLOW.md`
   - `memory/current/project-state.md` if present
   - `memory/current/task-context.md` if present
2. Run `agentic-memory-bootstrap doctor --target <repo>`.
3. Run `agentic-memory-bootstrap upgrade --dry-run --target <repo>`.
4. Separate the plan into:
   - safe shared replacements
   - manual-review items
   - optional append targets
5. Apply the safe upgrade actions.
6. Manually review local files that the tool deliberately leaves alone:
   - `AGENTS.md`
   - repo-local task-system notes or planning docs
   - customised seed notes
7. If the shared workflow changed, check whether the repo's local contract still keeps task tooling separate from memory.
8. Verify the result:
   - rerun `doctor`
   - run the memory freshness audit when available
   - review the final diff for accidental duplicate appends or local-doc drift

## Guardrails

- Never assume a shared file should replace a repo-local file with active customisation.
- Treat task-system-specific local docs as manual-review surfaces.
- Preserve repo-specific scope, commands, and guardrails in `AGENTS.md`.
- If a repo already has an equivalent optional fragment, keep the existing behaviour and avoid duplicate appends.

## Typical outputs

- a reviewed upgrade plan
- shared bootstrap files updated to the new version
- local docs aligned manually where needed
- post-upgrade verification notes and a clear statement of the active memory surfaces
