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

OUTPUT_PATH = REPO_ROOT / "src" / "agentic_workspace" / "generated_command_adapters.py"


def _render_generated_module(manifest: dict[str, Any]) -> str:
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
    }
    rendered = json.dumps(adapters_by_command, indent=2, sort_keys=True)
    return (
        '"""Generated command adapter metadata.\n\n'
        "Source: src/agentic_workspace/contracts/command_adapter_generation.json\n"
        "Regenerate with: uv run python scripts/generate/generate_command_adapters.py\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
        "import json\n"
        "from typing import Any\n\n"
        "# Generated file; edit command_adapter_generation.json instead.\n"
        "GENERATED_COMMAND_ADAPTERS_BY_COMMAND: dict[str, dict[str, Any]] = json.loads(\n"
        "    r\"\"\"\n"
        f"{rendered}\n"
        "\"\"\"\n"
        ")\n"
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate command adapter metadata from contract manifests.")
    parser.add_argument("--check", action="store_true", help="Fail if the generated command adapter module is stale.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    rendered = _render_generated_module(command_adapter_generation_manifest())
    if args.check:
        current = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
        if current != rendered:
            print(f"{OUTPUT_PATH.relative_to(REPO_ROOT).as_posix()} is stale; regenerate command adapters.")
            return 1
        print("[ok] generated command adapters")
        return 0
    OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    print(f"[ok] wrote {OUTPUT_PATH.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
