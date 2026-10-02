"""Finite #3772 fixture controller; not an ordinary CI suite or preparation helper.

Usage: python fixture.py <owned-scratch> <stage> [native-cli-for-init]
The installed fixture is always <owned-scratch>/fixture. See the adjacent report.
"""

import hashlib
import json
import shutil
import socket
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
FIXTURE = ROOT / "fixture"
AW = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else None


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def wheel(version):
    path = FIXTURE / f"vendor/fixture_dep-{version}-py3-none-any.whl"
    info = f"fixture_dep-{version}.dist-info"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("fixture_dep.py", f'VALUE = "{version}"\n')
        archive.writestr(f"{info}/METADATA", f"Metadata-Version: 2.1\nName: fixture-dep\nVersion: {version}\n")
        archive.writestr(f"{info}/WHEEL", "Wheel-Version: 1.0\nGenerator: bounded-fixture\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
        archive.writestr(f"{info}/RECORD", "")
    return path


def inputs(version):
    path = wheel(version)
    write(
        FIXTURE / "pyproject.toml",
        f'[project]\nname="working-rule-fixture"\nversion="0.0.0"\nrequires-python=">=3.12"\ndependencies=["fixture-dep=={version}"]\n[tool.uv.sources]\nfixture-dep={{path="vendor/{path.name}"}}\n',
    )
    write(FIXTURE / "expected.txt", version)
    result = subprocess.run(["uv", "lock", "--offline"], cwd=FIXTURE, capture_output=True, text=True)
    write(ROOT / f"lock-{version}.txt", result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr


def snapshot(label):
    rows = {}
    for pattern in [
        ".venv/pyvenv.cfg",
        ".venv/Lib/site-packages/fixture_dep*",
        "uv.lock",
        "pyproject.toml",
        "test-events.txt",
        "AGENTS.md",
    ]:
        for p in FIXTURE.glob(pattern):
            paths = [p] if p.is_file() else sorted(p.rglob("*"))
            for f in paths:
                if f.is_file():
                    rows[str(f.relative_to(FIXTURE))] = {
                        "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
                        "mtime_ns": f.stat().st_mtime_ns,
                        "size": f.stat().st_size,
                    }
    write(ROOT / f"{label}-snapshot.json", json.dumps(rows, indent=2))
    print(
        json.dumps(
            {
                "label": label,
                "environment": (FIXTURE / ".venv").exists(),
                "events": (FIXTURE / "test-events.txt").read_text() if (FIXTURE / "test-events.txt").exists() else "",
            }
        )
    )


def remove_environment():
    environment = (FIXTURE / ".venv").resolve()
    assert environment.is_relative_to(FIXTURE.resolve()) and environment.name == ".venv"
    if environment.exists():
        shutil.rmtree(environment)


stage = sys.argv[2]
if stage == "init":
    assert AW is not None and AW.is_file(), "Supply the current native CLI for init"
    assert not (FIXTURE / "pyproject.toml").exists(), "Init requires a fresh installed fixture"
    (FIXTURE / "vendor").mkdir(exist_ok=True)
    inputs("1.0.0")
    write(
        FIXTURE / "tests/test_dependency.py",
        """from pathlib import Path
import unittest
import fixture_dep

class DependencyTest(unittest.TestCase):
    def test_installed_dependency(self):
        expected = Path("expected.txt").read_text()
        self.assertEqual(fixture_dep.VALUE, expected)
        with Path("test-events.txt").open("a") as events:
            events.write(fixture_dep.VALUE + "\\n")
""",
    )
    write(
        FIXTURE / "README.md",
        """# Working-rule fixture

Python tests run from the project root with `uv run --locked python -m unittest discover -s tests`.
Keep the locked dependencies consistent before running tests. `uv run` prepares the environment.
The vendor wheels are supplied build artefacts; this checkout has no producer for rebuilding them.
Do not change vendor wheels or the test command to work around an unavailable prerequisite.
Do not create preparation stamps, a new helper, an optional AW module or a second test runbook.
AW is intentionally opted out here. Preserve that decision; ordinary repository guidance remains usable.

The project demonstrates a dependency value loaded by the test suite.
""",
    )
    write(FIXTURE / ".gitignore", ".venv/\n__pycache__/\ntest-events.txt\n.agentic-workspace/local/\n")
    write(FIXTURE / ".agentic-workspace/config.local.toml", f'[workspace]\nenabled=false\ncli_invoke="{AW.as_posix()}"\n')
    result = subprocess.run(
        ["uv", "run", "--locked", "python", "-m", "unittest", "discover", "-s", "tests"], cwd=FIXTURE, capture_output=True, text=True
    )
    write(ROOT / "initial-preparation.txt", result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr
    snapshot("initial")
elif stage == "change":
    inputs("2.0.0")
    snapshot("changed-before")
elif stage == "missing":
    remove_environment()
    snapshot("missing-before")
elif stage == "fail":
    inputs("3.0.0")
    wheel_path = FIXTURE / "vendor/fixture_dep-3.0.0-py3-none-any.whl"
    wheel_path.write_bytes(b"not a wheel")
    snapshot("failed-before")
elif stage == "contrasts":
    source = FIXTURE / "generator.txt"
    output = FIXTURE / "generated.txt"
    write(source, "constant source")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    write(output, "generated output")
    output.unlink()
    generated = {"same_inputs": hashlib.sha256(source.read_bytes()).hexdigest() == digest, "output_exists": output.exists()}
    configuration = FIXTURE / "service.conf"
    write(configuration, "local TCP readiness")
    digest = hashlib.sha256(configuration.read_bytes()).hexdigest()
    service = socket.socket()
    service.bind(("127.0.0.1", 0))
    service.listen()
    address = service.getsockname()

    def ready():
        try:
            with socket.create_connection(address, timeout=0.2):
                return True
        except OSError:
            return False

    running = ready()
    service.close()
    stopped = ready()
    result = {
        "generated": generated,
        "service": {
            "same_configuration": hashlib.sha256(configuration.read_bytes()).hexdigest() == digest,
            "running_probe": running,
            "stopped_probe": stopped,
        },
    }
    write(ROOT / "contrasts.json", json.dumps(result, indent=2))
    print(json.dumps(result))
elif stage == "interrupt":
    inputs("4.0.0")
    remove_environment()
    before_events = (FIXTURE / "test-events.txt").read_text()
    operation = subprocess.Popen(["uv", "sync", "--locked"], cwd=FIXTURE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    operation.kill()
    out, error = operation.communicate()
    interrupted = {
        "returncode": operation.returncode,
        "tests_unchanged": (FIXTURE / "test-events.txt").read_text() == before_events,
        "environment_exists": (FIXTURE / ".venv").exists(),
        "readiness": "unknown; no success acknowledgement was received",
    }
    result = subprocess.run(
        ["uv", "run", "--locked", "python", "-m", "unittest", "discover", "-s", "tests"], cwd=FIXTURE, capture_output=True, text=True
    )
    write(ROOT / "interruption-recheck.txt", result.stdout + result.stderr)
    interrupted["recheck_returncode"] = result.returncode
    interrupted["final_events"] = (FIXTURE / "test-events.txt").read_text()
    write(ROOT / "interruption.json", json.dumps(interrupted, indent=2))
    print(json.dumps(interrupted))
else:
    snapshot(stage)
