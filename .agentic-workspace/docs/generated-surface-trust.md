# Generated Surface Trust

This page names the canonical sources and freshness rules for generated maintainer-facing surfaces.

Use it when a change touches a generated doc, routing mirror, or installed surface that should be rerendered instead of hand-edited.

## Canonical Sources

- `.agentic-workspace/planning/agent-manifest.json` is the canonical source for `tools/agent-manifest.json`, `tools/AGENT_QUICKSTART.md`, and `tools/AGENT_ROUTING.md`.
- `scripts/render_agent_docs.py` is the checked-in renderer for the root generated routing docs.
- Package payloads under `packages/memory/bootstrap/` and `packages/planning/bootstrap/` remain the canonical source for their installed payload mirrors and verify paths.

## Generated Surfaces

- `tools/agent-manifest.json`
- `tools/AGENT_QUICKSTART.md`
- `tools/AGENT_ROUTING.md`
- Any other repo mirror that is explicitly rendered from the canonical planning manifest or package payload source

## Trust Rules

- Never hand-edit a generated surface when a canonical source exists.
- Change the canonical source first, then rerender the mirror.
- Keep generated files visibly marked as generated so reviewers do not have to guess.
- Treat stale generated output as a contract drift, not a cosmetic diff.

## Validation

- `make maintainer-surfaces`
- `make render-agent-docs`

## Review Rule

If a change touches generated mirrors or their startup/routing behavior, verify the canonical source, rerender path, and freshness check together before closing the task.