from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GeneratedOutput:
    path: Path
    content: str


def _json_block(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _maturity_levels(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    policy = manifest["generation_policy"]["generated_package_maturity"]
    return {level["id"]: level for level in policy["levels"]}


def _is_runnable_typescript_target(target: dict[str, Any]) -> bool:
    return target.get("maturity_level_ref") == "runnable-read-only-adapter"


def _python_module(package: dict[str, Any], *, source_path: str, regenerate_command: str) -> str:
    rendered = _json_block(package)
    return (
        '"""Generated command package metadata.\n\n'
        f"Source: {source_path}\n"
        f"Program: {package['program']}\n"
        f"Regenerate with: {regenerate_command}\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
        "import json\n"
        "from typing import Any\n\n"
        "# DO NOT EDIT DIRECTLY.\n"
        f"# Command/package interface changes belong in {source_path}.\n"
        "# Runtime behavior changes belong in hand-written operation/primitive implementation code.\n"
        f"# Regenerate with: {regenerate_command}\n"
        "GENERATED_COMMAND_PACKAGE: dict[str, Any] = json.loads(\n"
        '    r"""\n'
        f"{rendered}\n"
        '"""\n'
        ")\n"
    )


def _typescript_package_json(
    package: dict[str, Any],
    target: dict[str, Any],
    maturity: dict[str, Any],
    runtime_binding: dict[str, Any],
    *,
    source_path: str,
) -> str:
    payload = {
        "name": target["package_name"],
        "version": "0.0.0-generated",
        "private": True,
        "type": "module",
        "bin": {entrypoint: "./src/cli.mjs" for entrypoint in target["entrypoints"]} if _is_runnable_typescript_target(target) else {},
        "scripts": {"test": "node --test test/command-package.test.mjs"},
        "agenticWorkspace": {
            "generated": True,
            "fixtureOnly": not _is_runnable_typescript_target(target),
            "generationStatus": target["generation_status"],
            "maturity": maturity,
            "runtimeBinding": runtime_binding,
            "source": source_path,
            "program": package["program"],
            "declaredEntrypoints": target["entrypoints"],
        },
    }
    if not payload["bin"]:
        del payload["bin"]
    return _json_block(payload) + "\n"


def _typescript_module(package: dict[str, Any], *, source_path: str, regenerate_command: str) -> str:
    rendered = _json_block(package)
    return (
        "// Generated command package metadata.\n"
        f"// Source: {source_path}\n"
        f"// Program: {package['program']}\n"
        f"// Regenerate with: {regenerate_command}\n"
        "// DO NOT EDIT DIRECTLY.\n\n"
        f"export const generatedCommandPackage = {rendered} as const;\n"
        "\n"
        "export type GeneratedCommandPackage = typeof generatedCommandPackage;\n"
    )


def _typescript_cli_module(package: dict[str, Any], target: dict[str, Any], *, source_path: str, regenerate_command: str) -> str:
    command_names = sorted(command["command"]["name"] for command in package["commands"])
    rendered_commands = json.dumps(command_names)
    return (
        "#!/usr/bin/env node\n"
        "// Generated runnable read-only adapter.\n"
        f"// Source: {source_path}\n"
        f"// Program: {package['program']}\n"
        f"// Regenerate with: {regenerate_command}\n"
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
    return "const payload = {\n  command: process.argv[2],\n  args: process.argv.slice(2),\n};\nconsole.log(JSON.stringify(payload));\n"


def _typescript_test(package: dict[str, Any], target: dict[str, Any]) -> str:
    expected_commands = sorted(command["command"]["name"] for command in package["commands"])
    rendered_expected = json.dumps(expected_commands)
    runnable = _is_runnable_typescript_target(target)
    expected_maturity = target["maturity_level_ref"]
    expected_generation_status = target["generation_status"]
    imports = "import assert from 'node:assert/strict';\nimport test from 'node:test';\n"
    if runnable:
        imports += "import { spawnSync } from 'node:child_process';\nimport { fileURLToPath } from 'node:url';\n"
    imports += "import { readFileSync } from 'node:fs';\n"
    body = imports + (
        "\n"
        "const source = readFileSync(new URL('../src/commandPackage.ts', import.meta.url), 'utf8');\n"
        "const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));\n"
        "\n"
        "test('generated package metadata exposes expected commands', () => {\n"
        f"  const expected = {rendered_expected};\n"
        "  for (const command of expected) {\n"
        '    assert.match(source, new RegExp(`\\"name\\": \\\\"${command}\\\\"`));\n'
        "  }\n"
        "});\n"
        "\n"
        "test('generated package metadata exposes maturity and weak-agent routing status', () => {\n"
        "  const metadata = packageJson.agenticWorkspace;\n"
        f"  assert.equal(metadata.generationStatus, {expected_generation_status!r});\n"
        f"  assert.equal(metadata.maturity.id, {expected_maturity!r});\n"
        "  assert.equal(typeof metadata.maturity.summary, 'string');\n"
        "  assert.ok(metadata.maturity.summary.length > 0);\n"
        "  assert.ok(Array.isArray(metadata.maturity.promotion_requires));\n"
        "  assert.ok(metadata.maturity.promotion_requires.length > 0);\n"
    )
    if runnable:
        body += (
            "  assert.equal(metadata.fixtureOnly, false);\n"
            "  assert.equal(metadata.maturity.runnable, true);\n"
            "  assert.equal(metadata.maturity.weak_agent_routing, 'review-required');\n"
            "  assert.ok(packageJson.bin);\n"
        )
    else:
        body += (
            "  assert.equal(metadata.fixtureOnly, true);\n"
            "  assert.equal(metadata.maturity.runnable, false);\n"
            "  assert.equal(metadata.maturity.weak_agent_routing, 'forbidden');\n"
            "  assert.equal(packageJson.bin, undefined);\n"
        )
    body += "});\n"
    if runnable:
        body += (
            "\n"
            "test('generated runnable adapter delegates supported command to runtime process', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            "  const mockRuntime = fileURLToPath(new URL('./mock-runtime.mjs', import.meta.url));\n"
            '  const runtime = `"${process.execPath}" "${mockRuntime}"`;\n'
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


def render_outputs(
    manifest: dict[str, Any],
    *,
    repo_root: Path,
    source_path: str,
    regenerate_command: str,
) -> list[GeneratedOutput]:
    outputs: list[GeneratedOutput] = []
    maturity_levels = _maturity_levels(manifest)
    runtime_binding = manifest["generation_policy"]["non_python_runtime_binding"]
    for package in manifest["packages"]:
        for target in package["targets"]:
            root = repo_root / str(target["generated_root"])
            if target["kind"] == "python":
                outputs.append(
                    GeneratedOutput(
                        root / "__init__.py", _python_module(package, source_path=source_path, regenerate_command=regenerate_command)
                    )
                )
            elif target["kind"] == "typescript":
                outputs.append(
                    GeneratedOutput(
                        root / "package.json",
                        _typescript_package_json(
                            package, target, maturity_levels[target["maturity_level_ref"]], runtime_binding, source_path=source_path
                        ),
                    )
                )
                outputs.append(
                    GeneratedOutput(
                        root / "src" / "commandPackage.ts",
                        _typescript_module(package, source_path=source_path, regenerate_command=regenerate_command),
                    )
                )
                outputs.append(GeneratedOutput(root / "test" / "command-package.test.mjs", _typescript_test(package, target)))
                if _is_runnable_typescript_target(target):
                    outputs.append(
                        GeneratedOutput(
                            root / "src" / "cli.mjs",
                            _typescript_cli_module(package, target, source_path=source_path, regenerate_command=regenerate_command),
                        )
                    )
                    outputs.append(GeneratedOutput(root / "test" / "mock-runtime.mjs", _typescript_mock_runtime()))
    return outputs


def generate_command_packages(
    manifest: dict[str, Any],
    *,
    repo_root: Path,
    source_path: str,
    regenerate_command: str,
    check: bool,
) -> list[str]:
    stale_outputs: list[str] = []
    for output in render_outputs(manifest, repo_root=repo_root, source_path=source_path, regenerate_command=regenerate_command):
        if check:
            current = output.path.read_text(encoding="utf-8") if output.path.exists() else ""
            if current != output.content:
                stale_outputs.append(output.path.relative_to(repo_root).as_posix())
        else:
            output.path.parent.mkdir(parents=True, exist_ok=True)
            output.path.write_text(output.content, encoding="utf-8")
            print(f"[ok] wrote {output.path.relative_to(repo_root).as_posix()}")
    return stale_outputs
