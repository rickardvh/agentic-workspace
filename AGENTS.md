# Agent Instructions

<!-- agentic-workspace:workflow:start -->
Read `.agentic-workspace/WORKFLOW.md` for shared workflow rules.
<!-- agentic-workspace:workflow:end -->

Local bootstrap contract for agents working in this monorepo.

## Precedence

Resolve instruction conflicts in this order:

1. Explicit user request.
2. `AGENTS.md`.
3. Package-local `AGENTS.md` under `packages/*/` once imported.
4. Routed memory or canonical repo docs when present.

## Startup Path

1. Read `AGENTS.md`.
2. Read `agentic-workspace summary --format json` for the compact planning state.
3. Read `agentic-workspace config --target . --format json` when the current posture or startup entrypoint matters.
4. Inspect `.agentic-workspace/planning/state.toml` only when the compact summary is insufficient and raw queue detail is still needed.
5. Read the active feature plan in `docs/execplans/` when the summary points there.
6. Inspect the roadmap data in `.agentic-workspace/planning/state.toml` only when promoting work.
7. Load package-local docs only for the package being edited.
8. Before touching a shipped package, refresh it to the latest checked-in version through that package's canonical update workflow so local work starts from the current package contract.
9. When a change crosses package source, package payload, and root install boundaries, read `docs/extraction-and-discovery-contract.md` before editing.
10. When making claims about GitHub issue state, verify the live issue set with `gh` instead of relying only on checked-in intake notes.

Do not start coding from chat context alone when the same information exists in checked-in files.
Do not bulk-read all planning surfaces.
When the question is active planning recovery rather than startup order, prefer `agentic-workspace summary --format json` and `agentic-workspace defaults --section startup --format json` before reopening broader planning prose.
Read `docs/routing-contract.md` when execution hits an edge case, routing ambiguity, or requires deep context on the operating model.
Read `docs/lifecycle-and-config-contract.md` before editing CLI initialization or configuration logic.

### Planning Continuity

- the execplan must record both `Intent Continuity` and `Required Continuation` before archive.
- Every active slice must belong to a larger intended outcome.
- record the required next owner and activation trigger explicitly before archive if the larger outcome is unfinished.
- keep `Iterative Follow-Through` current.
- remove or archive the matched planning residue in the same pass.

## Operating Rules

### Execution Posture

- Prefer task-by-task judgment about whether work should stay direct, be split into planner/implementer/validator subtasks, or be escalated to a stronger planner.
- Use the effective mixed-agent posture from `agentic-workspace config --target . --format json` when deciding how much to delegate and how much reasoning to spend.
- Treat `agentic-workspace.local.toml` as the control surface for capability/cost posture: if it says internal delegation or a strong planner is available, prefer that mode when it reduces cost or risk; if it does not, stay direct unless the task shape clearly justifies promotion or escalation.
- Do not require the user to restate this preference every session when the config already makes the posture clear.
- Keep the chosen execution shape bounded and explicit in checked-in planning when the task is broad enough to survive across sessions.

### Sources Of Truth

- Active queue and candidate lanes: `.agentic-workspace/planning/state.toml`
- Design constraints for future changes: `docs/design-principles.md`

### Repo Rules

- Keep package boundaries explicit.
- Preserve independent package versioning and CLI entry points.
- Treat line-ending-only drift in generated `tools/` mirrors as noise unless the canonical manifest or rendered content changed.
- In checked-in human-facing docs, keep links clickable but use repo-relative paths only; do not commit absolute filesystem paths in Markdown links or prose path references unless a non-repo absolute path is the subject of the documentation itself.

### Validation

- Run the narrowest validation that proves a change.
- Prefer package-local checks after package import.
- Add monorepo-wide checks only when cross-package integration changes.
- As a final repo-level test after package work, refresh the root install to the latest checked-in version of both shipped packages: `uv run agentic-planning-bootstrap upgrade --target .` and `uv run agentic-memory-bootstrap upgrade --target .`.
- When verifying that the repo is on the latest shipped package contract, distinguish payload freshness from repo-local advisory warnings: run the package upgrade flow, `verify-payload`, package/root doctor surfaces, and report separately whether remaining warnings are package drift or expected repo-local customisation/noise.

### Dogfooding Rule

- Treat this monorepo as the proving ground for shipped agent workflows.
- For detailed dogfooding and product doctrine, see `docs/design-principles.md`.
