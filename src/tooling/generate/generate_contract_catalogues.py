from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
CLI_PATH = Path("src/core/contracts/source_decision_contract.json")
SURFACES_PATH = Path("src/core/contracts/workspace_surfaces.json")
SUPPORT_INSTALL_PATH = Path("src/tooling/contracts/support_bearing_install.json")
CLI_OUTPUT = Path("docs/reference/cli-catalogue.md")
SURFACES_OUTPUT = Path("docs/reference/installed-surface-catalogue.md")
SUPPORT_INSTALL_OUTPUT = Path("docs/reference/support-bearing-install.md")


def _load(path: Path) -> dict[str, Any]:
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def _digest(paths: list[Path]) -> str:
    value = hashlib.sha256()
    for path in paths:
        value.update(path.as_posix().encode("utf-8"))
        # Hash repository text, not the checkout's platform line endings.
        # This matches the LF form declared by .gitattributes while retaining
        # every other source-byte change in the catalogue freshness identity.
        value.update((REPO_ROOT / path).read_bytes().replace(b"\r\n", b"\n"))
    return value.hexdigest()


def _escape(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple)):
        return ", ".join(_escape(item) for item in value) or "—"
    return str(value).replace("|", "\\|").replace("\n", " ") or "—"


def render_cli_catalogue() -> str:
    manifest = _load(CLI_PATH)["native_cli"]
    lines = [
        "<!-- GENERATED FILE: edit source_decision_contract.json and rerun `make render-schema-reference`. -->",
        "",
        "# Current CLI Catalogue",
        "",
        "Generated from the same `native_cli` declaration used by the native executable. The main AW skill is the ordinary agent procedure; this page is tool reference, not a mandatory command loop.",
        "",
        f"- Contract digest: `sha256:{_digest([CLI_PATH])}`",
        f"- Program: `{manifest['executable']}`",
        f"- Command count: {len(manifest['commands'])}",
        "",
        "## Commands",
        "",
        "| Command | Requires JSON input | Purpose |",
        "| --- | --- | --- |",
    ]
    for command in manifest["commands"]:
        lines.append(
            f"| `{manifest['executable']} {command['name']}` | {_escape(command['input_required'])} | {_escape(command['description'])} |"
        )
    lines.extend(["", "## Options", "", "| Flag | Default | Choices | Purpose |", "| --- | --- | --- | --- |"])
    for option in manifest["options"]:
        lines.append(
            f"| `{option['flag']}` | {_escape(option.get('default'))} | {_escape(option.get('choices'))} | {_escape(option['description'])} |"
        )
    lines.extend(
        [
            "",
            "Use `--help` for the installed artefact's actual command boundary. Owner requests returned by `start` expose domain operations without adding domain CLI subcommands.",
            "",
            "`start` is current resolution; `invoke` consumes one exact returned action. `resources` and `worker` are bounded dedicated tools. A request, route, packet seal or successful process does not grant mutation, ownership, proof or completion authority. Optional machine-local diagnostics remain distinct from repository mutation.",
            "",
            "The retired `init`, `defaults`, `implement`, `proof` and module command families are not native public commands. Owner actions are obtained from the current native decision.",
            "",
            "See [installation](../agentic-workspace-install.md), [everyday use](../everyday-use.md) and the [shared authority graph](../architecture/shared-rust-core.md).",
            "",
        ]
    )
    return "\n".join(lines)




def render_surface_catalogue() -> str:
    surfaces = _load(SURFACES_PATH)
    lines = [
        "<!-- GENERATED FILE: edit workspace_surfaces.json and rerun `make render-schema-reference`. -->",
        "",
        "# Current Installed-Surface Catalogue",
        "",
        "The public v1 host footprint is one Configuration-owned contract. Adoption, refresh, and removal use the same file set. Optional domain state is never established by adoption.",
        "",
        f"- Contract digest: `sha256:{_digest([SURFACES_PATH])}`",
        "",
        "| Surface | Ownership | Materialisation | Lifetime | Establish / refresh / remove | Consumer |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in surfaces["surfaces"]:
        lines.append(
            f"| `{row['path']}` | {row['ownership']} | {row['materialization']['mode']} | {row['lifetime']} | `{row['establish']}` | {row['justification']} |"
        )
    lines.extend(["", surfaces["derivation"]["rule"], "", "Portable source promotions:", ""])
    lines.extend(f"- `{path}`" for path in surfaces["derivation"]["portable_sources"])
    lines.extend(
        [
            "",
            f"Adoption identity: `{surfaces['identity']}`. Payload provenance: `{surfaces['provenance']}`. Both are package integration records with the same lifecycle.",
            "",
            "Only the declared workflow fence in `AGENTS.md` is managed. Text outside it remains repository-owned. Edited, unowned, or unsafe destinations are preserved and reported by Configuration.",
            "",
            "## De-adoption preservation",
            "",
        ]
    )
    for owner, paths in surfaces["preserved_classes"].items():
        lines.append(f"- {owner}: " + ", ".join(f"`{path}`" for path in paths))
    lines.append(
        f"- Local diagnostic ignore rule: `{surfaces['local_ignore']['path']}`; created only when absent and preserved with local state on removal."
    )
    lines.extend(
        [
            "",
            "Current-version updates treat `.agentic-workspace/` as a closed enclave. Every file is covered by one current owner/class/lifetime declaration, including explicitly mutable, customisation and local subtrees. Unclassified residue is included in the exact authorised removal proposal; ambiguous declarations block reconciliation. Inventory is bounded and never traverses links or junctions. Current managed-file conflict rules still apply. A second successful reconciliation is quiet. De-adoption preserves independent state and remains a separate operation.",
            "",
            "Workspace declarations live in `workspace_surfaces.json` under `enclave`; Planning, Memory and Verification each own `contracts/enclave.json` in their package source. Owners register classification through a generic linked inventory; Workspace neither lists module identities nor refreshes their support. Repository OWNERSHIP.toml admits independent owner paths through explicit enclave rows (path, scope, owner, class, lifetime) and preserves repo_owned authority surfaces. Independent native publication namespaces follow current modules.independent admissions. Ambiguous overlaps block cleanup; broad legacy module roots do not hide residue. New repository extensions can also live under `.agentic-workspace/custom/`; scoped repository instructions remain under `.agentic-workspace/instructions/`.",
            "",
            "Skill-discovery links are removed through their authenticated Configuration exposure owner before removing their canonical targets.",
            "",
            "## Retired package surfaces",
            "",
            "These exact preimages are retained only for de-adoption compatibility. Current-version update hygiene uses current ownership declarations and requires no retirement entry or historical hash.",
            "",
        ]
    )
    for row in surfaces["retired_package_surfaces"]:
        lines.append(f"- `{row['path']}` -- `sha256:{row['sha256']}`")
    lines.extend(
        [
            "",
            "Historical profiles and executable fallback maintenance live in the separate [source-maintenance inventory](source-maintenance-surface-catalogue.md). They are not public host profiles or CLI commands.",
            "",
        ]
    )
    return "\n".join(lines)




def render_support_install() -> str:
    projection = _load(SUPPORT_INSTALL_PATH)
    receipt = projection["receipt"]
    artifact = projection["artifact"]
    return "\n".join(
        [
            "<!-- GENERATED FILE: edit the source projection and rerun `make render-schema-reference`. -->",
            "",
            "# Current Support-Bearing Install",
            "",
            "Human-copyable projection of the latest stable release-owned installation receipt.",
            "",
            "This receipt describes only its named release. It does not install newer branch or admitted-but-unpublished behaviour; consult the [installation guide](../agentic-workspace-install.md) for the current implementation boundary.",
            "",
            f"- Release: [{projection['version']}]({projection['release_url']})",
            f"- Published: `{projection['published_at']}`",
            f"- Dereferenced source commit: `{projection['source_commit']}`",
            f"- Receipt: [{receipt['kind']}]({receipt['url']})",
            f"- Receipt digest: `sha256:{receipt['sha256']}`",
            f"- Root artefact: [{artifact['name']}]({artifact['url']})",
            f"- Artefact digest: `sha256:{artifact['sha256']}`",
            "",
            "```bash",
            projection["install_command"],
            "```",
            "",
            "The command above is for the root receipt's named platform, not a universal wheel. Choose your platform:",
            "",
            *[f"- `{row['target']}`: `{row['command']}`" for row in projection.get("platforms", [])],
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
    target.write_text(content, encoding="utf-8", newline="\n")
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
