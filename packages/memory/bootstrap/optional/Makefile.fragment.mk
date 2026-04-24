check-memory:
	uv run agentic-workspace doctor --target . --format json
	uv run agentic-workspace report --target . --format json
