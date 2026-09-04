.PHONY: test lint typecheck format-check surface-check check build

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

check: lint typecheck format-check surface-check test

build:
	uv build --wheel --sdist
