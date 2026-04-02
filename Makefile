help:
	@echo "Available targets:"
	@echo "  help            Show this help."
	@echo "  test            Run the installer test suite."
	@echo "  doctor          Run doctor against this repo."
	@echo "  verify-payload  Verify the packaged payload contract."
	@echo "  prompt-upgrade  Print the upgrade prompt for this repo."
	@echo "  check-memory    Run the memory freshness audit."
	@echo "  lint            Run Ruff and Markdown lint checks."
	@echo "  markdownlint    Run Markdown lint checks."
	@echo "  format          Run Ruff formatting."
	@echo "  typecheck       Run ty type checking."

test:
	uv run pytest tests/test_installer.py

coverage:
	uv run pytest

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
	uv run pymarkdown -d md013,md024 scan .

markdownlint:
	uv run pymarkdown -d md013,md024 scan .

format:
	uv run ruff format .

typecheck:
	uv run ty check .
