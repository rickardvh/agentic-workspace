PYTEST_PARALLEL_ARGS ?= -n auto

help:
	@echo "Available targets:"
	@echo "  help            Show this help."
	@echo "  test            Run the installer test suite."
	@echo "  doctor          Run doctor against this repo."
	@echo "  verify-payload  Verify the packaged payload contract."
	@echo "  prompt-upgrade  Print the upgrade prompt for this repo."
	@echo "  check-memory    Run workspace doctor and report for memory health."
	@echo "  check-memory-strict  Alias for check-memory."
	@echo "  lint            Run Ruff and Markdown lint checks."
	@echo "  markdownlint    Run Markdown lint checks."
	@echo "  format          Run Ruff formatting."
	@echo "  typecheck       Run ty type checking."

test:
	uv run pytest $(PYTEST_PARALLEL_ARGS) tests/test_installer.py

coverage:
	uv run pytest $(PYTEST_PARALLEL_ARGS)

doctor:
	uv run agentic-memory-bootstrap doctor --target .

verify-payload:
	uv run agentic-memory-bootstrap verify-payload

prompt-upgrade:
	uv run agentic-memory-bootstrap prompt upgrade --target .

check-memory:
	uv run agentic-workspace doctor --target ../.. --format json
	uv run agentic-workspace report --target ../.. --format json

check-memory-strict:
	$(MAKE) check-memory

lint:
	uv run ruff check . --fix
	uv run pymarkdown -d md013,md024 scan AGENTS.md README.md bootstrap skills

markdownlint:
	uv run pymarkdown -d md013,md024 scan AGENTS.md README.md bootstrap skills

format:
	uv run ruff format .

typecheck:
	uv run ty check src
