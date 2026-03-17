from __future__ import annotations

from pathlib import Path

from repo_memory_bootstrap import installer


def test_extract_make_targets_ignores_assignments_and_recipes() -> None:
    text = """
    .PHONY: lint test
    PYTHON ?= python

    lint test:
    \t$(PYTHON) -m pytest

    check-memory:
    \tpython scripts/check/check_memory_freshness.py
    """

    assert installer._extract_make_targets(text) == {
        ".PHONY",
        "lint",
        "test",
        "check-memory",
    }


def test_equivalent_optional_fragment_detail_detects_existing_makefile_target() -> None:
    existing = """
    check-memory:
    \t$(PYTHON) scripts/check/check_memory_freshness.py
    """
    fragment = """
    check-memory:
    \tpython scripts/check/check_memory_freshness.py
    """

    detail = installer._equivalent_optional_fragment_detail(
        target_file=Path("Makefile"),
        existing=existing,
        fragment=fragment,
    )

    assert detail == "equivalent Makefile target already present (check-memory)"


def test_equivalent_optional_fragment_detail_requires_matching_targets() -> None:
    detail = installer._equivalent_optional_fragment_detail(
        target_file=Path("Makefile"),
        existing="lint:\n\tpython -m ruff check .\n",
        fragment="check-memory:\n\tpython scripts/check/check_memory_freshness.py\n",
    )

    assert detail is None


def test_plan_optional_appends_skips_equivalent_makefile_target(tmp_path: Path) -> None:
    source_root = tmp_path / "payload"
    target_root = tmp_path / "target"
    (source_root / "optional").mkdir(parents=True)
    target_root.mkdir()

    fragment = "check-memory:\n\tpython scripts/check/check_memory_freshness.py\n"
    makefile = "check-memory:\n\t$(PYTHON) scripts/check/check_memory_freshness.py\n"

    (source_root / "optional" / "Makefile.fragment.mk").write_text(fragment, encoding="utf-8")
    (source_root / "optional" / "CONTRIBUTING.fragment.md").write_text("Contributing fragment\n", encoding="utf-8")
    (source_root / "optional" / "pull_request_template.fragment.md").write_text("PR fragment\n", encoding="utf-8")
    (target_root / "Makefile").write_text(makefile, encoding="utf-8")

    result = installer.InstallResult(target_root=target_root, dry_run=False)

    installer._plan_optional_appends(
        source_root,
        target_root,
        result,
        apply=True,
    )

    assert (target_root / "Makefile").read_text(encoding="utf-8") == makefile
    makefile_actions = [action for action in result.actions if action.path == target_root / "Makefile"]
    assert len(makefile_actions) == 1
    assert makefile_actions[0].kind == "skipped"
    assert makefile_actions[0].detail == "equivalent Makefile target already present (check-memory)"


def test_patch_agents_workflow_block_inserts_pointer_after_heading() -> None:
    existing = "# Agent Instructions\n\nRepo-local rules live here.\n"

    patched = installer._patch_agents_workflow_block(existing)

    assert installer.WORKFLOW_POINTER_BLOCK in patched
    assert patched.startswith("# Agent Instructions\n\n")
    assert patched.endswith("Repo-local rules live here.\n")
