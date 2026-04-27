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

from agentic_workspace.contract_tooling import command_package_ir_manifest  # noqa: E402


def _json_block(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _python_module(package: dict[str, Any]) -> str:
    rendered = _json_block(package)
    return (
        '"""Generated command package metadata.\n\n'
        "Source: src/agentic_workspace/contracts/command_package_ir.json\n"
        f"Program: {package['program']}\n"
        "Regenerate with: uv run python scripts/generate/generate_command_packages.py\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
        "import json\n"
        "from typing import Any\n\n"
        "# DO NOT EDIT DIRECTLY.\n"
        "# Command/package interface changes belong in src/agentic_workspace/contracts/command_package_ir.json.\n"
        "# Runtime behavior changes belong in hand-written operation/primitive implementation code.\n"
        "# Regenerate with: uv run python scripts/generate/generate_command_packages.py\n"
        "GENERATED_COMMAND_PACKAGE: dict[str, Any] = json.loads(\n"
        "    r\"\"\"\n"
        f"{rendered}\n"
        "\"\"\"\n"
        ")\n"
    )


def _typescript_package_json(package: dict[str, Any], target: dict[str, Any]) -> str:
    payload = {
        "name": target["package_name"],
        "version": "0.0.0-generated",
        "private": True,
        "type": "module",
        "bin": {entrypoint: "./src/commandPackage.ts" for entrypoint in target["entrypoints"]},
        "scripts": {
            "test": "node --test test/command-package.test.mjs"
        },
        "agenticWorkspace": {
            "generated": True,
            "source": "src/agentic_workspace/contracts/command_package_ir.json",
            "program": package["program"]
        }
    }
    return _json_block(payload) + "\n"


def _typescript_module(package: dict[str, Any]) -> str:
    rendered = _json_block(package)
    return (
        "// Generated command package metadata.\n"
        "// Source: src/agentic_workspace/contracts/command_package_ir.json\n"
        f"// Program: {package['program']}\n"
        "// Regenerate with: uv run python scripts/generate/generate_command_packages.py\n"
        "// DO NOT EDIT DIRECTLY.\n\n"
        f"export const generatedCommandPackage = {rendered} as const;\n"
        "\n"
        "export type GeneratedCommandPackage = typeof generatedCommandPackage;\n"
    )


def _typescript_test(package: dict[str, Any]) -> str:
    expected_commands = sorted(command["command"]["name"] for command in package["commands"])
    rendered_expected = json.dumps(expected_commands)
    return (
        "import assert from 'node:assert/strict';\n"
        "import test from 'node:test';\n"
        "import { readFileSync } from 'node:fs';\n"
        "\n"
        "const source = readFileSync(new URL('../src/commandPackage.ts', import.meta.url), 'utf8');\n"
        "\n"
        "test('generated package metadata exposes expected commands', () => {\n"
        f"  const expected = {rendered_expected};\n"
        "  for (const command of expected) {\n"
        "    assert.match(source, new RegExp(`\\\"name\\\": \\\\\"${command}\\\\\"`));\n"
        "  }\n"
        "});\n"
    )


def _render_outputs(manifest: dict[str, Any]) -> list[tuple[Path, str]]:
    outputs: list[tuple[Path, str]] = []
    for package in manifest["packages"]:
        for target in package["targets"]:
            root = REPO_ROOT / str(target["generated_root"])
            if target["kind"] == "python":
                outputs.append((root / "__init__.py", _python_module(package)))
            elif target["kind"] == "typescript":
                outputs.append((root / "package.json", _typescript_package_json(package, target)))
                outputs.append((root / "src" / "commandPackage.ts", _typescript_module(package)))
                outputs.append((root / "test" / "command-package.test.mjs", _typescript_test(package)))
    return outputs


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate command package metadata from the command-package IR.")
    parser.add_argument("--check", action="store_true", help="Fail if generated command package files are stale.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    manifest = command_package_ir_manifest()
    outputs = _render_outputs(manifest)
    stale_outputs: list[str] = []
    for output_path, rendered in outputs:
        if args.check:
            current = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
            if current != rendered:
                stale_outputs.append(output_path.relative_to(REPO_ROOT).as_posix())
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding="utf-8")
            print(f"[ok] wrote {output_path.relative_to(REPO_ROOT).as_posix()}")
    if args.check:
        if stale_outputs:
            for output in stale_outputs:
                print(f"{output} is stale; regenerate command packages.")
            return 1
        print("[ok] generated command packages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
