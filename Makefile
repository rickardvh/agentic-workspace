test:
	uv run pytest tests/test_installer.py

doctor:
	uv run agentic-memory-bootstrap doctor --target .

verify-payload:
	uv run agentic-memory-bootstrap verify-payload

prompt-upgrade:
	uv run agentic-memory-bootstrap prompt upgrade --target .

check-memory:
	uv run python scripts/check/check_memory_freshness.py

lint:
	uv run ruff check . --fix

format:
	uv run ruff format .

typecheck:
	uv run ty check .
