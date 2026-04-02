#!/usr/bin/env python3
"""Advisory memory freshness audit.

Scan durable memory notes for missing required metadata, stale confirmations,
and growth signals. This is advisory and always exits with 0.
"""

from __future__ import annotations

import re
import tomllib
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

RE_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
RE_H1 = re.compile(r"^\s{0,3}#\s+(.+?)\s*$")
RE_LAST_CONFIRMED_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})\b")
RE_STATUS_VALUE = re.compile(r"^(Stable|Active|Needs verification|Deprecated)\s*$", re.IGNORECASE)

MEMORY_ROOT = Path("memory")
MANIFEST_PATH = MEMORY_ROOT / "manifest.toml"
MAX_LINES = 200
STALE_DAYS = 180

SKIP_FILES = {
    MEMORY_ROOT / "index.md",
    MANIFEST_PATH,
    MEMORY_ROOT / "domains" / "README.md",
    MEMORY_ROOT / "invariants" / "README.md",
    MEMORY_ROOT / "runbooks" / "README.md",
    MEMORY_ROOT / "decisions" / "README.md",
}
SKIP_DIRS = {
    MEMORY_ROOT / "bootstrap",
    MEMORY_ROOT / "skills",
    MEMORY_ROOT / "templates",
    MEMORY_ROOT / "system",
}


@dataclass
class NoteScan:
    path: Path
    title: str | None
    line_count: int
    has_last_confirmed: bool
    has_valid_last_confirmed_date: bool
    has_verify: bool
    has_load_when: bool
    has_review_when: bool
    has_failure_signals: bool
    has_needs_verification: bool
    newest_confirmed_date: datetime | None


def _normalise_label(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower().rstrip(":"))


def _label_match(line: str, target: str) -> bool:
    if _normalise_label(line) == target:
        return True
    match = RE_HEADING.match(line)
    return bool(match and _normalise_label(match.group(1)) == target)


def _iter_notes(root: Path) -> list[Path]:
    notes: list[Path] = []
    for path in sorted(root.rglob("*.md")):
        if path in SKIP_FILES:
            continue
        if any(parent in SKIP_DIRS for parent in path.parents):
            continue
        notes.append(path)
    return notes


def _scan_note(path: Path) -> NoteScan:
    lines = path.read_text(encoding="utf-8").splitlines()

    title = None
    for line in lines:
        match = RE_H1.match(line)
        if match:
            title = match.group(1).strip()
            break

    has_last_confirmed = False
    has_valid_last_confirmed_date = False
    has_verify = False
    has_load_when = False
    has_review_when = False
    has_failure_signals = False
    status_value: str | None = None
    dates: list[datetime] = []

    for idx, line in enumerate(lines):
        if _label_match(line, "status"):
            for follow in lines[idx + 1 :]:
                stripped = follow.strip()
                if not stripped:
                    continue
                if RE_HEADING.match(stripped):
                    break
                match = RE_STATUS_VALUE.match(stripped)
                if match:
                    status_value = match.group(1)
                break

        if _label_match(line, "last confirmed"):
            has_last_confirmed = True
            for follow in lines[idx + 1 :]:
                stripped = follow.strip()
                if not stripped:
                    continue
                match = RE_LAST_CONFIRMED_DATE.match(stripped)
                if match:
                    has_valid_last_confirmed_date = True
                    dates.append(datetime.strptime(match.group(1), "%Y-%m-%d").replace(tzinfo=UTC))
                break

        if _label_match(line, "verify") or _label_match(line, "verification"):
            has_verify = True
        if _label_match(line, "load when"):
            has_load_when = True
        if _label_match(line, "review when"):
            has_review_when = True
        if _label_match(line, "failure signals"):
            has_failure_signals = True

    return NoteScan(
        path=path,
        title=title,
        line_count=len(lines),
        has_last_confirmed=has_last_confirmed,
        has_valid_last_confirmed_date=has_valid_last_confirmed_date,
        has_verify=has_verify,
        has_load_when=has_load_when,
        has_review_when=has_review_when,
        has_failure_signals=has_failure_signals,
        has_needs_verification=(status_value or "").strip().lower() == "needs verification",
        newest_confirmed_date=max(dates) if dates else None,
    )


def _render_path(path: Path) -> str:
    return path.as_posix()


def _load_manifest_note_entries(path: Path) -> dict[str, dict[str, object]]:
    if not path.exists():
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {}
    notes = data.get("notes", {})
    return notes if isinstance(notes, dict) else {}


def _print_section(title: str, items: list[str]) -> None:
    print(f"\n{title}:")
    if not items:
        print("- none")
        return
    for item in items:
        print(f"- {item}")


def main() -> int:
    if not MEMORY_ROOT.exists():
        print("Memory freshness report\n")
        print("Memory root not found: memory/")
        return 0

    scans = [_scan_note(path) for path in _iter_notes(MEMORY_ROOT)]
    manifest_notes = _load_manifest_note_entries(MANIFEST_PATH)
    stale_before = datetime.now(UTC) - timedelta(days=STALE_DAYS)

    missing_last_confirmed = sorted(_render_path(scan.path) for scan in scans if not scan.has_last_confirmed)
    invalid_last_confirmed = sorted(
        _render_path(scan.path) for scan in scans if scan.has_last_confirmed and not scan.has_valid_last_confirmed_date
    )
    missing_verify = sorted(_render_path(scan.path) for scan in scans if not scan.has_verify)
    missing_load = sorted(_render_path(scan.path) for scan in scans if not scan.has_load_when)
    missing_review = sorted(_render_path(scan.path) for scan in scans if not scan.has_review_when)
    missing_failure = sorted(_render_path(scan.path) for scan in scans if not scan.has_failure_signals)
    missing_trigger = sorted(
        {_render_path(scan.path) for scan in scans if not (scan.has_load_when and scan.has_review_when and scan.has_failure_signals)}
    )
    needs_verification = sorted(_render_path(scan.path) for scan in scans if scan.has_needs_verification)
    old_confirmations = sorted(
        _render_path(scan.path) for scan in scans if scan.newest_confirmed_date and scan.newest_confirmed_date < stale_before
    )
    oversized_files = sorted(f"{_render_path(scan.path)} ({scan.line_count} lines)" for scan in scans if scan.line_count > MAX_LINES)

    title_map: dict[str, list[str]] = defaultdict(list)
    for scan in scans:
        if scan.title:
            title_map[scan.title.lower()].append(_render_path(scan.path))
    duplicate_titles = sorted(f"{paths[0]} (and {len(paths) - 1} more)" for paths in title_map.values() if len(paths) > 1)
    missing_manifest_entries = sorted(_render_path(scan.path) for scan in scans if _render_path(scan.path) not in manifest_notes)
    manifest_records_for_missing_notes = sorted(note_path for note_path in manifest_notes if not Path(note_path).exists())
    canonical_home_map: dict[str, list[str]] = defaultdict(list)
    for note_path, raw in manifest_notes.items():
        if not isinstance(raw, dict):
            continue
        canonical_home = str(raw.get("canonical_home", note_path))
        canonical_home_map[canonical_home].append(note_path)
    shared_canonical_homes = sorted(f"{home} <- {', '.join(paths)}" for home, paths in canonical_home_map.items() if len(paths) > 1)

    print("Memory freshness report")
    _print_section("Needs verification", needs_verification)
    _print_section("Missing trigger metadata", missing_trigger)
    _print_section("Missing Last confirmed", missing_last_confirmed)
    _print_section("Invalid Last confirmed date", invalid_last_confirmed)
    _print_section("Missing verification section", missing_verify)
    _print_section("Missing Load when", missing_load)
    _print_section("Missing Review when", missing_review)
    _print_section("Missing Failure signals", missing_failure)
    _print_section(f"Old confirmations (>{STALE_DAYS} days)", old_confirmations)
    _print_section("Oversized files", oversized_files)
    _print_section("Duplicate titles", duplicate_titles)
    _print_section("Missing manifest entries", missing_manifest_entries)
    _print_section("Manifest records for missing notes", manifest_records_for_missing_notes)
    _print_section("Shared canonical homes", shared_canonical_homes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
