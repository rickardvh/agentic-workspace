# Review-Skill Auto-Routing Hardening

## Goal

- Make review-shaped requests naturally route through the bundled planning review skill without requiring the user to know the skill id or explicitly ask for skill discovery first.

## Non-Goals

- Do not redesign the whole skill system.
- Do not implement every deferred skill-review finding in this slice.
- Do not force skills onto unstable or one-off workflows.

## Active Milestone

- ID: review-skill-auto-routing-hardening
- Status: completed
- Scope: harden the skill-discovery contract and planning startup guidance for review-shaped tasks, strengthen review-skill activation hints, and add regression coverage proving the workspace recommends the review skill for natural review requests.
- Ready: ready
- Blocked: none

## Immediate Next Action

- Archive this execplan and promote the next queued skill-system finding once the planning surfaces are refreshed cleanly.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `.agentic-workspace/planning/execplans/review-skill-auto-routing-hardening-2026-04-09.md`
- `docs/skill-discovery-contract.md`
- `packages/planning/skills/REGISTRY.json`
- `packages/planning/bootstrap/.agentic-workspace/planning/agent-manifest.json`
- `.agentic-workspace/planning/agent-manifest.json`
- `tools/AGENT_QUICKSTART.md`
- `tools/AGENT_ROUTING.md`
- `tests/test_workspace_cli.py`
- `packages/planning/tests/test_skills_catalog.py`

## Invariants

- Users should not need to know skill ids.
- Skills should be used aggressively for stable, repeatable workflows, not forced onto every task.
- Package-managed contract changes must update payload and root install together before the repo relies on them.

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py`
- `cd packages/planning && uv run pytest tests/test_skills_catalog.py tests/test_installer.py`
- `make maintainer-surfaces`
- `uv run agentic-planning-bootstrap upgrade --target .`

## Completion Criteria

- The skill-discovery contract says review-shaped requests should consult the skill layer before generic reasoning.
- Review-skill activation hints cover natural review requests better than before.
- Workspace CLI tests prove review-shaped requests recommend `planning-review-pass`.
- Root installed planning surfaces reflect the updated contract.

## Drift Log

- 2026-04-09: Promoted from the skill-system review after dogfooding showed that review skills were still not being selected automatically enough in normal repo work.
- 2026-04-09: Completed by tightening the skill-discovery consultation contract, expanding review-skill activation hints, and proving natural review requests recommend `planning-review-pass`.
