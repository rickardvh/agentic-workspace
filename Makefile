.PHONY: test lint typecheck format-check generated-check surface-check check build build-python build-typescript release-check

test:
	uv run --frozen pytest -q

lint:
	uv run --frozen ruff check src tests scripts

typecheck:
	uv run --frozen ty check src tests scripts

format-check:
	uv run --frozen ruff format --check src tests scripts

surface-check:
	uv run --frozen python scripts/check_v1_surface.py

generated-check:
	uv run --frozen python scripts/check_generated_contracts.py

check: lint typecheck format-check generated-check surface-check test

build: build-python build-typescript

build-python:
	uv build --wheel --sdist

build-typescript:
	npm pack ./typescript --pack-destination dist

release-check: check
	uv run --frozen python scripts/release_conformance.py
