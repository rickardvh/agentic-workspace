"""Derive shipped agent procedure bytes from the declared repository sources."""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def render_host_payload(root: Path) -> dict[str, str]:
    """Closed derivation graph: no source-maintenance semantic read capability."""
    from agentic_workspace.static_read_profile import LEDGER, PROFILE, render

    host = json.loads((root / "src/agentic_workspace/contracts/workspace_surfaces.json").read_text())
    portable = set(host["derivation"]["portable_sources"])
    for reference in [*portable, *host["derivation"]["source_only_inputs"]]:
        if "\\" in reference or ":" in reference or any(part in {"", ".", ".."} for part in reference.split("/")):
            raise ValueError("Portable source declarations require canonical repository-relative paths")
    source_only = {(root / reference).resolve() for reference in host["derivation"]["source_only_inputs"]}
    if portable & set(host["derivation"]["source_only_inputs"]):
        raise ValueError("Source-only policy cannot be promoted implicitly into portable inputs")
    rows = {row["path"]: row["materialization"] for row in host["surfaces"]}
    if len(rows) != len(host["surfaces"]) or set(rows) != set(host["payload_files"]):
        raise ValueError("Each public host surface requires exactly one materialization")

    def read_portable(reference: str) -> str:
        if reference not in portable:
            raise ValueError(f"Host derivation input is not explicitly portable: {reference}")
        path = (root / reference).resolve()
        if not path.is_relative_to(root.resolve()) or path in source_only:
            raise ValueError("Portable input escapes its producer boundary or aliases source-only policy")
        return path.read_text(encoding="utf-8").replace("\r\n", "\n")

    outputs: dict[str, str] = {}
    visiting: set[str] = set()

    def materialize(path: str) -> str:
        if path in outputs:
            return outputs[path]
        if path in visiting or path not in rows:
            raise ValueError("Cyclic or undeclared host derivation input")
        visiting.add(path)
        row = rows[path]
        mode = row.get("mode")
        if mode == "package-verbatim" and set(row) == {"mode", "source"} and path not in {LEDGER, PROFILE}:
            result = read_portable(row["source"])
        elif (
            mode == "host-composed" and set(row) == {"mode", "source", "composer"} and path == LEDGER and row["composer"] == "ownership-v1"
        ):
            result = read_portable(row["source"])
        elif (
            mode == "target-derived"
            and set(row) == {"mode", "input", "renderer"}
            and path == PROFILE
            and row["input"] == LEDGER
            and row["renderer"] == "ownership-read-profile-v1"
        ):
            result = render(materialize(row["input"]))
        else:
            raise ValueError(f"Unsupported host materialization: {path}")
        visiting.remove(path)
        outputs[path] = result
        return result

    for path in rows:
        materialize(path)
    return outputs


def synchronize(*, check: bool = False) -> list[str]:
    manifest = json.loads((ROOT / "src/agentic_workspace/contracts/source_maintenance_surfaces.json").read_text())
    # Validate and derive public outputs before any writes. This read capability
    # cannot be widened by the source-maintenance copy set below.
    host_outputs = render_host_payload(ROOT)
    if any(row["path"] in host_outputs for row in manifest.get("retired_surface_files", [])):
        raise ValueError("Source maintenance cannot retire a public host materialization")
    payload = ROOT / "src/agentic_workspace/_payload"
    from agentic_workspace.static_read_profile import LEDGER, PROFILE, render

    drift = []
    profile = ROOT / PROFILE
    expected_profile = render((ROOT / LEDGER).read_text(encoding="utf-8"))
    if not profile.is_file() or profile.read_text(encoding="utf-8") != expected_profile:
        drift.append(PROFILE)
        if not check:
            profile.write_text(expected_profile, encoding="utf-8", newline="\n")
    maintenance_outputs = {
        reference: (ROOT / reference).read_text(encoding="utf-8").replace("\r\n", "\n")
        for reference in manifest["payload_files"]
        if reference not in host_outputs
    }
    for reference, expected in {**maintenance_outputs, **host_outputs}.items():
        destination = payload / reference
        if not destination.is_file() or destination.read_text(encoding="utf-8") != expected:
            drift.append(reference)
            if not check:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(expected, encoding="utf-8", newline="\n")
    # Standalone first-party packages fall back to these shipped declarations.
    # These consumers need module roots only, never repository policy.
    for module in ("memory", "planning"):
        destination = ROOT / f"packages/{module}/src/repo_{module}_bootstrap/_ownership.toml"
        roots = tomllib.loads(host_outputs[LEDGER])["module_roots"]
        expected = "schema_version = 1\n" + "".join(
            "\n[[module_roots]]\n" + "".join(f"{key} = {json.dumps(value)}\n" for key, value in row.items()) for row in roots
        )
        if destination.read_text(encoding="utf-8") != expected:
            drift.append(destination.relative_to(ROOT).as_posix())
            if not check:
                destination.write_text(expected, encoding="utf-8", newline="\n")
    # Planning's compatibility installer shares this path with Workspace.
    # Derive identical bytes so alternating upgrades cannot overwrite each
    # other's configuration guidance on every pass.
    reference = ".agentic-workspace/docs/workspace-config-contract.md"
    destination = ROOT / "packages/planning/bootstrap" / reference
    expected = (ROOT / reference).read_text(encoding="utf-8")
    if destination.read_text(encoding="utf-8") != expected:
        drift.append(destination.relative_to(ROOT).as_posix())
        if not check:
            destination.write_text(expected, encoding="utf-8", newline="\n")
    for retired in manifest.get("retired_surface_files", []):
        destination = payload / retired["path"]
        if destination.exists():
            drift.append(retired["path"])
            if not check:
                destination.unlink()
    return drift


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed = synchronize(check=args.check)
    print(json.dumps({"drift" if args.check else "updated": changed}))
    raise SystemExit(1 if args.check and changed else 0)
