from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=REPO_ROOT, env=env, check=True)


def _venv_python(venv_root: Path) -> Path:
    if os.name == "nt":
        return venv_root / "Scripts" / "python.exe"
    return venv_root / "bin" / "python"


def _default_wheel() -> Path | None:
    sibling_dist = REPO_ROOT.parent / "command-generation" / "dist"
    wheels = sorted(sibling_dist.glob("command_generation-*.whl"))
    return wheels[-1] if wheels else None


def _installed_probe_script() -> str:
    return """
import importlib.metadata
import json
import command_generation

print(json.dumps({
    "version": importlib.metadata.version("command-generation"),
    "module_file": command_generation.__file__,
}, sort_keys=True))
"""


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prove AW generated-command checks consume a built command-generation artifact."
    )
    parser.add_argument("--wheel", type=Path, default=None, help="Built command-generation wheel to install.")
    parser.add_argument("--expected-version", default="", help="Expected command-generation version.")
    parser.add_argument(
        "--forbid-source-root",
        type=Path,
        default=REPO_ROOT.parent / "command-generation",
        help="Fail if the installed command_generation module resolves under this source checkout.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    wheel = args.wheel or _default_wheel()
    if wheel is None or not wheel.is_file():
        print("No built command-generation wheel found; pass --wheel or build the sibling package first.", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="aw-cg-artifact-proof-") as tmp:
        venv_root = Path(tmp) / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(venv_root)
        python = _venv_python(venv_root)
        _run([str(python), "-m", "pip", "install", "--no-cache-dir", str(wheel), "jsonschema"])
        _run([str(python), "-m", "pip", "install", "--no-deps", "-e", str(REPO_ROOT)])

        probe = subprocess.run(
            [str(python), "-c", _installed_probe_script()],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(probe.stdout)
        installed_version = str(payload.get("version", ""))
        if args.expected_version and installed_version != args.expected_version:
            print(
                f"command-generation artifact version mismatch: expected {args.expected_version}, got {installed_version}",
                file=sys.stderr,
            )
            return 1
        module_file = Path(str(payload.get("module_file", ""))).resolve()
        forbid_source_root = args.forbid_source_root.resolve()
        if module_file == forbid_source_root or forbid_source_root in module_file.parents:
            print(f"command_generation imported from source checkout, not artifact: {module_file}", file=sys.stderr)
            return 1

        env = os.environ.copy()
        source_roots = [
            REPO_ROOT,
            REPO_ROOT / "src",
            REPO_ROOT / "packages" / "planning" / "src",
            REPO_ROOT / "packages" / "memory" / "src",
            REPO_ROOT / "packages" / "verification" / "src",
        ]
        env["PYTHONPATH"] = os.pathsep.join(str(path) for path in source_roots)
        commands = [
            [str(python), "scripts/generate/generate_command_packages.py", "--check"],
            [str(python), "scripts/check/check_generated_command_packages.py"],
            [str(python), "scripts/check/check_generated_command_packages.py", "--aw-primitive-ownership", "--format", "json"],
            [str(python), "scripts/check/run_operation_conformance_tests.py", "--target", "all"],
        ]
        for command in commands:
            _run(command, env=env)

        print(
            json.dumps(
                {
                    "kind": "agentic-workspace/command-generation-artifact-consumption-proof/v1",
                    "status": "satisfied",
                    "wheel": str(wheel),
                    "installed_version": installed_version,
                    "module_file": str(module_file),
                    "source_tree_import": False,
                    "proof_commands": commands,
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
