from __future__ import annotations

import re
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
        pattern = re.compile(
            rf"^{re.escape(target)}:\n\t@\$\(COMPACT_RUN\) --label .+ -- uv run pytest "
            rf"\$\(PYTEST_PARALLEL_ARGS\) \$\({re.escape(variable)}\)$",
            re.MULTILINE,
        )
        assert pattern.search(text), f"{target} must run pytest through $(PYTEST_PARALLEL_ARGS) and $({variable})"


def test_workspace_broad_suite_exposes_split_target_matrix() -> None:
    config = tomllib.loads((WORKSPACE_ROOT / ".agentic-workspace" / "config.toml").read_text(encoding="utf-8"))
    commands = config["assurance"]["domain_proof_lanes"]["workspace_broad_suite"]["commands"]

    assert commands == [f"make {target}" for target in SPLIT_TARGETS] + ["make lint-workspace"]
