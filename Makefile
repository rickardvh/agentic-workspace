help:
	@echo "Available targets:"
	@echo "  help                 Show this help."
	@echo "  sync-all             Sync merged root environment for all workspace packages."
	@echo "  sync-memory          Sync package-scoped environment lane for memory package checks."
	@echo "  sync-planning        Sync package-scoped environment lane for planning package checks."
	@echo "  import-checklist     Show migration import checklist."
	@echo "  check-memory         Run package-local checks for packages/memory."
	@echo "  check-planning       Run package-local checks for packages/planning."
	@echo "  check-all            Run checks for both imported packages."

sync-all:
	uv sync --all-packages --all-groups

sync-memory:
	uv sync --package agentic-memory-bootstrap --group dev

sync-planning:
	uv sync --package agentic-planning-bootstrap --group dev

import-checklist:
	@echo "1) Import agentic-memory into packages/memory with history preservation"
	@echo "2) Import agentic-planning into packages/planning with history preservation"
	@echo "3) Run package-local tests and lint in both packages"
	@echo "4) Record source commit anchors in docs/migration/import-map.md"

check-memory:
	$(MAKE) sync-memory
	cd packages/memory && uv run pytest
	cd packages/memory && uv run ruff check .
	uv run python scripts/check/check_memory_freshness.py --strict

check-planning:
	$(MAKE) sync-planning
	cd packages/planning && uv run pytest
	cd packages/planning && uv run ruff check .
	uv run python scripts/check/check_planning_surfaces.py
	uv run python scripts/check/check_memory_freshness.py
	uv run python scripts/render_agent_docs.py

check-all: sync-all check-memory check-planning
