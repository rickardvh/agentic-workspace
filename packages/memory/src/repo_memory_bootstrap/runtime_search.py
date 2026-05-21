from __future__ import annotations

from pathlib import Path

from repo_memory_bootstrap._installer_output import _new_result
from repo_memory_bootstrap._installer_paths import resolve_target_root
from repo_memory_bootstrap._installer_shared import InstallResult


def search_memory(
    *,
    query: str,
    target: str | Path | None = None,
) -> InstallResult:
    target_root = resolve_target_root(target)
    result = _new_result(target_root, dry_run=True, message=f"Memory search results for '{query}'")

    memory_dirs = ["memory", ".agentic-workspace/memory"]
    found_any = False

    for mdir in memory_dirs:
        root = target_root / mdir
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.md")):
            try:
                content = path.read_text(encoding="utf-8")
                if query.lower() in content.lower():
                    match_line = ""
                    for line in content.splitlines():
                        if query.lower() in line.lower():
                            match_line = line.strip()
                            break

                    result.add(
                        "found",
                        path,
                        f"matched query: {match_line}",
                        role="memory-search",
                        safety="safe",
                        source=path.relative_to(target_root).as_posix(),
                        category="search-result",
                    )
                    found_any = True
            except (UnicodeDecodeError, PermissionError):
                continue

    if not found_any:
        result.add(
            "not found",
            target_root / Path(".agentic-workspace/memory/repo/index.md"),
            f"no matches found for '{query}' in memory notes",
            role="memory-search",
            safety="safe",
            source=".agentic-workspace/memory/repo/index.md",
            category="search-result",
        )

    return result
