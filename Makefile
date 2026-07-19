-include .env.local

UV_CACHE_DIR ?= $(CURDIR)/.uv-cache-root
REVIEW_MAX_CYCLES ?= 3
export UV_CACHE_DIR
# Serial execution is the safe local default.  Callers that have measured
# capacity may explicitly opt in, for example: PYTEST_PARALLEL_ARGS='-n 4'.
PYTEST_PARALLEL_ARGS ?=
COMPACT_RUN = uv run python scripts/check/run_compact_command.py

.PHONY: help sync-all sync-memory sync-planning sync-verification \
	setup install-hooks \
	test test-workspace test-memory test-planning test-verification \
	lint lint-workspace lint-memory lint-planning lint-verification markdownlint markdownlint-memory \
	typecheck typecheck-workspace typecheck-memory typecheck-planning typecheck-verification \
	format format-workspace format-memory format-planning format-verification \
	format-check format-check-workspace format-check-memory format-check-planning format-check-verification \
	verify verify-workspace verify-memory verify-planning verify-verification \
	memory-freshness memory-freshness-strict recurring-friction-ledger planning-surfaces planning-surfaces-strict structured-file-inventory package-artifact-duplicates agent-aids source-payload-operational-install source-payload-operational-install-strict maintainer-surfaces maintainer-surfaces-strict render-agent-docs render-schema-reference render-command-packages schema-reference-docs absolute-paths \
	generated-command-packages generated-command-packages-docker \
	check check-memory check-planning check-verification check-all start-review-poller

help:
	@echo "Available targets:"
	@echo "  help                 Show this help."
	@echo "  setup                Sync the dev environment and install local git hooks."
	@echo "  install-hooks        Install the repo-managed local git hooks for this clone."
	@echo "  sync-all             Sync merged root environment for all workspace packages."
	@echo "  sync-memory          Sync consolidated root dev environment for memory package checks."
	@echo "  sync-planning        Sync consolidated root dev environment for planning package checks."
	@echo "  sync-verification    Sync consolidated root dev environment for verification package checks."
	@echo "  test                 Run workspace and package test suites serially by default."
	@echo "                       Opt into pytest-xdist only with PYTEST_PARALLEL_ARGS='-n <count>'."
	@echo "  lint                 Run non-mutating lint checks across workspace and packages."
	@echo "  markdownlint         Run Markdown lint checks for the memory package surfaces."
	@echo "  typecheck            Run ty type checks across workspace and packages."
	@echo "  format               Apply Ruff formatting across workspace and packages."
	@echo "  format-check         Run formatting checks across workspace and packages."
	@echo "  verify               Verify workspace CLI wiring and both packaged payload contracts."
	@echo "  memory-freshness     Run the root memory freshness audit."
	@echo "  recurring-friction-ledger  Run the root recurring-friction ledger audit."
	@echo "  planning-surfaces    Run the root planning surface audit."
	@echo "  structured-file-inventory  Check tracked JSON/TOML/YAML/YML files against the inventory."
	@echo "  package-artifact-duplicates  Check built package artifacts for duplicate archive members."
	@echo "  agent-aids           Check checked-in agent aid manifests and coverage."
	@echo "  source-payload-operational-install  Run source/payload/root-install boundary checks."
	@echo "  maintainer-surfaces  Run maintainer-surface freshness and liveness checks."
	@echo "  render-agent-docs    Regenerate root planning docs from the managed manifest."
	@echo "  render-schema-reference  Regenerate generated JSON Schema reference docs."
	@echo "  render-command-packages  Regenerate generated command package CLIs."
	@echo "  absolute-paths       Fail if tracked files contain absolute filesystem paths."
	@echo "  generated-command-packages  Run generated command package proof with compact output."
	@echo "  generated-command-packages-docker  Run generated command package Docker proof with compact output."
	@echo "  check                Run the full root validation lane."
	@echo "  check-memory         Run package-local checks for packages/memory."
	@echo "  check-planning       Run package-local checks for packages/planning."
	@echo "  check-verification   Run package-local checks for packages/verification."
	@echo "  check-all            Run checks for imported packages."
	@echo "  start-review-poller  Start one detached global PR-review poller for this checkout."

sync-all:
	@$(COMPACT_RUN) --label "sync-all" -- uv sync --all-packages --all-groups

install-hooks:
	uv run python scripts/install_git_hooks.py

setup: sync-all install-hooks

start-review-poller:
	@$(COMPACT_RUN) --label "review poller" -- uv run python tools/start_chatgpt_review_poller.py --target . --max-cycles $(REVIEW_MAX_CYCLES)

sync-memory:
	@$(COMPACT_RUN) --label "sync-memory" -- uv sync --all-packages --group dev

sync-planning:
	@$(COMPACT_RUN) --label "sync-planning" -- uv sync --all-packages --group dev

sync-verification:
	@$(COMPACT_RUN) --label "sync-verification" -- uv sync --all-packages --group dev

test-workspace:
	@$(COMPACT_RUN) --label "workspace tests" -- uv run pytest $(PYTEST_PARALLEL_ARGS) tests

test-memory:
	@$(COMPACT_RUN) --label "memory tests" --cwd packages/memory -- uv run pytest $(PYTEST_PARALLEL_ARGS)

test-planning:
	@$(COMPACT_RUN) --label "planning tests" --cwd packages/planning -- uv run pytest $(PYTEST_PARALLEL_ARGS)

test-verification:
	@$(COMPACT_RUN) --label "verification tests" --cwd packages/verification -- uv run pytest $(PYTEST_PARALLEL_ARGS)

test: sync-all test-workspace test-memory test-planning test-verification

lint-workspace:
	@$(COMPACT_RUN) --label "workspace lint" -- uv run ruff check src tests
	@$(COMPACT_RUN) --label "prompt semantic markers" -- uv run python scripts/check/check_prompt_semantic_markers.py

lint-memory:
	@$(COMPACT_RUN) --label "memory lint" --cwd packages/memory -- uv run ruff check .
	@$(COMPACT_RUN) --label "memory markdownlint" --cwd packages/memory -- uv run pymarkdown -d md013,md024 scan AGENTS.md README.md bootstrap skills

lint-planning:
	@$(COMPACT_RUN) --label "planning lint" --cwd packages/planning -- uv run ruff check .

lint-verification:
	@$(COMPACT_RUN) --label "verification lint" --cwd packages/verification -- uv run ruff check .

lint: sync-all lint-workspace lint-memory lint-planning lint-verification

markdownlint-memory:
	@$(COMPACT_RUN) --label "memory markdownlint" --cwd packages/memory -- uv run pymarkdown -d md013,md024 scan AGENTS.md README.md bootstrap skills

markdownlint: sync-all markdownlint-memory

typecheck-workspace:
	@$(COMPACT_RUN) --label "workspace typecheck" -- uv run ty check src

typecheck-memory:
	@$(COMPACT_RUN) --label "memory typecheck" --cwd packages/memory -- uv run ty check src

typecheck-planning:
	@$(COMPACT_RUN) --label "planning typecheck" --cwd packages/planning -- uv run ty check src

typecheck-verification:
	@$(COMPACT_RUN) --label "verification typecheck" --cwd packages/verification -- uv run ty check src

typecheck: sync-all typecheck-workspace typecheck-memory typecheck-planning typecheck-verification

format-workspace:
	@$(COMPACT_RUN) --label "workspace format" -- uv run ruff format src tests

format-memory:
	@$(COMPACT_RUN) --label "memory format" --cwd packages/memory -- uv run ruff format .

format-planning:
	@$(COMPACT_RUN) --label "planning format" --cwd packages/planning -- uv run ruff format .

format-verification:
	@$(COMPACT_RUN) --label "verification format" --cwd packages/verification -- uv run ruff format .

format: sync-all format-workspace format-memory format-planning format-verification

format-check-workspace:
	@$(COMPACT_RUN) --label "workspace format-check" -- uv run ruff format --check src tests

format-check-memory:
	@$(COMPACT_RUN) --label "memory format-check" --cwd packages/memory -- uv run ruff format --check .

format-check-planning:
	@$(COMPACT_RUN) --label "planning format-check" --cwd packages/planning -- uv run ruff format --check .

format-check-verification:
	@$(COMPACT_RUN) --label "verification format-check" --cwd packages/verification -- uv run ruff format --check .

format-check: sync-all format-check-workspace format-check-memory format-check-planning format-check-verification

verify-workspace:
	@$(COMPACT_RUN) --label "workspace verify" -- uv run agentic-workspace modules --format json

verify-memory:
	@$(COMPACT_RUN) --label "memory verify-payload" --cwd packages/memory -- uv run agentic-memory verify-payload --target .

verify-planning:
	@$(COMPACT_RUN) --label "planning verify-payload" --cwd packages/planning -- uv run agentic-planning verify-payload

verify-verification:
	@$(COMPACT_RUN) --label "verification report" --cwd packages/verification -- uv run agentic-verification report --target . --format json

verify: sync-all verify-workspace verify-memory verify-planning verify-verification

memory-freshness:
	@$(COMPACT_RUN) --label "memory doctor" -- uv run agentic-workspace doctor --target . --format json

memory-freshness-strict:
	@$(COMPACT_RUN) --label "memory report" -- uv run agentic-workspace report --target . --format json

recurring-friction-ledger:
	@$(COMPACT_RUN) --label "memory report" -- uv run agentic-workspace report --target . --format json

planning-surfaces:
	@$(COMPACT_RUN) --label "planning surfaces" -- uv run python scripts/check/check_planning_surfaces.py

planning-surfaces-strict:
	@$(COMPACT_RUN) --label "planning surfaces strict" -- uv run python scripts/check/check_planning_surfaces.py --strict

structured-file-inventory:
	@$(COMPACT_RUN) --label "structured file inventory" -- uv run python scripts/check/check_structured_file_inventory.py

package-artifact-duplicates:
	@$(COMPACT_RUN) --label "package artifact duplicates" -- uv run python scripts/check/check_package_artifact_duplicates.py

agent-aids:
	@$(COMPACT_RUN) --label "agent aid manifests" -- uv run python scripts/check/check_agent_aids.py

source-payload-operational-install:
	@$(COMPACT_RUN) --label "source-payload boundary" -- uv run python scripts/check/check_source_payload_operational_install.py

source-payload-operational-install-strict:
	@$(COMPACT_RUN) --label "source-payload boundary strict" -- uv run python scripts/check/check_source_payload_operational_install.py --strict

maintainer-surfaces: render-agent-docs schema-reference-docs planning-surfaces source-payload-operational-install verify-memory verify-planning
	@$(COMPACT_RUN) --label "maintainer surfaces" -- uv run python scripts/check/check_maintainer_surfaces.py

maintainer-surfaces-strict: render-agent-docs schema-reference-docs planning-surfaces-strict source-payload-operational-install-strict verify-memory verify-planning
	@$(COMPACT_RUN) --label "maintainer surfaces strict" -- uv run python scripts/check/check_maintainer_surfaces.py --strict

render-agent-docs:
	@$(COMPACT_RUN) --label "render agent docs" -- uv run python scripts/render_agent_docs.py

render-schema-reference:
	@$(COMPACT_RUN) --label "render schema reference" -- uv run python scripts/generate/generate_schema_reference.py

render-command-packages:
	@$(COMPACT_RUN) --label "render command packages" -- uv run python scripts/generate/generate_command_packages.py

schema-reference-docs:
	@$(COMPACT_RUN) --label "schema reference docs" -- uv run python scripts/generate/generate_schema_reference.py --check --check-annotations

absolute-paths:
	@$(COMPACT_RUN) --label "absolute paths" -- uv run python scripts/check/check_no_absolute_paths.py

generated-command-packages:
	@uv run python scripts/check/run_generated_command_package_proof.py --all

generated-command-packages-docker:
	@uv run python scripts/check/run_generated_command_package_proof.py

check-memory: sync-all test-memory lint-memory typecheck-memory verify-memory memory-freshness-strict recurring-friction-ledger

check-planning: sync-all test-planning lint-planning typecheck-planning maintainer-surfaces memory-freshness

check-verification: sync-all test-verification lint-verification typecheck-verification verify-verification
	@$(COMPACT_RUN) --label "generated command packages" -- uv run python scripts/check/check_generated_command_packages.py

check: sync-all test lint typecheck format-check verify memory-freshness-strict maintainer-surfaces structured-file-inventory package-artifact-duplicates agent-aids absolute-paths

check-all: check-memory check-planning check-verification
