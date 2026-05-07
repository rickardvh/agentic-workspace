---
name: github-issue-creation
description: Create GitHub issues from this repo while preserving issue-template fields, labels, and post-create planning refresh.
---

# GitHub Issue Creation

Use this repo-owned skill before creating GitHub issues for this repository.

## Required Shape

1. Inspect or use the current `.github/ISSUE_TEMPLATE/*.yml` forms instead of hand-authoring an ad hoc issue body.
2. Pick the matching template kind:
   - `direction` for product direction, architecture, lanes, and bounded planning slices.
   - `bug` for correctness, reliability, or regression problems.
   - `review` for dogfooding friction, review gaps, trust gaps, and continuation or handoff friction.
3. Generate a template-shaped body with:
   - `uv run python .agentic-workspace/agent-aids/scripts/github-issue-body/new_github_issue_body.py --kind <kind> --title "<title>" --field <id>=<value> ... --format json`
4. Create the issue with the generated title, labels, and body.
5. Refresh and reconcile external intent after creating or editing issues:
   - `uv run agentic-workspace external-intent refresh-github --target . --state all --storage cache --format json`
   - `uv run agentic-workspace reconcile --format json`

## Rules

- Preserve the template headings in the body.
- Apply the labels emitted by the helper.
- Fill required fields with concrete evidence; do not leave `TODO` values in a created issue.
- Use `review` for dogfooding findings unless the finding is clearly a product direction or bug.
- If the helper output and the YAML template disagree, trust the YAML template and fix the helper.
