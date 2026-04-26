from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from agentic_workspace.contract_tooling import command_adapter_generation_manifest  # noqa: E402

DEFAULT_PROGRAM = "agentic-workspace"


def _adapters_for_program(manifest: dict[str, Any], *, program: str) -> dict[str, dict[str, Any]]:
    adapters_by_command = {
        str(adapter["command"]["name"]): {
            "id": adapter["id"],
            "status": adapter["status"],
            "command": adapter["command"],
            "operation_id": adapter["operation_ref"]["id"],
            "runtime_binding": adapter["runtime_binding"],
            "effect_hints": adapter["effect_hints"],
            "schemas": adapter["schemas"],
            "conformance_refs": adapter["conformance_refs"],
        }
        for adapter in manifest["adapters"]
        if adapter["command"]["program"] == program
    }
    if not adapters_by_command:
        raise SystemExit(f"No command adapters declared for program {program!r}.")
    return adapters_by_command


def _render_generated_module(manifest: dict[str, Any], *, program: str = DEFAULT_PROGRAM) -> str:
    adapters_by_command = _adapters_for_program(manifest, program=program)
    rendered = json.dumps(adapters_by_command, indent=2, sort_keys=True)
    return (
        '"""Generated command adapter metadata.\n\n'
        "Source: src/agentic_workspace/contracts/command_adapter_generation.json\n"
        f"Program: {program}\n"
        "Regenerate with: uv run python scripts/generate/generate_command_adapters.py\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
        "import json\n"
        "from typing import Any\n\n"
        "# DO NOT EDIT DIRECTLY.\n"
        "# Command/interface changes belong in src/agentic_workspace/contracts/command_adapter_generation.json.\n"
        "# Runtime behavior changes belong in hand-written operation/primitive implementation code.\n"
        "# Regenerate with: uv run python scripts/generate/generate_command_adapters.py\n"
        "GENERATED_COMMAND_ADAPTERS_BY_COMMAND: dict[str, dict[str, Any]] = json.loads(\n"
        "    r\"\"\"\n"
        f"{rendered}\n"
        "\"\"\"\n"
        ")\n"
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate command adapter metadata from contract manifests.")
    parser.add_argument("--check", action="store_true", help="Fail if the generated command adapter module is stale.")
    parser.add_argument("--program", help="Generate only adapters for this program.")
    parser.add_argument("--output", help="Output path for one program. Defaults to the contract-declared output.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    manifest = command_adapter_generation_manifest()
    output_specs = list(manifest["generated_outputs"])
    if args.program is not None or args.output is not None:
        program = args.program or DEFAULT_PROGRAM
        output_path = Path(args.output) if args.output is not None else _output_path_for_program(manifest, program=program)
        output_specs = [{"program": program, "path": output_path.as_posix()}]

    stale_outputs: list[str] = []
    rendered_outputs: list[tuple[Path, str]] = []
    for output_spec in output_specs:
        program = str(output_spec["program"])
        output_path = (REPO_ROOT / str(output_spec["path"])).resolve()
        rendered = _render_generated_module(manifest, program=program)
        rendered_outputs.append((output_path, rendered))
        if args.check:
            current = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
            if current != rendered:
                stale_outputs.append(output_path.relative_to(REPO_ROOT).as_posix())

    if args.check:
        if stale_outputs:
            for output in stale_outputs:
                print(f"{output} is stale; regenerate command adapters.")
            return 1
        print("[ok] generated command adapters")
        return 0
    for output_path, rendered in rendered_outputs:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
        print(f"[ok] wrote {output_path.relative_to(REPO_ROOT).as_posix()}")
    return 0


def _output_path_for_program(manifest: dict[str, Any], *, program: str) -> Path:
    matches = [Path(str(output["path"])) for output in manifest["generated_outputs"] if output["program"] == program]
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one generated output for program {program!r}, found {len(matches)}.")
    return matches[0]


if __name__ == "__main__":
    raise SystemExit(main())
