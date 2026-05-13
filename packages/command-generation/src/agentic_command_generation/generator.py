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
    return target.get("maturity_level_ref") in {"runnable-read-only-adapter", "weak-agent-safe-adapter"}


def _is_weak_agent_safe_typescript_target(target: dict[str, Any]) -> bool:
    return target.get("maturity_level_ref") == "weak-agent-safe-adapter"


def _is_weak_agent_safe_python_target(target: dict[str, Any]) -> bool:
    return target.get("kind") == "python" and target.get("maturity_level_ref") == "weak-agent-safe-adapter"


def _is_runtime_backed_python_target(target: dict[str, Any]) -> bool:
    return target.get("kind") == "python" and target.get("maturity_level_ref") in {
        "runtime-backed-read-only-adapter",
        "weak-agent-safe-adapter",
    }


def _runtime_command_for_package(package: dict[str, Any], runtime_binding: dict[str, Any]) -> str:
    generated_package = _generated_package_module_for_package(package)
    if generated_package:
        return "python -c " + json.dumps(f"import sys; from {generated_package} import main; raise SystemExit(main(sys.argv[1:]))")
    return str(runtime_binding["default_runtime_command"])


def _generated_package_module_for_package(package: dict[str, Any]) -> str:
    binding = package.get("python_runtime_binding", {})
    if not isinstance(binding, dict):
        return ""
    return str(binding.get("generated_package_module") or "")


def _runtime_module_for_package(package: dict[str, Any]) -> str:
    binding = package.get("python_runtime_binding", {})
    if not isinstance(binding, dict):
        return ""
    return str(binding.get("runtime_module") or "")


def _python_adapter_commands(package: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        command for command in package["commands"] if command.get("status") == "generated" and isinstance(command.get("interface"), dict)
    ]


def _python_adapter_command_payload(package: dict[str, Any]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for command in _python_adapter_commands(package):
        interface = dict(command["interface"])
        operation_ref = dict(command["operation_ref"])
        payload.append(
            {
                "adapter_id": command["adapter_id"],
                "operation_id": operation_ref["id"],
                "operation_path": operation_ref["path"],
                "interface": interface,
            }
        )
    return payload


def _runtime_consumed_operation_outputs(
    package: dict[str, Any],
    *,
    repo_root: Path,
    root: Path,
) -> list[GeneratedOutput]:
    outputs: list[GeneratedOutput] = []
    emitted: set[str] = set()
    contracts_package_root = "agentic" + "_workspace"
    for command in _python_adapter_commands(package):
        operation_ref = command["operation_ref"]
        operation_path = str(operation_ref["path"])
        if operation_path in emitted:
            continue
        source = repo_root / "src" / contracts_package_root / "contracts" / operation_path
        if not source.is_file():
            continue
        operation = json.loads(source.read_text(encoding="utf-8"))
        ir_plan = operation.get("ir_plan", {})
        if not isinstance(ir_plan, dict) or ir_plan.get("status") not in {"representative", "complete"}:
            continue
        emitted.add(operation_path)
        outputs.append(GeneratedOutput(root / "generated_cli_package" / operation_path, _json_block(operation) + "\n"))
    return outputs


def _python_runtime_adapter_module(package: dict[str, Any], target: dict[str, Any], *, source_path: str, regenerate_command: str) -> str:
    weak_agent_routing = "allowed-read-only" if _is_weak_agent_safe_python_target(target) else "review-required"
    runnable = str(target.get("maturity_level_ref") in {"runtime-backed-read-only-adapter", "weak-agent-safe-adapter"})
    runtime_module = _runtime_module_for_package(package)
    main_function = ""
    if runtime_module:
        main_function = (
            "\n\n"
            "def main(argv: list[str] | None = None) -> int:\n"
            f"    from {runtime_module} import main as runtime_main\n\n"
            "    return runtime_main(argv)\n"
        )
    return (
        '"""Generated runtime-backed Python command adapter.\n\n'
        f"Source: {source_path}\n"
        f"Program: {package['program']}\n"
        f"Regenerate with: {regenerate_command}\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
        "import argparse\n"
        "import json\n"
        "from collections.abc import Callable\n"
        "from importlib.resources import files\n"
        "from pathlib import Path\n"
        "from typing import Any\n\n"
        "# DO NOT EDIT DIRECTLY.\n"
        f"# Command/interface changes belong in {source_path}.\n"
        "# Runtime behavior changes belong in hand-written operation/primitive implementation code.\n"
        f"# Regenerate with: {regenerate_command}\n"
        "\n\n"
        "def _load_generated_json(name: str) -> Any:\n"
        "    parts = tuple(part for part in name.replace('\\\\', '/').split('/') if part)\n"
        "    try:\n"
        '        return json.loads(files(__package__).joinpath(*parts).read_text(encoding="utf-8"))\n'
        "    except (AttributeError, FileNotFoundError, ModuleNotFoundError, TypeError):\n"
        '        return json.loads(Path(__file__).parent.joinpath(*parts).read_text(encoding="utf-8"))\n\n\n'
        'GENERATED_COMMAND_PACKAGE: dict[str, Any] = _load_generated_json("command_package.json")\n\n'
        '_GENERATED_ADAPTER_COMMANDS: list[dict[str, Any]] = _load_generated_json("adapter_commands.json")\n'
        "_GENERATED_COMMANDS_BY_NAME: dict[str, dict[str, Any]] = {\n"
        '    str(command["interface"]["name"]): command for command in _GENERATED_ADAPTER_COMMANDS\n'
        "}\n\n"
        "_GENERATED_OPERATION_PATHS_BY_ID: dict[str, str] = {\n"
        '    str(command["operation_id"]): str(command["operation_path"])\n'
        "    for command in _GENERATED_ADAPTER_COMMANDS\n"
        '    if "operation_path" in command\n'
        "}\n\n"
        f"_GENERATED_MATURITY_ID = {target['maturity_level_ref']!r}\n"
        f"_GENERATED_WEAK_AGENT_ROUTING = {weak_agent_routing!r}\n"
        f"_GENERATED_RUNNABLE = {runnable}\n\n"
        "RuntimeHandler = Callable[[str, argparse.Namespace], int]\n\n\n"
        "def generated_maturity() -> dict[str, object]:\n"
        "    return {\n"
        '        "id": _GENERATED_MATURITY_ID,\n'
        '        "runnable": _GENERATED_RUNNABLE,\n'
        '        "weak_agent_routing": _GENERATED_WEAK_AGENT_ROUTING,\n'
        "    }\n\n\n"
        "def generated_weak_agent_routing() -> str:\n"
        "    return _GENERATED_WEAK_AGENT_ROUTING\n\n\n"
        "def generated_command_names() -> tuple[str, ...]:\n"
        "    return tuple(sorted(_GENERATED_COMMANDS_BY_NAME))\n\n\n"
        "def generated_operation_ids() -> tuple[str, ...]:\n"
        '    return tuple(sorted(str(command["operation_id"]) for command in _GENERATED_ADAPTER_COMMANDS))\n\n\n'
        "def generated_operation_contract(operation_id: str) -> dict[str, Any]:\n"
        "    operation_path = _GENERATED_OPERATION_PATHS_BY_ID[str(operation_id)]\n"
        "    return _load_generated_json(operation_path)\n\n\n"
        "def supports_generated_command(argv: list[str] | tuple[str, ...]) -> bool:\n"
        "    return bool(argv) and str(argv[0]) in _GENERATED_COMMANDS_BY_NAME\n\n\n"
        "def _option_type(option_spec: dict[str, Any]) -> Any:\n"
        '    if option_spec.get("type") == "integer":\n'
        "        return int\n"
        "    return None\n\n\n"
        "def _add_option(parser: argparse.ArgumentParser, option_spec: dict[str, Any]) -> None:\n"
        "    kwargs: dict[str, Any] = {}\n"
        '    action = option_spec.get("action")\n'
        "    if isinstance(action, str):\n"
        '        kwargs["action"] = action\n'
        '    if "choices" in option_spec:\n'
        '        kwargs["choices"] = tuple(option_spec["choices"])\n'
        '    if "default" in option_spec:\n'
        '        kwargs["default"] = option_spec["default"]\n'
        '    if "nargs" in option_spec:\n'
        '        kwargs["nargs"] = option_spec["nargs"]\n'
        "    option_type = _option_type(option_spec)\n"
        "    if option_type is not None:\n"
        '        kwargs["type"] = option_type\n'
        '    if option_spec.get("required") is True:\n'
        '        kwargs["required"] = True\n'
        '    help_text = option_spec.get("help")\n'
        "    if isinstance(help_text, str):\n"
        '        kwargs["help"] = help_text\n'
        '    parser.add_argument(*option_spec["flags"], **kwargs)\n\n\n'
        "def build_generated_parser() -> argparse.ArgumentParser:\n"
        "    epilog = (\n"
        '        f"Weak-agent routing: {_GENERATED_WEAK_AGENT_ROUTING}\\n"\n'
        '        "Recovery: use one of the supported generated commands or route back to the canonical Python CLI."\n'
        "    )\n"
        f"    parser = argparse.ArgumentParser(prog={json.dumps(package['program'])}, description={json.dumps(package.get('summary', ''))}, epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)\n"
        '    subparsers = parser.add_subparsers(dest="command", required=True)\n'
        "    for command in _GENERATED_ADAPTER_COMMANDS:\n"
        '        interface = command["interface"]\n'
        "        command_parser = subparsers.add_parser(\n"
        '            str(interface["name"]),\n'
        '            help=str(interface["help"]),\n'
        '            description=str(interface["help"]),\n'
        "        )\n"
        '        command_parser.set_defaults(_generated_operation_id=command["operation_id"])\n'
        '        for option in interface.get("options", []):\n'
        "            _add_option(command_parser, option)\n"
        "    return parser\n\n\n"
        "def run_generated_command(argv: list[str] | tuple[str, ...], runtime_handler: RuntimeHandler) -> int:\n"
        "    parser = build_generated_parser()\n"
        "    args = parser.parse_args(list(argv))\n"
        '    operation_id = str(getattr(args, "_generated_operation_id"))\n'
        "    return runtime_handler(operation_id, args)\n"
        f"{main_function}"
    )


def _python_module(package: dict[str, Any], *, source_path: str, regenerate_command: str) -> str:
    return (
        '"""Generated command package metadata.\n\n'
        f"Source: {source_path}\n"
        f"Program: {package['program']}\n"
        f"Regenerate with: {regenerate_command}\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
        "import json\n"
        "from importlib.resources import files\n"
        "from pathlib import Path\n"
        "from typing import Any\n\n"
        "# DO NOT EDIT DIRECTLY.\n"
        f"# Command/package interface changes belong in {source_path}.\n"
        "# Runtime behavior changes belong in hand-written operation/primitive implementation code.\n"
        f"# Regenerate with: {regenerate_command}\n"
        "\n\n"
        "def _load_generated_json(name: str) -> Any:\n"
        "    try:\n"
        '        return json.loads(files(__package__).joinpath(name).read_text(encoding="utf-8"))\n'
        "    except (AttributeError, FileNotFoundError, ModuleNotFoundError, TypeError):\n"
        '        return json.loads(Path(__file__).with_name(name).read_text(encoding="utf-8"))\n\n\n'
        'GENERATED_COMMAND_PACKAGE: dict[str, Any] = _load_generated_json("command_package.json")\n'
    )


def _typescript_package_json(
    package: dict[str, Any],
    target: dict[str, Any],
    maturity: dict[str, Any],
    runtime_binding: dict[str, Any],
    *,
    source_path: str,
) -> str:
    runtime_command = _runtime_command_for_package(package, runtime_binding)
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
            "effectiveRuntimeCommand": runtime_command,
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


def _typescript_cli_module(
    package: dict[str, Any],
    target: dict[str, Any],
    runtime_binding: dict[str, Any],
    *,
    source_path: str,
    regenerate_command: str,
) -> str:
    command_names = sorted(command["command"]["name"] for command in package["commands"])
    rendered_commands = json.dumps(command_names)
    default_runtime_command = json.dumps(_runtime_command_for_package(package, runtime_binding))
    weak_agent_safe = _is_weak_agent_safe_typescript_target(target)
    weak_agent_status = "allowed-read-only" if weak_agent_safe else "review-required"
    recovery_command = f"{target['entrypoints'][0]} --help"
    return (
        "#!/usr/bin/env node\n"
        "// Generated runnable read-only adapter.\n"
        f"// Source: {source_path}\n"
        f"// Program: {package['program']}\n"
        f"// Regenerate with: {regenerate_command}\n"
        "// DO NOT EDIT DIRECTLY.\n\n"
        "import { spawnSync } from 'node:child_process';\n"
        "import { writeSync } from 'node:fs';\n\n"
        f"const supportedCommands = new Set({rendered_commands});\n"
        "const argv = process.argv.slice(2);\n"
        "const command = argv[0];\n\n"
        "if (!command || command === '--help' || command === '-h') {\n"
        f"  console.log(`Usage: {target['entrypoints'][0]} <command> [options]`);\n"
        "  console.log(`Supported generated commands: ${Array.from(supportedCommands).join(', ')}`);\n"
        f"  console.log('Weak-agent routing: {weak_agent_status}');\n"
        "  console.log('Recovery: use a supported generated command or route back to the canonical Python CLI.');\n"
        "  process.exit(0);\n"
        "}\n\n"
        "if (!supportedCommands.has(command)) {\n"
        "  console.error(`Unsupported generated command: ${command}`);\n"
        f"  console.error('Recovery: run {recovery_command} and choose one of the supported generated commands.');\n"
        "  process.exit(2);\n"
        "}\n\n"
        f"const runtimeCommand = process.env.AGENTIC_WORKSPACE_RUNTIME ?? {default_runtime_command};\n"
        "\n"
        "function splitRuntimeCommand(commandLine) {\n"
        "  const parts = [];\n"
        "  let current = '';\n"
        "  let quote = null;\n"
        "  for (const char of commandLine.trim()) {\n"
        "    if (quote) {\n"
        "      if (char === quote) quote = null;\n"
        "      else current += char;\n"
        "    } else if (char === '\"' || char === \"'\") {\n"
        "      quote = char;\n"
        "    } else if (/\\s/.test(char)) {\n"
        "      if (current) {\n"
        "        parts.push(current);\n"
        "        current = '';\n"
        "      }\n"
        "    } else {\n"
        "      current += char;\n"
        "    }\n"
        "  }\n"
        "  if (quote) throw new Error('runtime command has an unterminated quote');\n"
        "  if (current) parts.push(current);\n"
        "  if (parts.length === 0) throw new Error('runtime command is empty');\n"
        "  return parts;\n"
        "}\n"
        "\n"
        "let result;\n"
        "try {\n"
        "  const [runtimeExecutable, ...runtimeArgs] = splitRuntimeCommand(runtimeCommand);\n"
        "  result = spawnSync(runtimeExecutable, [...runtimeArgs, ...argv], { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 });\n"
        "} catch (error) {\n"
        "  console.error(`Adapter runtime handoff failed: ${error.message}`);\n"
        "  console.error('Recovery: verify AGENTIC_WORKSPACE_RUNTIME or run the canonical Python CLI directly.');\n"
        "  process.exit(1);\n"
        "}\n"
        "if (result.error) {\n"
        "  console.error(`Adapter runtime handoff failed: ${result.error.message}`);\n"
        "  console.error('Recovery: verify AGENTIC_WORKSPACE_RUNTIME or run the canonical Python CLI directly.');\n"
        "  process.exit(1);\n"
        "}\n"
        "if (result.stdout) writeSync(1, result.stdout);\n"
        "if (result.stderr) writeSync(2, result.stderr);\n"
        "process.exit(result.status ?? 1);\n"
    )


def _typescript_mock_runtime() -> str:
    return "const payload = {\n  command: process.argv[2],\n  args: process.argv.slice(2),\n};\nconsole.log(JSON.stringify(payload));\n"


def _typescript_test(package: dict[str, Any], target: dict[str, Any]) -> str:
    expected_commands = sorted(command["command"]["name"] for command in package["commands"])
    rendered_expected = json.dumps(expected_commands)
    sample_command = expected_commands[0]
    runnable = _is_runnable_typescript_target(target)
    weak_agent_safe = _is_weak_agent_safe_typescript_target(target)
    expected_maturity = target["maturity_level_ref"]
    expected_generation_status = target["generation_status"]
    expected_weak_agent_routing = "allowed-read-only" if weak_agent_safe else "review-required"
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
            f"  assert.equal(metadata.maturity.weak_agent_routing, {expected_weak_agent_routing!r});\n"
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
            f"  const result = spawnSync(process.execPath, [cli, {sample_command!r}, '--format', 'json'], {{\n"
            "    encoding: 'utf8',\n"
            "    env: { ...process.env, AGENTIC_WORKSPACE_RUNTIME: runtime },\n"
            "  });\n"
            "  assert.equal(result.status, 0);\n"
            "  const payload = JSON.parse(result.stdout);\n"
            f"  assert.equal(payload.command, {sample_command!r});\n"
            f"  assert.deepEqual(payload.args, [{sample_command!r}, '--format', 'json']);\n"
            "});\n"
            "\n"
            "test('generated runnable adapter preserves spaced argv values during runtime handoff', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            "  const mockRuntime = fileURLToPath(new URL('./mock-runtime.mjs', import.meta.url));\n"
            '  const runtime = `"${process.execPath}" "${mockRuntime}"`;\n'
            f"  const result = spawnSync(process.execPath, [cli, {sample_command!r}, '--task', 'value with spaces'], {{\n"
            "    encoding: 'utf8',\n"
            "    env: { ...process.env, AGENTIC_WORKSPACE_RUNTIME: runtime },\n"
            "  });\n"
            "  assert.equal(result.status, 0);\n"
            "  const payload = JSON.parse(result.stdout);\n"
            f"  assert.deepEqual(payload.args, [{sample_command!r}, '--task', 'value with spaces']);\n"
            "});\n"
            "\n"
            "test('generated runnable adapter exposes routing status and recovery guidance', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            "  const result = spawnSync(process.execPath, [cli, '--help'], { encoding: 'utf8' });\n"
            "  assert.equal(result.status, 0);\n"
            "  assert.match(result.stdout, /Supported generated commands:/);\n"
            f"  assert.match(result.stdout, /Weak-agent routing: {expected_weak_agent_routing}/);\n"
            "  assert.match(result.stdout, /Recovery:/);\n"
            "});\n"
            "\n"
            "test('generated runnable adapter rejects unsupported commands with recovery guidance', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            "  const result = spawnSync(process.execPath, [cli, '__unsupported__'], { encoding: 'utf8' });\n"
            "  assert.equal(result.status, 2);\n"
            "  assert.equal(result.stdout, '');\n"
            "  assert.match(result.stderr, /Unsupported generated command: __unsupported__/);\n"
            "  assert.match(result.stderr, /Recovery:/);\n"
            "});\n"
            "\n"
            "test('generated runnable adapter maps runtime handoff failure with recovery guidance', () => {\n"
            "  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));\n"
            f"  const result = spawnSync(process.execPath, [cli, {sample_command!r}], {{\n"
            "    encoding: 'utf8',\n"
            "    env: { ...process.env, AGENTIC_WORKSPACE_RUNTIME: '' },\n"
            "  });\n"
            "  assert.equal(result.status, 1);\n"
            "  assert.match(result.stderr, /Adapter runtime handoff failed:/);\n"
            "  assert.match(result.stderr, /Recovery:/);\n"
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
                module_path = root / "generated_cli_package" / "__init__.py"
                outputs.append(GeneratedOutput(root / "generated_cli_package" / "command_package.json", _json_block(package) + "\n"))
                if _is_runtime_backed_python_target(target):
                    outputs.extend(_runtime_consumed_operation_outputs(package, repo_root=repo_root, root=root))
                    outputs.append(
                        GeneratedOutput(
                            root / "generated_cli_package" / "adapter_commands.json",
                            _json_block(_python_adapter_command_payload(package)) + "\n",
                        )
                    )
                    outputs.append(
                        GeneratedOutput(
                            module_path,
                            _python_runtime_adapter_module(package, target, source_path=source_path, regenerate_command=regenerate_command),
                        )
                    )
                    continue
                outputs.append(
                    GeneratedOutput(module_path, _python_module(package, source_path=source_path, regenerate_command=regenerate_command))
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
                            _typescript_cli_module(
                                package,
                                target,
                                runtime_binding,
                                source_path=source_path,
                                regenerate_command=regenerate_command,
                            ),
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
            current = _read_generated_text(output.path) if output.path.exists() else ""
            if current != output.content:
                stale_outputs.append(output.path.relative_to(repo_root).as_posix())
        else:
            output.path.parent.mkdir(parents=True, exist_ok=True)
            output.path.write_text(output.content, encoding="utf-8", newline="\n")
            print(f"[ok] wrote {output.path.relative_to(repo_root).as_posix()}")
    return stale_outputs


def _read_generated_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()
