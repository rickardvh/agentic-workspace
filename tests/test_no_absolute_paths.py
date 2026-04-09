from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_no_absolute_paths.py"
_SPEC = importlib.util.spec_from_file_location("check_no_absolute_paths", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
check_no_absolute_paths = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = check_no_absolute_paths
_SPEC.loader.exec_module(check_no_absolute_paths)


def test_scan_text_allows_relative_paths() -> None:
    findings = check_no_absolute_paths.scan_text(
        "Use ./repo and docs/setup.md.\n",
        path=check_no_absolute_paths.REPO_ROOT / "README.md",
    )

    assert findings == []


def test_scan_text_flags_windows_and_posix_absolute_paths() -> None:
    windows_path = "C:" + "/repo/docs"
    posix_path = "/" + "Users" + "/example/src/project"
    findings = check_no_absolute_paths.scan_text(
        f"Bad: {windows_path} and {posix_path}\n",
        path=check_no_absolute_paths.REPO_ROOT / "README.md",
    )

    assert [finding.value for finding in findings] == [windows_path, posix_path]
    assert findings[0].line == 1
    assert findings[0].column == 6


def test_scan_text_honours_exact_literal_allowlist(monkeypatch) -> None:
    allowed_path = "C:" + "/allowed-placeholder"
    blocked_path = "C:" + "/repo"
    monkeypatch.setattr(
        check_no_absolute_paths,
        "ALLOWED_LITERAL_EXCEPTIONS",
        frozenset({allowed_path}),
    )

    findings = check_no_absolute_paths.scan_text(
        f"Allowed {allowed_path} but not {blocked_path}\n",
        path=check_no_absolute_paths.REPO_ROOT / "README.md",
    )

    assert [finding.value for finding in findings] == [blocked_path]


def test_scan_file_skips_binary_files(tmp_path: Path) -> None:
    path = tmp_path / "image.bin"
    path.write_bytes(b"\0\1\2")

    assert check_no_absolute_paths.scan_file(path) == []
