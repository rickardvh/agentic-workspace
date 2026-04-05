.PHONY: help sync-all sync-memory sync-planning \
	test test-workspace test-memory test-planning \
	lint lint-workspace lint-memory lint-planning markdownlint markdownlint-memory \
	typecheck typecheck-workspace typecheck-memory typecheck-planning \
	format-check format-check-workspace format-check-memory format-check-planning \
	verify verify-workspace verify-memory verify-planning \
	memory-freshness memory-freshness-strict planning-surfaces planning-surfaces-strict render-agent-docs \
	check check-memory check-planning check-all

help:
	@echo "Available targets:"
	@echo "  help                 Show this help."
	@echo "  sync-all             Sync merged root environment for all workspace packages."
	@echo "  sync-memory          Sync consolidated root dev environment for memory package checks."
	@echo "  sync-planning        Sync consolidated root dev environment for planning package checks."
	@echo "  test                 Run workspace and package test suites."
	@echo "  lint                 Run non-mutating lint checks across workspace and packages."
	@echo "  markdownlint         Run Markdown lint checks for the memory package surfaces."
	@echo "  typecheck            Run ty type checks across workspace and packages."
	@echo "  format-check         Run formatting checks across workspace and packages."
	@echo "  verify               Verify workspace CLI wiring and both packaged payload contracts."
	@echo "  memory-freshness     Run the root memory freshness audit."
	@echo "  planning-surfaces    Run the root planning surface audit."
	@echo "  render-agent-docs    Regenerate root planning docs from the managed manifest."
	@echo "  check                Run the full root validation lane."
	@echo "  check-memory         Run package-local checks for packages/memory."
	@echo "  check-planning       Run package-local checks for packages/planning."
	@echo "  check-all            Run checks for both imported packages."

sync-all:
	uv sync --all-packages --all-groups

sync-memory:
	uv sync --all-packages --group dev

sync-planning:
	uv sync --all-packages --group dev

test-workspace:
	uv run pytest tests

test-memory:
	cd packages/memory && uv run pytest

test-planning:
	cd packages/planning && uv run pytest

test: sync-all test-workspace test-memory test-planning

lint-workspace:
	uv run ruff check src tests

lint-memory:
	cd packages/memory && uv run ruff check .
	cd packages/memory && uv run pymarkdown -d md013,md024 scan AGENTS.md README.md bootstrap skills

lint-planning:
	cd packages/planning && uv run ruff check .

lint: sync-all lint-workspace lint-memory lint-planning

markdownlint-memory:
	cd packages/memory && uv run pymarkdown -d md013,md024 scan AGENTS.md README.md bootstrap skills

markdownlint: sync-all markdownlint-memory

typecheck-workspace:
	uv run ty check src

typecheck-memory:
	cd packages/memory && uv run ty check src

typecheck-planning:
	cd packages/planning && uv run ty check src

typecheck: sync-all typecheck-workspace typecheck-memory typecheck-planning

format-check-workspace:
	uv run ruff format --check src tests

format-check-memory:
	cd packages/memory && uv run ruff format --check .

format-check-planning:
	cd packages/planning && uv run ruff format --check .

format-check: sync-all format-check-workspace format-check-memory format-check-planning

verify-workspace:
	uv run agentic-workspace modules --format json

verify-memory:
	cd packages/memory && uv run agentic-memory-bootstrap verify-payload --target .

verify-planning:
	cd packages/planning && uv run agentic-planning-bootstrap verify-payload

verify: sync-all verify-workspace verify-memory verify-planning

memory-freshness:
	uv run python scripts/check/check_memory_freshness.py

memory-freshness-strict:
	uv run python scripts/check/check_memory_freshness.py --strict

planning-surfaces:
	uv run python scripts/check/check_planning_surfaces.py

planning-surfaces-strict:
	uv run python scripts/check/check_planning_surfaces.py --strict

render-agent-docs:
	uv run python scripts/render_agent_docs.py

check-memory: sync-all test-memory lint-memory typecheck-memory verify-memory memory-freshness-strict

check-planning: sync-all test-planning lint-planning typecheck-planning verify-planning planning-surfaces memory-freshness render-agent-docs

check: sync-all test lint typecheck format-check verify memory-freshness-strict planning-surfaces render-agent-docs

check-all: check-memory check-planning
