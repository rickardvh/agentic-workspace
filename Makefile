-include .env.local

UV_CACHE_DIR ?= $(CURDIR)/.uv-cache-root
export UV_CACHE_DIR
PYTEST_PARALLEL_ARGS ?= -n auto
COMPACT_RUN = uv run python scripts/check/run_compact_command.py

.PHONY: help sync-all sync-memory sync-planning \
	setup install-hooks \
	test test-workspace test-memory test-planning \
	lint lint-workspace lint-memory lint-planning markdownlint markdownlint-memory \
	typecheck typecheck-workspace typecheck-memory typecheck-planning \
	format format-workspace format-memory format-planning \
	format-check format-check-workspace format-check-memory format-check-planning \
	verify verify-workspace verify-memory verify-planning \
	memory-freshness memory-freshness-strict recurring-friction-ledger planning-surfaces planning-surfaces-strict source-payload-operational-install source-payload-operational-install-strict maintainer-surfaces maintainer-surfaces-strict render-agent-docs absolute-paths \
	check check-memory check-planning check-all

help:
	@echo "Available targets:"
	@echo "  help                 Show this help."
	@echo "  setup                Sync the dev environment and install local git hooks."
	@echo "  install-hooks        Install the repo-managed local git hooks for this clone."
	@echo "  sync-all             Sync merged root environment for all workspace packages."
	@echo "  sync-memory          Sync consolidated root dev environment for memory package checks."
	@echo "  sync-planning        Sync consolidated root dev environment for planning package checks."
	@echo "  test                 Run workspace and package test suites with pytest-xdist."
	@echo "                       Override worker selection with PYTEST_PARALLEL_ARGS='-n <count>' or empty."
	@echo "  lint                 Run non-mutating lint checks across workspace and packages."
	@echo "  markdownlint         Run Markdown lint checks for the memory package surfaces."
	@echo "  typecheck            Run ty type checks across workspace and packages."
	@echo "  format               Apply Ruff formatting across workspace and packages."
	@echo "  format-check         Run formatting checks across workspace and packages."
	@echo "  verify               Verify workspace CLI wiring and both packaged payload contracts."
	@echo "  memory-freshness     Run the root memory freshness audit."
	@echo "  recurring-friction-ledger  Run the root recurring-friction ledger audit."
	@echo "  planning-surfaces    Run the root planning surface audit."
	@echo "  source-payload-operational-install  Run source/payload/root-install boundary checks."
	@echo "  maintainer-surfaces  Run maintainer-surface freshness and liveness checks."
	@echo "  render-agent-docs    Regenerate root planning docs from the managed manifest."
	@echo "  absolute-paths       Fail if tracked files contain absolute filesystem paths."
	@echo "  check                Run the full root validation lane."
	@echo "  check-memory         Run package-local checks for packages/memory."
	@echo "  check-planning       Run package-local checks for packages/planning."
	@echo "  check-all            Run checks for both imported packages."

sync-all:
	@$(COMPACT_RUN) --label "sync-all" -- uv sync --all-packages --all-groups

install-hooks:
	uv run python scripts/install_git_hooks.py

setup: sync-all install-hooks

sync-memory:
	@$(COMPACT_RUN) --label "sync-memory" -- uv sync --all-packages --group dev

sync-planning:
	@$(COMPACT_RUN) --label "sync-planning" -- uv sync --all-packages --group dev

test-workspace:
	@$(COMPACT_RUN) --label "workspace tests" -- uv run pytest $(PYTEST_PARALLEL_ARGS) tests

test-memory:
	@$(COMPACT_RUN) --label "memory tests" --cwd packages/memory -- uv run pytest $(PYTEST_PARALLEL_ARGS)

test-planning:
	@$(COMPACT_RUN) --label "planning tests" --cwd packages/planning -- uv run pytest $(PYTEST_PARALLEL_ARGS)

test: sync-all test-workspace test-memory test-planning

lint-workspace:
	@$(COMPACT_RUN) --label "workspace lint" -- uv run ruff check src tests

lint-memory:
	@$(COMPACT_RUN) --label "memory lint" --cwd packages/memory -- uv run ruff check .
	@$(COMPACT_RUN) --label "memory markdownlint" --cwd packages/memory -- uv run pymarkdown -d md013,md024 scan AGENTS.md README.md bootstrap skills

lint-planning:
	@$(COMPACT_RUN) --label "planning lint" --cwd packages/planning -- uv run ruff check .

lint: sync-all lint-workspace lint-memory lint-planning

markdownlint-memory:
	@$(COMPACT_RUN) --label "memory markdownlint" --cwd packages/memory -- uv run pymarkdown -d md013,md024 scan AGENTS.md README.md bootstrap skills

markdownlint: sync-all markdownlint-memory

typecheck-workspace:
	@$(COMPACT_RUN) --label "workspace typecheck" -- uv run ty check src

typecheck-memory:
	@$(COMPACT_RUN) --label "memory typecheck" --cwd packages/memory -- uv run ty check src

typecheck-planning:
	@$(COMPACT_RUN) --label "planning typecheck" --cwd packages/planning -- uv run ty check src

typecheck: sync-all typecheck-workspace typecheck-memory typecheck-planning

format-workspace:
	@$(COMPACT_RUN) --label "workspace format" -- uv run ruff format src tests

format-memory:
	@$(COMPACT_RUN) --label "memory format" --cwd packages/memory -- uv run ruff format .

format-planning:
	@$(COMPACT_RUN) --label "planning format" --cwd packages/planning -- uv run ruff format .

format: sync-all format-workspace format-memory format-planning

format-check-workspace:
	@$(COMPACT_RUN) --label "workspace format-check" -- uv run ruff format --check src tests

format-check-memory:
	@$(COMPACT_RUN) --label "memory format-check" --cwd packages/memory -- uv run ruff format --check .

format-check-planning:
	@$(COMPACT_RUN) --label "planning format-check" --cwd packages/planning -- uv run ruff format --check .

format-check: sync-all format-check-workspace format-check-memory format-check-planning

verify-workspace:
	@$(COMPACT_RUN) --label "workspace verify" -- uv run agentic-workspace modules --format json

verify-memory:
	@$(COMPACT_RUN) --label "memory verify-payload" --cwd packages/memory -- uv run agentic-memory-bootstrap verify-payload --target .

verify-planning:
	@$(COMPACT_RUN) --label "planning verify-payload" --cwd packages/planning -- uv run agentic-planning-bootstrap verify-payload

verify: sync-all verify-workspace verify-memory verify-planning

memory-freshness:
	@$(COMPACT_RUN) --label "memory freshness" -- uv run python scripts/check/check_memory_freshness.py

memory-freshness-strict:
	@$(COMPACT_RUN) --label "memory freshness strict" -- uv run python scripts/check/check_memory_freshness.py --strict

recurring-friction-ledger:
	@$(COMPACT_RUN) --label "recurring friction ledger" -- uv run python scripts/check/check_recurring_friction_ledger.py

planning-surfaces:
	@$(COMPACT_RUN) --label "planning surfaces" -- uv run python scripts/check/check_planning_surfaces.py

planning-surfaces-strict:
	@$(COMPACT_RUN) --label "planning surfaces strict" -- uv run python scripts/check/check_planning_surfaces.py --strict

source-payload-operational-install:
	@$(COMPACT_RUN) --label "source-payload boundary" -- uv run python scripts/check/check_source_payload_operational_install.py

source-payload-operational-install-strict:
	@$(COMPACT_RUN) --label "source-payload boundary strict" -- uv run python scripts/check/check_source_payload_operational_install.py --strict

maintainer-surfaces: render-agent-docs planning-surfaces source-payload-operational-install verify-memory verify-planning
	@$(COMPACT_RUN) --label "maintainer surfaces" -- uv run python scripts/check/check_maintainer_surfaces.py

maintainer-surfaces-strict: render-agent-docs planning-surfaces-strict source-payload-operational-install-strict verify-memory verify-planning
	@$(COMPACT_RUN) --label "maintainer surfaces strict" -- uv run python scripts/check/check_maintainer_surfaces.py --strict

render-agent-docs:
	@$(COMPACT_RUN) --label "render agent docs" -- uv run python scripts/render_agent_docs.py

absolute-paths:
	@$(COMPACT_RUN) --label "absolute paths" -- uv run python scripts/check/check_no_absolute_paths.py

check-memory: sync-all test-memory lint-memory typecheck-memory verify-memory memory-freshness-strict recurring-friction-ledger

check-planning: sync-all test-planning lint-planning typecheck-planning maintainer-surfaces memory-freshness

check: sync-all test lint typecheck format-check verify memory-freshness-strict maintainer-surfaces absolute-paths

check-all: check-memory check-planning
