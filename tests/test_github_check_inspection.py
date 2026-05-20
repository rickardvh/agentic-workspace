import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "github" / "inspect_pr_checks.py"
SPEC = importlib.util.spec_from_file_location("inspect_pr_checks", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
inspect_pr_checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inspect_pr_checks)

compact_check_summary = inspect_pr_checks.compact_check_summary
extract_error_lines = inspect_pr_checks.extract_error_lines


def test_compact_check_summary_treats_missing_checks_as_pending_attach() -> None:
    payload = compact_check_summary([])

    assert payload["state"] == "pending_attach"
    assert "retry" in payload["summary"]


def test_compact_check_summary_infers_reproduction_without_log_tail() -> None:
    payload = compact_check_summary(
        [
            {
                "name": "package-checks (planning, 3.13)",
                "state": "failure",
                "workflowName": "CI",
                "link": "https://example.test/run",
            }
        ]
    )

    assert payload["state"] == "failed"
    assert payload["failing"] == [
        {
            "name": "package-checks (planning, 3.13)",
            "state": "failure",
            "workflow": "CI",
            "url": "https://example.test/run",
            "local_reproduction": "make check-planning",
        }
    ]


def test_extract_error_lines_omits_unrelated_passing_tail() -> None:
    lines = extract_error_lines("ok package\nERROR missing schema description\nall done passing tail\n")

    assert lines == ["ERROR missing schema description"]
