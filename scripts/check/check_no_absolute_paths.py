from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Keep these lists explicit and small. If a checked-in fixture truly needs to
# mention a literal absolute filesystem path, whitelist the exact literal here
# rather than weakening the detector globally.
ALLOWED_LITERAL_EXCEPTIONS = frozenset[str]()
ALLOWED_FILE_LITERAL_EXCEPTIONS: dict[Path, frozenset[str]] = {}

_POSIX_ROOT_NAMES = ("Users", "home", "tmp", "var", "etc", "opt", "srv", "mnt", "media", "root", "workspace", "workspaces")
_POSIX_PLACEHOLDER_ROOTS = (("absolute", "path"), ("path", "to"))

_TOKEN_TRAILING_PUNCTUATION = ".,:;!?)]}>\"'"

WINDOWS_ABSOLUTE_PATH = re.compile(r"(?<![A-Za-z0-9_./-])[A-Za-z]:[\\/]\S+")
POSIX_ABSOLUTE_PATH = re.compile(
    r"(?<![A-Za-z0-9_./-])(?:"
    + "|".join(
        [rf"/(?:{'|'.join(_POSIX_ROOT_NAMES)})\S*"]
        + [re.escape("/" + "/".join(parts)) + r"\S*" for parts in _POSIX_PLACEHOLDER_ROOTS]
    )
    + r")"
)


@dataclass(frozen=True, slots=True)
class Finding:
    path: Path
    line: int
    column: int
    value: str


def _tracked_files(repo_root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    return [repo_root / Path(raw.decode("utf-8")) for raw in result.stdout.split(b"\0") if raw]


def _is_allowed(path: Path, value: str) -> bool:
    repo_relative_path = path.relative_to(REPO_ROOT)
    return value in ALLOWED_LITERAL_EXCEPTIONS or value in ALLOWED_FILE_LITERAL_EXCEPTIONS.get(repo_relative_path, frozenset())


def _line_and_column(text: str, index: int) -> tuple[int, int]:
    line = text.count("\n", 0, index) + 1
    last_newline = text.rfind("\n", 0, index)
    column = index + 1 if last_newline == -1 else index - last_newline
    return line, column


def _find_matches(text: str) -> list[tuple[int, str]]:
    matches: list[tuple[int, str]] = []
    for pattern in (WINDOWS_ABSOLUTE_PATH, POSIX_ABSOLUTE_PATH):
        for match in pattern.finditer(text):
            value = match.group(0).rstrip(_TOKEN_TRAILING_PUNCTUATION)
            if value:
                matches.append((match.start(), value))
    matches.sort(key=lambda item: item[0])
    return matches


def scan_text(text: str, *, path: Path) -> list[Finding]:
    findings: list[Finding] = []
    for index, value in _find_matches(text):
        if _is_allowed(path, value):
            continue
        line, column = _line_and_column(text, index)
        findings.append(Finding(path=path, line=line, column=column, value=value))
    return findings


def scan_file(path: Path) -> list[Finding]:
    raw = path.read_bytes()
    if b"\0" in raw:
        return []
    return scan_text(raw.decode("utf-8", errors="ignore"), path=path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fail when tracked files contain absolute filesystem paths.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    parse_args(argv)

    findings: list[Finding] = []
    for path in _tracked_files(REPO_ROOT):
        if path.is_file():
            findings.extend(scan_file(path))

    if not findings:
        print("No absolute filesystem paths found in tracked files.")
        return 0

    print("Absolute filesystem paths found in tracked files:")
    for finding in findings:
        relative_path = finding.path.relative_to(REPO_ROOT).as_posix()
        print(f"{relative_path}:{finding.line}:{finding.column}: {finding.value}")
    print("If a literal absolute path must remain as a placeholder fixture, add the exact literal to the checker allowlist.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
