.PHONY: test lint check-planning-surfaces check-planning-surfaces-json check-planning-surfaces-strict plan-check plan-check-json plan-check-strict plan-summary render-agent-docs check-memory
PYTEST_PARALLEL_ARGS ?= -n auto

PLANNING_CHECK_SCRIPT := scripts/check/check_planning_surfaces.py
ifeq (,$(wildcard $(PLANNING_CHECK_SCRIPT)))
PLANNING_CHECK_SCRIPT := ../../scripts/check/check_planning_surfaces.py
endif

MEMORY_CHECK_SCRIPT := scripts/check/check_memory_freshness.py
ifeq (,$(wildcard $(MEMORY_CHECK_SCRIPT)))
MEMORY_CHECK_SCRIPT := ../../scripts/check/check_memory_freshness.py
endif

RENDER_AGENT_DOCS_SCRIPT := scripts/render_agent_docs.py
ifeq (,$(wildcard $(RENDER_AGENT_DOCS_SCRIPT)))
RENDER_AGENT_DOCS_SCRIPT := ../../scripts/render_agent_docs.py
endif

test:
	uv run pytest $(PYTEST_PARALLEL_ARGS)

lint:
	uv run ruff check .

check-planning-surfaces:
	uv run python $(PLANNING_CHECK_SCRIPT)

check-planning-surfaces-json:
	uv run python $(PLANNING_CHECK_SCRIPT) --format json

check-planning-surfaces-strict:
	uv run python $(PLANNING_CHECK_SCRIPT) --strict

plan-check:
	uv run python $(PLANNING_CHECK_SCRIPT)

plan-check-json:
	uv run python $(PLANNING_CHECK_SCRIPT) --format json

plan-check-strict:
	uv run python $(PLANNING_CHECK_SCRIPT) --strict

plan-summary:
	uv run python $(PLANNING_CHECK_SCRIPT) --format json

render-agent-docs:
	uv run python $(RENDER_AGENT_DOCS_SCRIPT)

check-memory:
	uv run python $(MEMORY_CHECK_SCRIPT)
