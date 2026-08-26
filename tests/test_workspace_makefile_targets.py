from __future__ import annotations

import os
import re
import subprocess
import tomllib
from collections import Counter
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]

SPLIT_TARGETS = {
    "test-workspace-cli": "WORKSPACE_TEST_CLI",
    "test-workspace-proof": "WORKSPACE_TEST_PROOF",
    "test-workspace-session-review": "WORKSPACE_TEST_SESSION_REVIEW",
    "test-workspace-contracts": "WORKSPACE_TEST_CONTRACTS",
    "test-workspace-generated-release": "WORKSPACE_TEST_GENERATED_RELEASE",
    "test-workspace-integration": "WORKSPACE_TEST_INTEGRATION",
}


def _makefile_text() -> str:
    return (WORKSPACE_ROOT / "Makefile").read_text(encoding="utf-8")


def _make_variable_items(text: str, variable: str) -> list[str]:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"^{re.escape(variable)}\s*(?::=|=)\s*", line):
            items: list[str] = []
            current = re.split(r":=|=", line, maxsplit=1)[1]
            for continuation in [current, *lines[index + 1 :]]:
                stripped = continuation.replace("\\", "").strip()
                if stripped:
                    items.extend(stripped.split())
                if not continuation.rstrip().endswith("\\"):
                    return items
    raise AssertionError(f"Missing Makefile variable: {variable}")


def test_workspace_split_targets_cover_root_test_files_once() -> None:
    text = _makefile_text()
    assigned = [item for variable in SPLIT_TARGETS.values() for item in _make_variable_items(text, variable)]
    counts = Counter(assigned)
    tracked_tests = sorted(path.relative_to(WORKSPACE_ROOT).as_posix() for path in (WORKSPACE_ROOT / "tests").glob("test_*.py"))

    assert sorted(assigned) == tracked_tests
    assert [item for item, count in counts.items() if count > 1] == []


def test_workspace_split_targets_preserve_serial_pytest_contract() -> None:
    text = _makefile_text()

    assert ".NOTPARALLEL: test-workspace" in text
    assert (
        "test-workspace: "
        "test-workspace-cli test-workspace-proof test-workspace-session-review "
        "test-workspace-contracts test-workspace-generated-release test-workspace-integration"
    ) in text

    for target, variable in SPLIT_TARGETS.items():
        parallel_variable = "WORKSPACE_PROOF_PYTEST_PARALLEL_ARGS" if target == "test-workspace-proof" else "WORKSPACE_PYTEST_PARALLEL_ARGS"
        pattern = re.compile(
            rf"^{re.escape(target)}:\n\t@\$\(COMPACT_RUN\) --label .+ -- uv run pytest "
            rf"\$\({parallel_variable}\) \$\({re.escape(variable)}\)$",
            re.MULTILINE,
        )
        assert pattern.search(text), f"{target} must run pytest through $({parallel_variable}) and $({variable})"
    assert "WORKSPACE_PYTEST_PARALLEL_ARGS ?= $(PYTEST_PARALLEL_ARGS)" in text
    assert "WORKSPACE_PROOF_PYTEST_PARALLEL_ARGS ?= $(PYTEST_PARALLEL_ARGS)" in text
    assert "PACKAGE_PYTEST_PARALLEL_ARGS ?= $(PYTEST_PARALLEL_ARGS)" in text
    assert "MEMORY_PYTEST_PARALLEL_ARGS ?= $(PACKAGE_PYTEST_PARALLEL_ARGS)" in text
    assert "PLANNING_PYTEST_PARALLEL_ARGS ?= $(PACKAGE_PYTEST_PARALLEL_ARGS)" in text
    assert "VERIFICATION_PYTEST_PARALLEL_ARGS ?= $(PACKAGE_PYTEST_PARALLEL_ARGS)" in text
    assert "check-bounded-parallel:" in text
    assert "$(MAKE) test-workspace-cli WORKSPACE_PYTEST_PARALLEL_ARGS='-n 16'" in text
    assert (
        "$(MAKE) -j 4 test-workspace-proof test-workspace-session-review test-workspace-contracts-measurement test-workspace-generated-release "
        "test-workspace-integration test-memory test-planning test-verification lint-nosync typecheck-nosync format-check-nosync "
        "verify-nosync memory-freshness-strict maintainer-surfaces validation-runtime-plan-measurement structured-file-inventory "
        "package-artifact-duplicates agent-aids absolute-paths composed-operation-scenarios WORKSPACE_PYTEST_PARALLEL_ARGS='-n 16' "
        "WORKSPACE_PROOF_PYTEST_PARALLEL_ARGS='-n 8' MEMORY_PYTEST_PARALLEL_ARGS='-n 8' PLANNING_PYTEST_PARALLEL_ARGS='' "
        "VERIFICATION_PYTEST_PARALLEL_ARGS='-n 8'"
    ) in text
    assert "validation-runtime-plan-measurement:" in text
    assert "check_validation_runtime_plan.py --measurement-phase" in text
    assert "not test_validation_runtime_plan_matches_makefile_ci_and_evidence" in text
    assert "validation-runtime-plan:\n" in text
    assert "test-workspace-contracts:\n" in text


def test_workspace_broad_suite_exposes_split_target_matrix() -> None:
    config = tomllib.loads((WORKSPACE_ROOT / ".agentic-workspace" / "config.toml").read_text(encoding="utf-8"))
    commands = config["assurance"]["domain_proof_lanes"]["workspace_broad_suite"]["commands"]

    assert commands == [f"make {target}" for target in SPLIT_TARGETS] + ["make lint-workspace"]


def test_makefile_exposes_setup_free_aggregate_targets() -> None:
    text = _makefile_text()

    assert "test-nosync: test-workspace test-memory test-planning test-verification" in text
    assert "test: sync-all test-nosync" in text
    assert "lint-nosync: lint-workspace lint-memory lint-planning lint-verification" in text
    assert "lint: sync-all lint-nosync" in text
    assert "typecheck-nosync: typecheck-workspace typecheck-memory typecheck-planning typecheck-verification" in text
    assert "typecheck: sync-all typecheck-nosync" in text
    assert "verify-nosync: verify-workspace verify-memory verify-planning verify-verification" in text
    assert "verify: sync-all verify-nosync" in text
    assert "check: sync-all check-nosync" in text


def test_makefile_exposes_local_packed_artifact_semantic_replay() -> None:
    text = _makefile_text()

    assert "packed-artifact-conformance:" in text
    assert "PACKED_ARTIFACT_DIR ?= $(CURDIR)/.agentic-workspace/local/packed-artifact-conformance" in text
    assert "PACKED_ARTIFACT_CONTEXT ?= local" in text
    assert (
        'run_generated_command_package_proof.py --packed-conformance --artifact-dir "$(PACKED_ARTIFACT_DIR)" '
        '--receipt-out "$(PACKED_ARTIFACT_RECEIPT)" --execution-context "$(PACKED_ARTIFACT_CONTEXT)"'
    ) in text


def test_makefile_allocates_fresh_top_level_run_and_preserves_admitted_child_join(tmp_path: Path) -> None:
    fixture = tmp_path / "validation-context.mk"
    fixture.write_text(
        f"include {(WORKSPACE_ROOT / 'Makefile').as_posix()}\n"
        "print-validation-context:\n"
        '\t@echo "$(VALIDATION_RUN_ID)|$(VALIDATION_JOIN_TOKEN)|$(VALIDATION_RUN_PROVENANCE)"\n',
        encoding="utf-8",
    )
    clean_environment = os.environ.copy()
    for key in ("VALIDATION_RUN_ID", "VALIDATION_JOIN_TOKEN", "VALIDATION_RUN_PROVENANCE"):
        clean_environment.pop(key, None)
    stale_environment = {**clean_environment, "VALIDATION_RUN_ID": "stale-run"}

    allocated = (
        subprocess.run(
            ["make", "-f", str(fixture), "print-validation-context"],
            cwd=WORKSPACE_ROOT,
            env=stale_environment,
            capture_output=True,
            text=True,
            check=True,
        )
        .stdout.strip()
        .strip('"')
    )
    allocated_run, allocated_token, provenance = allocated.split("|")
    assert allocated_run != "stale-run"
    assert allocated_token == f"join:{allocated_run}"
    assert provenance == "allocated-here"

    joined = (
        subprocess.run(
            ["make", "-f", str(fixture), "print-validation-context"],
            cwd=WORKSPACE_ROOT,
            env={**clean_environment, "VALIDATION_RUN_ID": allocated_run, "VALIDATION_JOIN_TOKEN": allocated_token},
            capture_output=True,
            text=True,
            check=True,
        )
        .stdout.strip()
        .strip('"')
    )
    assert joined == f"{allocated_run}|{allocated_token}|transported-child"


def test_root_check_does_not_expand_nested_sync_aggregates() -> None:
    text = _makefile_text()
    check_line = next(line for line in text.splitlines() if line.startswith("check-nosync:"))

    assert " test " not in f" {check_line} "
    assert " lint " not in f" {check_line} "
    assert " typecheck " not in f" {check_line} "
    assert " format-check " not in f" {check_line} "
    assert " verify " not in f" {check_line} "
    assert "test-nosync" in check_line
    assert "lint-nosync" in check_line
    assert "typecheck-nosync" in check_line
    assert "format-check-nosync" in check_line
    assert "verify-nosync" in check_line


def test_ci_uses_setup_free_targets_after_explicit_sync() -> None:
    workflow = (WORKSPACE_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "run: make sync-all" in workflow
    assert "run: make typecheck-nosync" in workflow
    assert "run: make check-${{ matrix.package }}-nosync" in workflow
    assert "run: make typecheck\n" not in workflow
    assert "run: make check-${{ matrix.package }}\n" not in workflow
