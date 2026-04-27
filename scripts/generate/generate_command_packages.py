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


def _maturity_levels(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    policy = manifest["generation_policy"]["generated_package_maturity"]
    return {level["id"]: level for level in policy["levels"]}


def _is_runnable_typescript_target(target: dict[str, Any]) -> bool:
    return target.get("maturity_level_ref") == "runnable-read-only-adapter"


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


def _typescript_package_json(
    package: dict[str, Any],
    target: dict[str, Any],
    maturity: dict[str, Any],
    runtime_binding: dict[str, Any],
) -> str:
    payload = {
        "name": target["package_name"],
        "version": "0.0.0-generated",
        "private": True,
        "type": "module",
        "bin": {entrypoint: "./src/cli.mjs" for entrypoint in target["entrypoints"]} if _is_runnable_typescript_target(target) else {},
        "scripts": {
            "test": "node --test test/command-package.test.mjs"
        },
        "agenticWorkspace": {
            "generated": True,
            "fixtureOnly": not _is_runnable_typescript_target(target),
            "generationStatus": target["generation_status"],
            "maturity": maturity,
            "runtimeBinding": runtime_binding,
            "source": "src/agentic_workspace/contracts/command_package_ir.json",
            "program": package["program"],
            "declaredEntrypoints": target["entrypoints"]
        }
    }
    if not payload["bin"]:
        del payload["bin"]
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


def _typescript_cli_module(package: dict[str, Any], target: dict[str, Any]) -> str:
    command_names = sorted(command["command"]["name"] for command in package["commands"])
    rendered_commands = json.dumps(command_names)
    return (
        "#!/usr/bin/env node\n"
        "// Generated runnable read-only adapter.\n"
        "// Source: src/agentic_workspace/contracts/command_package_ir.json\n"
        f"// Program: {package['program']}\n"
        "// Regenerate with: uv run python scripts/generate/generate_command_packages.py\n"
        "// DO NOT EDIT DIRECTLY.\n\n"
        "import { spawnSync } from 'node:child_process';\n\n"
        f"const supportedCommands = new Set({rendered_commands});\n"
        "const argv = process.argv.slice(2);\n"
        "const command = argv[0];\n\n"
        "if (!command || command === '--help' || command === '-h') {\n"
        f"  console.log(`Usage: {target['entrypoints'][0]} <command> [options]`);\n"
        "  console.log(`Supported generated commands: ${Array.from(supportedCommands).join(', ')}`);\n"
        "  process.exit(0);\n"
        "}\n\n"
        "if (!supportedCommands.has(command)) {\n"
        "  console.error(`Unsupported generated command: ${command}`);\n"
        "  process.exit(2);\n"
        "}\n\n"
        "const runtimeCommand = process.env.AGENTIC_WORKSPACE_RUNTIME || 'python -m agentic_workspace.cli';\n"
        "const result = spawnSync(runtimeCommand, argv, { encoding: 'utf8', shell: true });\n"
        "if (result.error) {\n"
        "  console.error(`Adapter runtime handoff failed: ${result.error.message}`);\n"
        "  process.exit(1);\n"
        "}\n"
        "if (result.stdout) process.stdout.write(result.stdout);\n"
        "if (result.stderr) process.stderr.write(result.stderr);\n"
        "process.exit(result.status ?? 1);\n"
    )


def _typescript_mock_runtime() -> str:
    return (
        "const payload = {\n"
        "  command: process.argv[2],\n"
        "  args: process.argv.slice(2),\n"
        "};\n"
        "console.log(JSON.stringify(payload));\n"
    )


def _typescript_test(package: dict[str, Any], target: dict[str, Any]) -> str:
    expected_commands = sorted(command["command"]["name"] for command in package["commands"])
    rendered_expected = json.dumps(expected_commands)
    runnable = _is_runnable_typescript_target(target)
    imports = (
        "import assert from 'node:assert/strict';\n"
        "import test from 'node:test';\n"
    )
    if runnable:
        imports += (
            "import { spawnSync } from 'node:child_process';\n"
            "import { fileURLToPath } from 'node:url';\n"
        )
    imports += "import { readFileSync } from 'node:fs';\n"
    body = imports + (
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
    if runnable:
        body += (
            "\n"
            "test('generated runnable adapter delegates supported command to runtime process', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            "  const mockRuntime = fileURLToPath(new URL('./mock-runtime.mjs', import.meta.url));\n"
            "  const runtime = `\"${process.execPath}\" \"${mockRuntime}\"`;\n"
            "  const result = spawnSync(process.execPath, [cli, 'defaults', '--format', 'json'], {\n"
            "    encoding: 'utf8',\n"
            "    env: { ...process.env, AGENTIC_WORKSPACE_RUNTIME: runtime },\n"
            "  });\n"
            "  assert.equal(result.status, 0);\n"
            "  const payload = JSON.parse(result.stdout);\n"
            "  assert.equal(payload.command, 'defaults');\n"
            "  assert.deepEqual(payload.args, ['defaults', '--format', 'json']);\n"
            "});\n"
        )
    return body


def _render_outputs(manifest: dict[str, Any]) -> list[tuple[Path, str]]:
    outputs: list[tuple[Path, str]] = []
    maturity_levels = _maturity_levels(manifest)
    runtime_binding = manifest["generation_policy"]["non_python_runtime_binding"]
    for package in manifest["packages"]:
        for target in package["targets"]:
            root = REPO_ROOT / str(target["generated_root"])
            if target["kind"] == "python":
                outputs.append((root / "__init__.py", _python_module(package)))
            elif target["kind"] == "typescript":
                outputs.append(
                    (
                        root / "package.json",
                        _typescript_package_json(package, target, maturity_levels[target["maturity_level_ref"]], runtime_binding),
                    )
                )
                outputs.append((root / "src" / "commandPackage.ts", _typescript_module(package)))
                outputs.append((root / "test" / "command-package.test.mjs", _typescript_test(package, target)))
                if _is_runnable_typescript_target(target):
                    outputs.append((root / "src" / "cli.mjs", _typescript_cli_module(package, target)))
                    outputs.append((root / "test" / "mock-runtime.mjs", _typescript_mock_runtime()))
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
