from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR_SCRIPT_ROOT = REPO_ROOT / "scripts" / "generate"
if str(GENERATOR_SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(GENERATOR_SCRIPT_ROOT))

from workspace_command_generation import SCHEMA_PATH, SOURCE_PATH, load_workspace_command_package_ir  # noqa: E402


def _run(command: list[str]) -> int:
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    return int(completed.returncode)


def _python_executable() -> str:
    return sys.executable or "python"


def _conformance_env(*, runtime: str | None = None) -> dict[str, str]:
    env = os.environ.copy()
    paths = [str(REPO_ROOT / "src")]
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        paths.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    if runtime is not None:
        env["AGENTIC_WORKSPACE_RUNTIME"] = runtime
    return env


def _capture(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)


def _selected_defaults_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    return {
        "profile": payload.get("profile"),
        "surface": payload.get("surface"),
        "section": payload.get("selector", {}).get("section") if isinstance(payload.get("selector"), dict) else None,
        "matched": payload.get("matched"),
        "default_canonical_agent_instructions_file": (
            payload.get("answer", {}).get("default_canonical_agent_instructions_file") if isinstance(payload.get("answer"), dict) else None
        ),
    }


def _run_adapter_conformance(*, require_node: bool) -> list[str]:
    errors: list[str] = []
    node = shutil.which("node")
    if node is None:
        message = "adapter conformance skipped: node is not available"
        if require_node:
            return [message]
        print(message)
        return []

    cli = REPO_ROOT / "generated" / "typescript" / "workspace-cli" / "src" / "cli.mjs"
    if not cli.is_file():
        return ["adapter conformance failed before execution: generated/typescript/workspace-cli/src/cli.mjs is missing"]

    python = _python_executable()
    with tempfile.TemporaryDirectory(prefix="agentic-workspace-generated-adapter-") as tmp:
        temp_root = Path(tmp)
        shim = temp_root / "agentic_workspace_cli_shim.py"
        shim.write_text(
            "import sys\n"
            f"sys.path.insert(0, {str(REPO_ROOT / 'src')!r})\n"
            "from agentic_workspace.cli import main\n"
            "raise SystemExit(main(sys.argv[1:]))\n",
            encoding="utf-8",
        )
        runtime = f'"{python}" "{shim}"'
        fixture_root = temp_root / "minimal-repo"
        (fixture_root / ".git").mkdir(parents=True)
        (fixture_root / ".git" / ".keep").write_text("", encoding="utf-8")
        (fixture_root / "README.md").write_text("# Fixture\n", encoding="utf-8")

        success_args = ["defaults", "--section", "startup", "--format", "json"]
        canonical = _capture(
            [python, str(shim), *success_args],
            cwd=fixture_root,
            env=_conformance_env(),
        )
        if canonical.returncode != 0:
            return [f"runtime primitive failure: canonical defaults command exited {canonical.returncode}; stderr={canonical.stderr!r}"]
        try:
            canonical_fields = _selected_defaults_fields(canonical.stdout)
        except json.JSONDecodeError as exc:
            return [f"runtime primitive failure: canonical defaults stdout was not JSON: {exc}"]
        expected_fields = {
            "profile": "compact-contract-answer/v1",
            "surface": "defaults",
            "section": "startup",
            "matched": True,
            "default_canonical_agent_instructions_file": "AGENTS.md",
        }
        if canonical_fields != expected_fields:
            return [
                "runtime primitive failure: canonical defaults output shape drifted; "
                f"expected selected fields {expected_fields!r}, got {canonical_fields!r}"
            ]

        adapter = _capture(
            [node, str(cli), *success_args],
            cwd=fixture_root,
            env=_conformance_env(runtime=runtime),
        )
        if adapter.returncode != canonical.returncode:
            errors.append(
                "adapter failure: defaults exit code drifted from canonical process; "
                f"expected {canonical.returncode}, got {adapter.returncode}; stderr={adapter.stderr!r}"
            )
        else:
            try:
                adapter_fields = _selected_defaults_fields(adapter.stdout)
            except json.JSONDecodeError as exc:
                errors.append(f"adapter failure: defaults stdout was not JSON: {exc}; stdout={adapter.stdout!r}")
            else:
                if adapter_fields != canonical_fields:
                    errors.append(
                        "adapter failure: defaults JSON selected fields drifted from canonical process; "
                        f"expected {canonical_fields!r}, got {adapter_fields!r}"
                    )
        if adapter.stderr.strip():
            errors.append(f"adapter failure: defaults emitted unexpected stderr: {adapter.stderr!r}")

        invalid_args = ["defaults", "--section", "startup", "--format", "json", "--definitely-invalid"]
        canonical_invalid = _capture(
            [python, str(shim), *invalid_args],
            cwd=fixture_root,
            env=_conformance_env(),
        )
        if canonical_invalid.returncode == 0 or not canonical_invalid.stderr.strip():
            errors.append(
                "runtime primitive failure: canonical invalid-option behavior did not fail with stderr; "
                f"exit={canonical_invalid.returncode}, stderr={canonical_invalid.stderr!r}"
            )
        adapter_invalid = _capture(
            [node, str(cli), *invalid_args],
            cwd=fixture_root,
            env=_conformance_env(runtime=runtime),
        )
        if adapter_invalid.returncode != canonical_invalid.returncode:
            errors.append(
                "adapter failure: invalid-option exit code drifted from canonical process; "
                f"expected {canonical_invalid.returncode}, got {adapter_invalid.returncode}"
            )
        if bool(adapter_invalid.stderr.strip()) != bool(canonical_invalid.stderr.strip()):
            errors.append(
                "adapter failure: invalid-option stderr presence drifted from canonical process; "
                f"canonical={canonical_invalid.stderr!r}, adapter={adapter_invalid.stderr!r}"
            )

        unsupported = _capture(
            [node, str(cli), "workspace-status", "--format", "json"],
            cwd=fixture_root,
            env=_conformance_env(runtime=runtime),
        )
        if unsupported.returncode != 2 or "Unsupported generated command" not in unsupported.stderr or unsupported.stdout.strip():
            errors.append(
                "adapter failure: unsupported command refusal drifted; "
                f"exit={unsupported.returncode}, stdout={unsupported.stdout!r}, stderr={unsupported.stderr!r}"
            )

    return errors


def _validate_static_surfaces() -> list[str]:
    errors: list[str] = []
    expected_levels = {
        "metadata-proof-fixture",
        "parser-help-proof",
        "runnable-read-only-adapter",
        "runtime-backed-read-only-adapter",
        "weak-agent-safe-adapter",
        "mutation-capable-adapter",
        "deferred",
    }
    ir_path = REPO_ROOT / SOURCE_PATH
    schema_path = REPO_ROOT / SCHEMA_PATH
    if not ir_path.is_file():
        errors.append("src/agentic_workspace/contracts/command_package_ir.json is missing")
    if not schema_path.is_file():
        errors.append("packages/command-generation/schemas/command_package_ir.schema.json is missing")
    if errors:
        return errors
    try:
        ir = load_workspace_command_package_ir(repo_root=REPO_ROOT)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"command-package IR validation failed: {exc}")
    else:
        maturity_policy = ir.get("generation_policy", {}).get("generated_package_maturity", {})
        level_ids = {level.get("id") for level in maturity_policy.get("levels", []) if isinstance(level, dict)}
        missing = expected_levels - level_ids
        if missing:
            errors.append(f"command_package_ir.json missing generated package maturity levels: {sorted(missing)!r}")
        routing_rule = str(maturity_policy.get("routing_rule", ""))
        if "Weak agents may use only generated targets" not in routing_rule:
            errors.append("command_package_ir.json maturity routing rule does not protect weak-agent routing")
        packages = {package.get("id"): package for package in ir.get("packages", []) if isinstance(package, dict)}
        expected_python_promotions = {
            "root-workspace": "agentic-workspace",
            "planning-bootstrap": "agentic-planning-bootstrap",
            "memory-bootstrap": "agentic-memory-bootstrap",
        }
        for package_id, program in expected_python_promotions.items():
            package = packages.get(package_id)
            if not isinstance(package, dict):
                errors.append(f"command_package_ir.json is missing package {package_id!r}")
                continue
            python_targets = [target for target in package.get("targets", []) if isinstance(target, dict) and target.get("kind") == "python"]
            if not python_targets:
                errors.append(f"command_package_ir.json package {package_id!r} is missing a Python generated target")
                continue
            python_target = python_targets[0]
            if python_target.get("maturity_level_ref") != "runtime-backed-read-only-adapter":
                errors.append(
                    f"command_package_ir.json package {package_id!r} Python target is not runtime-backed; "
                    f"got {python_target.get('maturity_level_ref')!r}"
                )
            if python_target.get("generation_status") != "runtime-backed-read-only-adapter":
                errors.append(
                    f"command_package_ir.json package {package_id!r} Python generation_status is not runtime-backed; "
                    f"got {python_target.get('generation_status')!r}"
                )
            if package.get("program") != program:
                errors.append(f"command_package_ir.json package {package_id!r} program drifted from {program!r}")
        generated_entrypoints = {
            "src/agentic_workspace/cli.py": "agentic_workspace.generated_cli_package",
            "packages/planning/src/repo_planning_bootstrap/cli.py": "repo_planning_bootstrap.generated_cli_package",
            "packages/memory/src/repo_memory_bootstrap/cli.py": "repo_memory_bootstrap.generated_cli_package",
        }
        for relative_path, import_name in generated_entrypoints.items():
            text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
            main_index = text.find("def main(")
            generated_index = text.find("_run_generated_cli_package_if_supported", main_index)
            parser_index = text.find("build_parser()", main_index)
            if import_name not in text:
                errors.append(f"{relative_path} does not import the generated Python CLI package")
            if main_index == -1 or generated_index == -1 or parser_index == -1 or generated_index > parser_index:
                errors.append(f"{relative_path} does not route generated Python adapters before the handwritten parser")
    dockerfile = REPO_ROOT / "generated" / "typescript" / "Dockerfile"
    if not dockerfile.is_file():
        errors.append("generated/typescript/Dockerfile is missing")
    conformance_dockerfile = REPO_ROOT / "generated" / "typescript" / "Dockerfile.conformance"
    if not conformance_dockerfile.is_file():
        errors.append("generated/typescript/Dockerfile.conformance is missing")
    for package in ("workspace-cli", "planning-cli", "memory-cli"):
        package_root = REPO_ROOT / "generated" / "typescript" / package
        for relative in ("package.json", "src/commandPackage.ts", "test/command-package.test.mjs"):
            if not (package_root / relative).is_file():
                errors.append(f"generated/typescript/{package}/{relative} is missing")
        package_json_path = package_root / "package.json"
        if package_json_path.is_file():
            payload = json.loads(package_json_path.read_text(encoding="utf-8"))
            metadata = payload.get("agenticWorkspace", {})
            maturity = metadata.get("maturity", {})
            is_runnable = maturity.get("id") == "runnable-read-only-adapter"
            if not maturity.get("summary") or not maturity.get("promotion_requires"):
                errors.append(f"generated/typescript/{package}/package.json maturity is missing summary or promotion criteria")
            if is_runnable and not (package_root / "src" / "cli.mjs").is_file():
                errors.append(f"generated/typescript/{package}/src/cli.mjs is missing for runnable target")
            if is_runnable and "bin" not in payload:
                errors.append(f"generated/typescript/{package}/package.json is missing bin entry for runnable target")
            if is_runnable and maturity.get("weak_agent_routing") != "review-required":
                errors.append(f"generated/typescript/{package}/package.json runnable target is missing review-required weak-agent routing")
            if not is_runnable and (maturity.get("weak_agent_routing") != "forbidden" or maturity.get("runnable") is not False):
                errors.append(f"generated/typescript/{package}/package.json maturity does not mark proof fixture as non-runnable")
            if bool(metadata.get("fixtureOnly")) == is_runnable:
                errors.append(f"generated/typescript/{package}/package.json fixtureOnly does not match maturity runnable state")
    return errors


def _run_docker(tag: str, *, dockerfile: str, require_docker: bool) -> int:
    if shutil.which("docker") is None:
        print("docker is not available; cannot run generated TypeScript package container proof")
        return 1 if require_docker else 0
    info = subprocess.run(["docker", "info"], cwd=REPO_ROOT, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if info.returncode:
        detail = info.stderr.strip().splitlines()
        suffix = f": {detail[0]}" if detail else ""
        print(f"docker daemon is not available; skipped generated TypeScript package container proof{suffix}")
        return 1 if require_docker else 0
    build = _run(["docker", "build", "-f", dockerfile, "-t", tag, "."])
    if build:
        return build
    return _run(["docker", "run", "--rm", tag])


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check generated command package outputs.")
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Run generated TypeScript package tests inside Docker.",
    )
    parser.add_argument(
        "--docker-conformance",
        action="store_true",
        help="Run runnable generated adapter canonical-runtime conformance inside Docker.",
    )
    parser.add_argument(
        "--conformance",
        action="store_true",
        help="Run black-box conformance for runnable generated adapters using local Node and the canonical Python CLI.",
    )
    parser.add_argument(
        "--require-node",
        action="store_true",
        help="Fail instead of skipping adapter conformance when Node is unavailable.",
    )
    parser.add_argument(
        "--tag",
        default="agentic-workspace-generated-typescript-cli-test",
        help="Docker image tag used for generated TypeScript package tests.",
    )
    parser.add_argument(
        "--require-docker",
        action="store_true",
        help="Fail instead of skipping when Docker is unavailable.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    generator = REPO_ROOT / "scripts" / "generate" / "generate_command_packages.py"
    freshness = _run([_python_executable(), str(generator), "--check"])
    if freshness:
        return freshness
    errors = _validate_static_surfaces()
    if errors:
        for error in errors:
            print(error)
        return 1
    if args.conformance:
        conformance_errors = _run_adapter_conformance(require_node=bool(args.require_node))
        if conformance_errors:
            for error in conformance_errors:
                print(error)
            return 1
        print("[ok] generated command package adapter conformance")
    docker_status = 0
    if args.docker:
        docker_status = _run_docker(
            str(args.tag),
            dockerfile="generated/typescript/Dockerfile",
            require_docker=bool(args.require_docker),
        )
        if docker_status:
            return docker_status
    if args.docker_conformance:
        docker_status = _run_docker(
            f"{args.tag}-conformance",
            dockerfile="generated/typescript/Dockerfile.conformance",
            require_docker=bool(args.require_docker),
        )
        if docker_status:
            return docker_status
    if args.docker or args.docker_conformance:
        print("[ok] generated command package Docker proof")
        return 0
    print("[ok] generated command package static proof")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
