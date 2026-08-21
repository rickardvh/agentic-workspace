from __future__ import annotations

import argparse
import hashlib
import json
import sys
from itertools import combinations
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_PATH = Path("src/agentic_workspace/contracts/cli_commands.json")
OPTION_GROUPS_PATH = Path("src/agentic_workspace/contracts/cli_option_groups.json")
SURFACES_PATH = Path("src/agentic_workspace/contracts/workspace_surfaces.json")
MODULES_PATH = Path("src/agentic_workspace/contracts/module_registry.json")
SUPPORT_INSTALL_PATH = Path("src/agentic_workspace/contracts/support_bearing_install.json")
CLI_OUTPUT = Path("docs/reference/cli-catalogue.md")
SURFACES_OUTPUT = Path("docs/reference/installed-surface-catalogue.md")
SUPPORT_INSTALL_OUTPUT = Path("docs/reference/support-bearing-install.md")


def _load(path: Path) -> dict[str, Any]:
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def _digest(paths: list[Path]) -> str:
    value = hashlib.sha256()
    for path in paths:
        value.update(path.as_posix().encode("utf-8"))
        value.update((REPO_ROOT / path).read_bytes())
    return value.hexdigest()


def _escape(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple)):
        return ", ".join(_escape(item) for item in value) or "—"
    return str(value).replace("|", "\\|").replace("\n", " ") or "—"


def _command_rows(commands: list[dict[str, Any]], prefix: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], dict[str, Any]]]:
    rows: list[tuple[tuple[str, ...], dict[str, Any]]] = []
    for command in commands:
        path = (*prefix, str(command["name"]))
        rows.append((path, command))
        rows.extend(_command_rows(command.get("subcommands", []), path))
    return rows


def _group_options(group_id: str, groups: dict[str, Any], seen: set[str] | None = None) -> list[dict[str, Any]]:
    visited = set(seen or set())
    if group_id in visited:
        return []
    visited.add(group_id)
    group = groups.get(group_id, {})
    options: list[dict[str, Any]] = []
    for parent in group.get("uses", []):
        options.extend(_group_options(str(parent), groups, visited))
    options.extend(item for item in group.get("options", []) if isinstance(item, dict))
    return options


def _options(command: dict[str, Any], groups: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for group_id in command.get("uses_option_groups", []):
        values.extend(_group_options(str(group_id), groups))
    values.extend(item for item in command.get("options", []) if isinstance(item, dict))
    deduped: dict[str, dict[str, Any]] = {}
    for item in values:
        deduped[str(item.get("name") or _escape(item.get("flags")))] = item
    return list(deduped.values())


def render_cli_catalogue() -> str:
    manifest = _load(CLI_PATH)
    groups = _load(OPTION_GROUPS_PATH).get("option_groups", {})
    rows = _command_rows(manifest["commands"])
    source_digest = _digest([CLI_PATH, OPTION_GROUPS_PATH])
    lines = [
        "<!-- GENERATED FILE: edit the source contracts and rerun `make render-schema-reference`. -->",
        "# Current CLI Catalogue",
        "",
        "Exact current command values generated from `cli_commands.json` and `cli_option_groups.json`. The schema-shape references remain at `cli-commands.md` and `cli-option-groups.md`.",
        "",
        f"- Contract digest: `sha256:{source_digest}`",
        f"- Program: `{manifest['program']}`",
        f"- Command/subcommand count: {len(rows)}",
        "",
        "Shared-state mutability and ignored local diagnostics are separate. A `no` below means the command contract does not mutate shared workspace state. When local session logging is enabled, any command may still write ignored machine-local diagnostics:",
        "",
        f"- Condition: {_escape(manifest['local_execution_effects']['condition'])}",
        f"- Possible effects: {_escape(manifest['local_execution_effects']['effects'])}",
        f"- Authority: `{manifest['local_execution_effects']['authority']}` — {_escape(manifest['local_execution_effects']['rule'])}",
        "",
        "## Command index",
        "",
        "| Command | Role | Audience | Shared mutation | Options | Description |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for path, command in rows:
        command_text = " ".join((manifest["program"], *path))
        lines.append(
            f"| `{command_text}` | `{_escape(command.get('role'))}` | `{_escape(command.get('audience'))}` | "
            f"{_escape(command.get('mutates_state', False))} | {len(_options(command, groups))} | {_escape(command.get('help'))} |"
        )
    for path, command in rows:
        command_text = " ".join((manifest["program"], *path))
        options = _options(command, groups)
        lines.extend(
            [
                "",
                f"## `{command_text}`",
                "",
                f"{_escape(command.get('classification_note') or command.get('help'))}",
                "",
                "| Flags | Required | Default | Choices | Action / nargs | Description |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        if not options:
            lines.append("| — | — | — | — | — | No declared options. |")
        for option in options:
            default = option.get("default_ref") or option.get("default") if "default" in option or option.get("default_ref") else None
            action = option.get("action") or "value"
            if option.get("nargs") is not None:
                action = f"{action}; nargs={option['nargs']}"
            choices = option.get("choices_ref") or option.get("choices")
            lines.append(
                f"| `{_escape(option.get('flags'))}` | {_escape(option.get('required', False))} | `{_escape(default)}` | "
                f"{_escape(choices)} | `{_escape(action)}` | {_escape(option.get('help') or option.get('help_template'))} |"
            )
    return "\n".join(lines) + "\n"


def _module_sets(names: list[str]) -> list[tuple[str, ...]]:
    return [combo for size in range(len(names) + 1) for combo in combinations(names, size)]


def render_surface_catalogue() -> str:
    surfaces = _load(SURFACES_PATH)
    registry = _load(MODULES_PATH)
    modules = [str(item["name"]) for item in registry.get("modules", [])]
    source_digest = _digest([SURFACES_PATH, MODULES_PATH])
    module_files = {key: sorted(value) for key, value in surfaces.get("module_surface_files", {}).items()}
    profiles = {
        "necessary-surfaces": sorted(surfaces.get("necessary_surface_files", [])),
        "full-mirror": sorted(surfaces.get("payload_files", [])),
    }
    lines = [
        "<!-- GENERATED FILE: edit the source contracts and rerun `make render-schema-reference`. -->",
        "# Current Installed-Surface Catalogue",
        "",
        "Exact footprint, ownership, and availability values generated from `workspace_surfaces.json` and `module_registry.json`.",
        "",
        f"- Contract digest: `sha256:{source_digest}`",
        f"- Supported profiles: {', '.join(f'`{name}`' for name in profiles)}",
        f"- Declared modules: {', '.join(f'`{name}`' for name in modules)}",
        "",
        "Package-managed base and module files are installed by lifecycle operations. Repo-owned optional references are never invented merely because a module is selected. Generated/derived output and ignored local state are outside the necessary checked-in surface unless a source contract explicitly lists them.",
        "",
        "## Profile and module cells",
        "",
        "Each cell below lists the exact package-managed checked-in files: profile base plus selected module additions.",
    ]
    for profile_name, base_files in profiles.items():
        for selection in _module_sets(modules):
            selected = ",".join(selection) if selection else "none"
            files = sorted({*base_files, *(path for module in selection for path in module_files.get(module, []))})
            lines.extend(
                [
                    "",
                    f"### `{profile_name}` + `{selected}`",
                    "",
                    f"File count: {len(files)}",
                    "",
                    *[f"- `{path}`" for path in files],
                ]
            )
    lines.extend(
        [
            "",
            "## Required and optional references",
            "",
            "| Target | Kind | Profiles | Modules | Availability / degraded behavior |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    seen: set[tuple[str, str, tuple[str, ...], tuple[str, ...]]] = set()
    for reference in surfaces.get("required_references", []):
        identity = (
            str(reference.get("target")),
            str(reference.get("kind")),
            tuple(reference.get("profiles", [])),
            tuple(reference.get("modules", [])),
        )
        if identity in seen:
            continue
        seen.add(identity)
        degraded = reference.get("degraded_behavior") or "required in the selected footprint"
        if reference.get("kind") == "optional" and "verification" in reference.get("modules", []):
            degraded = f"selected-but-unconfigured: {degraded}"
        lines.append(
            f"| `{_escape(reference.get('target'))}` | `{_escape(reference.get('kind'))}` | "
            f"{_escape(reference.get('profiles'))} | {_escape(reference.get('modules'))} | {_escape(degraded)} |"
        )
    lines.extend(
        [
            "",
            "## Ownership classes",
            "",
            "| Class | Contract meaning |",
            "| --- | --- |",
            "| Repo-owned | Host configuration, canonical docs/source, and optional policy remain owned by the repository. |",
            "| Package-managed | Lifecycle operations install and refresh the declared base payload. |",
            "| Module-owned | A selected module owns only its declared roots and additions. |",
            "| Generated/derived | Rebuildable projections are owned by their source contract and generator. |",
            "| Local-only | Ignored diagnostics, logs, caches, and machine preferences are not shared authority. |",
            "| Optional/degraded | Absence is explicit and produces the listed degraded behavior rather than invented state. |",
            "| Promoted output | Output becomes durable only through an explicit owning repository or module operation. |",
        ]
    )
    return "\n".join(lines) + "\n"


def render_support_install() -> str:
    projection = _load(SUPPORT_INSTALL_PATH)
    receipt = projection["receipt"]
    artifact = projection["artifact"]
    return "\n".join(
        [
            "<!-- GENERATED FILE: edit the source projection and rerun `make render-schema-reference`. -->",
            "# Current Support-Bearing Install",
            "",
            "Human-copyable projection of the latest immutable release-owned installation receipt.",
            "",
            f"- Release: [{projection['version']}]({projection['release_url']})",
            f"- Published: `{projection['published_at']}`",
            f"- Dereferenced source commit: `{projection['source_commit']}`",
            f"- Receipt: [{receipt['kind']}]({receipt['url']})",
            f"- Receipt digest: `sha256:{receipt['sha256']}`",
            f"- Root artifact: [{artifact['name']}]({artifact['url']})",
            f"- Artifact digest: `sha256:{artifact['sha256']}`",
            "",
            "```bash",
            projection["install_command"],
            "```",
            "",
            "The release receipt remains authority. This checked-in page is a parity-checked projection for discovery; mutable branch, registry, editable, source-checkout, and debug installs are not substituted for this identity.",
            "",
        ]
    )


def _write_or_check(path: Path, content: str, *, check: bool) -> bool:
    target = REPO_ROOT / path
    if check:
        return target.exists() and target.read_text(encoding="utf-8") == content
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate current-value contract catalogues.")
    parser.add_argument("--check", action="store_true", help="Fail when generated catalogues are stale.")
    args = parser.parse_args()
    outputs = {
        CLI_OUTPUT: render_cli_catalogue(),
        SURFACES_OUTPUT: render_surface_catalogue(),
        SUPPORT_INSTALL_OUTPUT: render_support_install(),
    }
    stale = [path for path, content in outputs.items() if not _write_or_check(path, content, check=args.check)]
    if stale:
        print("stale generated contract catalogue(s): " + ", ".join(path.as_posix() for path in stale), file=sys.stderr)
        return 1
    print("[ok] generated contract catalogues" if args.check else "[generated] contract catalogues")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
