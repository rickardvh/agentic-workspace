help:
	@echo "Available targets:"
	@echo "  help                 Show this help."
	@echo "  import-checklist     Show migration import checklist."

import-checklist:
	@echo "1) Import agentic-memory into packages/memory with history preservation"
	@echo "2) Import agentic-planning into packages/planning with history preservation"
	@echo "3) Run package-local tests and lint in both packages"
	@echo "4) Record source commit anchors in docs/migration/import-map.md"
