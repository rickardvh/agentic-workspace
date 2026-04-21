---
name: memory-reporting
description: Point to the canonical memory reporting surfaces (freshness, routing health, cleanup signals, remediation) without reading raw memory files first.
---

# Memory Reporting

Use this skill when you need to answer memory-operating questions cheaply and consistently without opening raw `memory/**/*.md` first.

## Default read path (machine-readable first)

1. `uv run agentic-memory-bootstrap status --target . --format json`
2. If remediation is needed: `uv run agentic-memory-bootstrap doctor --target . --format json`

Treat `status` as the fast "what is wrong / what next" view, and `doctor` as the compact remediation guide.

## Freshness and staleness

- Fast audit: `uv run python scripts/check/check_memory_freshness.py`
- Strict audit (CI posture): `uv run python scripts/check/check_memory_freshness.py --strict`

If you need to check current-memory note shape and staleness specifically:

- `uv run agentic-memory-bootstrap current check --target . --format json`

## Anti-rediscovery health (routing and promotion pressure)

Use these when you want signals about whether the memory system is saving tokens or creating noise:

- Routing health and working-set pressure:
  - `uv run agentic-memory-bootstrap route-report --target . --format json`
- Promotion / elimination candidates (notes that should shrink, move to docs, or be replaced by tests/scripts):
  - `uv run agentic-memory-bootstrap promotion-report --target . --format json`

If you need "what should I load for this task" without guessing:

- `uv run agentic-memory-bootstrap route --target . --format json`

## Cleanup signals

Prefer cleanup signals surfaced via `status`/`doctor` first.
When work touched the memory system, re-run:

- `uv run python scripts/check/check_memory_freshness.py`
- `uv run agentic-memory-bootstrap status --target . --format json`

## Output expectations (for handoff)

When reporting memory state to another agent or a human:

- paste the `status --format json` result (or the minimal relevant fields)
- if action is required, include `doctor --format json` and name the specific remediation step you are taking

