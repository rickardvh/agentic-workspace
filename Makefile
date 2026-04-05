.PHONY: test lint check-planning-surfaces render-agent-docs

test:
	uv run pytest

lint:
	uv run ruff check .

check-planning-surfaces:
	uv run python scripts/check/check_planning_surfaces.py

render-agent-docs:
	uv run python scripts/render_agent_docs.py
