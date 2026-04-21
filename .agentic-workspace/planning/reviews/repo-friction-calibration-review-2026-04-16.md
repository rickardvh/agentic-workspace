# Repo Friction Calibration Review

## Review Metadata

- Review mode: `ordinary-use-pull`
- Review question: Does recent agent-driven work in this repo tend to increase repo friction, reduce it, or mostly shift moderation burden into the same front-door hotspots?
- Main inputs inspected first:
  - `uv run agentic-workspace report --target . --format json`
  - `git log --stat --oneline -8`
  - `git log --name-only --pretty=format: -8`
  - recent workspace/improvement-latitude commits `f12e7d4`, `a43808a`, `d558a60`
- Default finding cap: 3

## Scope

- Inspect the current repo-friction evidence and a bounded recent sample of agent-driven work.
- Judge whether the shipped improvement-latitude posture is justified for this repo.
- Identify only the repeated moderation or friction patterns that still matter after the current contract work.

## Non-Goals

- Do not turn this into a broad code-quality review.
- Do not reopen the just-landed workspace contract work unless the review shows it is still insufficient.
- Do not activate new work from the review alone unless the existing roadmap queue still needs it.

## Findings

### 1. The same front-door hotspots are still absorbing repeated agent-driven growth

- Source class: `friction-confirmed`
- Confidence: high
- Risk if unchanged: The repo can keep clarifying policy while still centralizing that clarity inside the same oversized implementation and test hotspots, which increases future edit cost and makes bounded cleanup more tempting but also more expensive.
- Evidence:
  - The current workspace report shows `[src/agentic_workspace/cli.py](../src/agentic_workspace/cli.py)` at 5134 lines and `[tests/test_workspace_cli.py](../tests/test_workspace_cli.py)` at 2433 lines under `repo_friction.large_file_hotspots`.
  - In the last eight commits, `src/agentic_workspace/cli.py`, `tests/test_workspace_cli.py`, and `ROADMAP.md` were each touched six times, with `[.agentic-workspace/docs/reporting-contract.md](reporting-contract.md)`, `[docs/delegated-judgment-contract.md](delegated-judgment-contract.md)`, and `[docs/workspace-config-contract.md](workspace-config-contract.md)` also recurring.
  - The recent improvement-latitude tranche itself (`f12e7d4`, `a43808a`, `d558a60`) kept adding value, but it still landed primarily in those same surfaces.
- Suggested action: Keep the repo posture `proactive`, but use it to justify bounded structural cleanup of repeated front-door hotspots when the current slice already owns them instead of continuing to let them accrete.
- Promotion target and trigger: no new promotion needed; this is now covered by the shipped repo-friction evidence and policy lane.

### 2. Recent simplification has reduced moderation ambiguity more than it has reduced structural complexity

- Source class: `mixed`
- Confidence: high
- Risk if unchanged: The repo will make better decisions about when cleanup is allowed, but contributors may still keep paying a repeated cost in the same large code and concept surfaces because the product is clarifying boundaries faster than it is structurally burning down hotspots.
- Evidence:
  - `a43808a` added explicit `none` and `reporting` modes, which removes a false choice between silence and autonomous cleanup and materially reduces moderation ambiguity.
  - `d558a60` added concept-surface hotspots, a queryable decision test, and a workspace-level ownership rule, which further reduces hidden judgment cost.
  - The current report now exposes both code and concept friction, but the leading concept hotspots are still large surfaces such as `[docs/design-principles.md](design-principles.md)` and `[.agentic-workspace/memory/repo/manifest.toml](../.agentic-workspace/memory/repo/manifest.toml)`, which means conceptual weight is still real even as the boundary story improves.
- Suggested action: Treat the current `proactive` repo posture as justified for this repo, but calibrate it toward bounded cleanup of repeated hotspots and low-pull visible surfaces rather than toward creating more machinery.
- Promotion target and trigger: dismiss as a separate queue item now that the calibration has been folded into shipped policy/reporting surfaces.

## Dismissed Or Deferred

- No evidence that the repo should drop back from `proactive` to `balanced` or `conservative`; the current repo remains agent-driven enough that lower initiative would likely preserve moderation burden rather than remove it.
- No evidence that this lane needs a new module; the shipped workspace-level ownership rule is the right boundary for the current problem.
- No new top-priority queue item is justified beyond the already-open planning-residue follow-through lane.

## Recommended Outcome

- Close the current top-priority improvement-latitude / repo-friction issues as satisfied by the shipped contract plus this calibration review.
- Keep the repo-configured `workspace.improvement_latitude = "proactive"` in this repo.
- Let the next promoted work move to the planning-residue lane rather than reopening improvement-latitude immediately.

## Validation / Inspection Commands Used

- `uv run agentic-workspace report --target . --format json`
- `git log --stat --oneline -8`
- `git log --name-only --pretty=format: -8`
