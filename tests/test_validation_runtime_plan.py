from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def _load_run_id_allocator():
    path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "allocate_validation_run_id.py"
    spec = importlib.util.spec_from_file_location("allocate_validation_run_id", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_automatic_validation_run_ids_do_not_collide_within_one_second_or_concurrently() -> None:
    allocator = _load_run_id_allocator()

    with ThreadPoolExecutor(max_workers=16) as pool:
        run_ids = list(pool.map(lambda _: allocator.allocate_validation_run_id(), range(128)))

    assert len(run_ids) == len(set(run_ids))
    assert all(run_id.startswith("local-") for run_id in run_ids)


def test_make_materializes_one_automatic_run_id_per_process(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    probe = tmp_path / "validation-id-probe.mk"
    probe.write_text(
        ".PHONY: validation-id-probe\nvalidation-id-probe:\n\t@echo $(VALIDATION_RUN_ID)\n\t@echo $(VALIDATION_RUN_ID)\n",
        encoding="utf-8",
    )

    def invoke() -> list[str]:
        fresh_environment = os.environ.copy()
        for key in ("VALIDATION_RUN_ID", "VALIDATION_JOIN_TOKEN", "VALIDATION_RUN_PROVENANCE"):
            fresh_environment.pop(key, None)
        result = subprocess.run(
            ["make", "--no-print-directory", "-f", str(root / "Makefile"), "-f", str(probe), "validation-id-probe"],
            cwd=root,
            env=fresh_environment,
            check=True,
            capture_output=True,
            text=True,
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    first = invoke()
    second = invoke()

    assert len(first) == 2 and first[0] == first[1]
    assert len(second) == 2 and second[0] == second[1]
    assert first[0] != second[0]


def test_stock_pre_commit_routes_through_the_repo_owned_composition() -> None:
    root = Path(__file__).resolve().parents[1]
    config = (root / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "entry: uv run python scripts/git_hooks/pre_commit.py" in config
    assert "entry: make format\n" not in config
    assert "entry: make lint\n" not in config
    assert "entry: make typecheck\n" not in config
