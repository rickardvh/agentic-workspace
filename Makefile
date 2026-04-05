.PHONY: test lint check-planning-surfaces check-planning-surfaces-json check-planning-surfaces-strict plan-check plan-check-json plan-check-strict render-agent-docs check-memory

test:
	uv run pytest

lint:
	uv run ruff check .

check-planning-surfaces:
	uv run python scripts/check/check_planning_surfaces.py

check-planning-surfaces-json:
	uv run python scripts/check/check_planning_surfaces.py --format json

check-planning-surfaces-strict:
	uv run python scripts/check/check_planning_surfaces.py --strict

plan-check:
	uv run python scripts/check/check_planning_surfaces.py

plan-check-json:
	uv run python scripts/check/check_planning_surfaces.py --format json

plan-check-strict:
	uv run python scripts/check/check_planning_surfaces.py --strict

render-agent-docs:
	uv run python scripts/render_agent_docs.py

check-memory:
	uv run python scripts/check/check_memory_freshness.py
