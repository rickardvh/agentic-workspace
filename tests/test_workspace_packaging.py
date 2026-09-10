"""Validate agentic-workspace artifacts against the checked-in payload inventory."""

from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tarfile
import time
import tomllib
from pathlib import Path
from zipfile import ZipFile

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_ROOT = WORKSPACE_ROOT / "src" / "agentic_workspace" / "_payload"
PACKAGE_PREFIX = Path("agentic_workspace") / "_payload"
MODULE_PACKAGE_DIRS = (
    WORKSPACE_ROOT / "packages" / "memory",
    WORKSPACE_ROOT / "packages" / "planning",
    WORKSPACE_ROOT / "packages" / "verification",
)
RELEASE_WHEEL_PATCHER = WORKSPACE_ROOT / "scripts" / "release" / "patch_workspace_release_wheel.py"


@contextlib.contextmanager
def _package_build_lock():
    lock_path = WORKSPACE_ROOT / "scratch" / "package-build.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            lock_path.mkdir()
            break
        except (FileExistsError, PermissionError):
            time.sleep(0.05)
    try:
        yield
    finally:
        lock_path.rmdir()


def _source_inventory() -> set[str]:
    return {path.relative_to(PAYLOAD_ROOT).as_posix() for path in PAYLOAD_ROOT.rglob("*") if path.is_file()}


@pytest.fixture(scope="module")
def workspace_artifacts(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    output_dir = tmp_path_factory.mktemp("workspace-artifacts")
    return _build_artifact(str(output_dir), "wheel"), _build_artifact(str(output_dir), "sdist")


@pytest.fixture(scope="module")
def workspace_wheel(workspace_artifacts: tuple[Path, Path]) -> Path:
    return workspace_artifacts[0]


@pytest.fixture(scope="module")
def workspace_sdist(workspace_artifacts: tuple[Path, Path]) -> Path:
    return workspace_artifacts[1]


@pytest.fixture(scope="module")
def workspace_wheelhouse(tmp_path_factory: pytest.TempPathFactory, workspace_wheel: Path) -> list[Path]:
    output_dir = tmp_path_factory.mktemp("workspace-wheelhouse")
    return _build_workspace_wheelhouse(str(output_dir), root_wheel=workspace_wheel)


def _build_artifact(tmpdir: str, artifact: str) -> Path:
    return _build_artifact_from(WORKSPACE_ROOT, tmpdir, artifact)


def _build_artifact_from(package_root: Path, tmpdir: str, artifact: str) -> Path:
    output_dir = Path(tmpdir)
    pattern = "*.whl" if artifact == "wheel" else "*.tar.gz"
    before = set(output_dir.glob(pattern))
    with _package_build_lock():
        subprocess.run(
            ["uv", "build", f"--{artifact}", "-o", tmpdir, str(package_root)],
            cwd=WORKSPACE_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    artifacts = [path for path in output_dir.glob(pattern) if path not in before]
    assert len(artifacts) == 1, f"Expected exactly 1 {artifact}, found {len(artifacts)}"
    return artifacts[0]


def _wheel_inventory(path: Path) -> set[str]:
    with ZipFile(path) as wheel:
        return {
            Path(name).relative_to(PACKAGE_PREFIX).as_posix()
            for name in wheel.namelist()
            if name.startswith(f"{PACKAGE_PREFIX.as_posix()}/") and not name.endswith("/")
        }


def _sdist_inventory(path: Path) -> set[str]:
    with tarfile.open(path, "r:gz") as archive:
        root_dir = archive.getnames()[0].split("/")[0]
        prefix = Path(root_dir) / "src" / PACKAGE_PREFIX
        return {
            Path(name).relative_to(prefix).as_posix()
            for name in archive.getnames()
            if name.startswith(f"{prefix.as_posix()}/") and not name.endswith("/")
        }


def _installed_inventory(wheel_path: Path, tmpdir: str) -> set[str]:
    install_root = Path(tmpdir) / "installed"
    subprocess.run(
        ["uv", "pip", "install", "--no-deps", "--target", str(install_root), str(wheel_path)],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    installed_payload = install_root / PACKAGE_PREFIX
    return {path.relative_to(installed_payload).as_posix() for path in installed_payload.rglob("*") if path.is_file()}


def _raw_wheel_inventory(path: Path) -> set[str]:
    with ZipFile(path) as wheel:
        return {name for name in wheel.namelist() if not name.endswith("/")}


def _raw_sdist_inventory(path: Path) -> set[str]:
    with tarfile.open(path, "r:gz") as archive:
        return {name for name in archive.getnames() if not name.endswith("/")}


def test_workspace_artifacts_match_checked_in_payload_inventory(workspace_artifacts: tuple[Path, Path], tmp_path: Path) -> None:
    expected_inventory = _source_inventory()
    wheel_path, sdist_path = workspace_artifacts

    wheel_inventory = _wheel_inventory(wheel_path)
    sdist_inventory = _sdist_inventory(sdist_path)
    installed_inventory = _installed_inventory(wheel_path, str(tmp_path))

    assert wheel_inventory == expected_inventory
    assert sdist_inventory == expected_inventory
    assert installed_inventory == expected_inventory


def test_workspace_package_declares_semver_identity() -> None:
    pyproject = tomllib.loads((WORKSPACE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert re.fullmatch(r"\d+\.\d+\.\d+", pyproject["project"]["version"])


def test_ci_retains_root_package_artifacts_for_explicit_exhaustive_dispatch() -> None:
    ci_text = (WORKSPACE_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    artifact_job = ci_text.partition("  workspace-package-artifacts:\n")[2].partition("\n  package-checks:\n")[0]

    assert "ready_for_review" in ci_text
    assert "if: ${{ github.event_name == 'workflow_dispatch' }}" in artifact_job
    assert "uv build --wheel --sdist --out-dir dist" in artifact_job
    assert "uv build --wheel --sdist --out-dir dist packages/memory" in artifact_job
    assert "uv build --wheel --sdist --out-dir dist packages/planning" in artifact_job
    assert "uv build --wheel --sdist --out-dir dist packages/verification" in artifact_job
    assert "test_installed_workspace_stack_runs_fresh_repo_cli_sequence" in artifact_job
    assert "test_release_root_wheel_installs_workspace_stack_from_same_release_assets" in artifact_job
    assert (
        "make packed-artifact-conformance PACKED_ARTIFACT_DIR=dist "
        "PACKED_ARTIFACT_RECEIPT=dist/generated-command-conformance-ci.json PACKED_ARTIFACT_CONTEXT=hosted-ci"
    ) in artifact_job
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1" in artifact_job


def test_typescript_instruction_runtime_has_no_source_checkout_python_dependency() -> None:
    support = (WORKSPACE_ROOT / "src/agentic_workspace/contracts/typescript_primitive_support.mjs").read_text(encoding="utf-8")
    instruction_runtime = support[support.index("function instructionsExecute") : support.index("function reportMemory")]

    assert "scripts/run_agentic_workspace.py" not in instruction_runtime
    assert "authoritative-python-boundary-unavailable" not in instruction_runtime


def test_ci_runs_release_proof_typecheck_before_generated_verification() -> None:
    ci_text = (WORKSPACE_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "run: make typecheck" in ci_text
    assert ci_text.index("run: make lint-workspace") < ci_text.index("run: make typecheck")
    assert ci_text.index("run: make typecheck") < ci_text.index("run: make verify-workspace")


def test_pr_semver_label_workflow_skips_draft_prs() -> None:
    workflow_text = (WORKSPACE_ROOT / ".github" / "workflows" / "pr-semver-label.yml").read_text(encoding="utf-8")

    assert "ready_for_review" in workflow_text
    assert "if: ${{ github.event.pull_request.draft == false }}" in workflow_text


def test_release_workflow_publishes_tagged_root_package_artifacts() -> None:
    release_text = (WORKSPACE_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert '"v[0-9]+.[0-9]+.[0-9]+"' in release_text
    assert "Verify tag targets coordinated release commit" in release_text
    assert 'coordinated_release.py verify --tag "${RELEASE_TAG}"' in release_text
    assert "must point at a commit reachable from origin/master" in release_text
    assert ".github/release-ownership.json" in release_text
    assert "uv build --wheel --sdist --out-dir dist" in release_text
    assert "uv build --wheel --sdist --out-dir dist packages/memory" in release_text
    assert "uv build --wheel --sdist --out-dir dist packages/planning" in release_text
    assert "uv build --wheel --sdist --out-dir dist packages/verification" in release_text
    assert "scripts/release/patch_workspace_release_wheel.py" in release_text
    assert "test_release_root_wheel_installs_workspace_stack_from_same_release_assets" in release_text
    assert "agentic-workspace-release-manifest.json" in release_text
    assert "source_commit" in release_text
    assert "body_path: .release/releases/${{ env.RELEASE_TAG }}.md" in release_text
    assert "SHA256SUMS" in release_text
    assert "softprops/action-gh-release@3d0d9888cb7fd7b750713d6e236d1fcb99157228 # v3.0.2" in release_text


def test_workspace_surface_manifest_payload_entries_exist_in_source_payload() -> None:
    manifest = json.loads((WORKSPACE_ROOT / "src" / "agentic_workspace" / "contracts" / "workspace_surfaces.json").read_text())

    missing = [path for path in manifest["payload_files"] if not (PAYLOAD_ROOT / path).is_file()]

    assert missing == []


def test_workspace_artifacts_ship_generated_cli_package_import_dependency(workspace_artifacts: tuple[Path, Path]) -> None:
    wheel_path, sdist_path = workspace_artifacts
    wheel_inventory = _raw_wheel_inventory(wheel_path)
    sdist_inventory = _raw_sdist_inventory(sdist_path)

    assert "agentic_workspace/generated_cli_package.py" not in wheel_inventory
    assert "agentic_workspace/generated_cli_package/__init__.py" not in wheel_inventory
    assert "agentic_workspace/_generated_cli_package_impl/__init__.py" in wheel_inventory
    assert "agentic_workspace/_generated_cli_package_impl/command_package.json" in wheel_inventory
    assert "agentic_workspace/_generated_cli_package_impl/adapter_commands.json" in wheel_inventory
    assert any(name.endswith("/generated/workspace/python/__init__.py") for name in sdist_inventory)
    assert any(name.endswith("/generated/workspace/python/command_package.json") for name in sdist_inventory)
    assert any(name.endswith("/generated/workspace/python/adapter_commands.json") for name in sdist_inventory)
    assert not any(name.endswith("/src/agentic_workspace/generated_cli_package.py") for name in sdist_inventory)
    assert not any(name.endswith("/src/agentic_workspace/generated_cli_package/__init__.py") for name in sdist_inventory)


def test_root_native_artifact_and_sdist_rebuild_inputs(workspace_wheel: Path, workspace_sdist: Path) -> None:
    executable = "agentic-workspace-core.exe" if os.name == "nt" else "agentic-workspace-core"
    with ZipFile(workspace_wheel) as wheel:
        assert f"agentic_workspace/_native/{executable}" in wheel.namelist()
        native = "agentic-workspace.exe" if os.name == "nt" else "agentic-workspace"
        assert f"agentic_workspace/_native/{native}" in wheel.namelist()
        metadata = wheel.read(next(name for name in wheel.namelist() if name.endswith(".dist-info/WHEEL"))).decode()
        assert "Root-Is-Purelib: false" in metadata
        assert "Tag: py3-none-" in metadata
        assert "none-any" not in metadata
        assert "manylinux" not in metadata
    inventory = _raw_sdist_inventory(workspace_sdist)
    for path in (
        "hatch_build.py",
        "Cargo.toml",
        "Cargo.lock",
        "crates/agentic-workspace-core/src/main.rs",
        "crates/agentic-workspace-cli/Cargo.toml",
        "src/agentic_workspace/contracts/schemas/separation_of_duty.schema.json",
        "generated/workspace/python/external_contract_bundle.json",
    ):
        assert any(name.endswith(f"/{path}") for name in inventory), path


def test_wheel_native_cli_runs_without_language_hosts_or_checkout(workspace_wheel: Path, tmp_path: Path) -> None:
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    repository = tmp_path / "repository"
    repository.mkdir()
    suffix = ".exe" if os.name == "nt" else ""
    with ZipFile(workspace_wheel) as wheel:
        metadata = wheel.read(next(name for name in wheel.namelist() if name.endswith(".dist-info/METADATA"))).decode()
        version_match = re.search(r"^Version: (.+)$", metadata, re.MULTILINE)
        assert version_match is not None
        version = version_match.group(1)
        for name in ("agentic-workspace", "agentic-workspace-core"):
            entry = wheel.getinfo(f"agentic_workspace/_native/{name}{suffix}")
            binary = binary_dir / f"{name}{suffix}"
            binary.write_bytes(wheel.read(entry))
            if os.name != "nt":
                mode = entry.external_attr >> 16
                assert mode & 0o111, "native wheel payload must preserve executable permission"
                binary.chmod(mode)
    environment = {**os.environ, "PATH": "", "PYTHONHOME": str(tmp_path / "absent-python")}
    # Only the extracted binaries and empty target are available to the process;
    # neither language package, the source checkout, nor Cargo supplies semantics.
    context = {"target": str(repository), "task": "Inspect the repository", "projection": "full"}
    native = subprocess.run(
        [
            str(binary_dir / f"agentic-workspace{suffix}"),
            "start",
            "--target",
            str(repository),
            "--task",
            context["task"],
            "--projection",
            "full",
        ],
        cwd=repository,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    native_result = json.loads(native.stdout)
    assert native_result["decision_packet"]["status"] == "direct"
    assert native_result["runtime_compatibility"]["observed_runtime"]["version"] == version
    transport = subprocess.run(
        [str(binary_dir / f"agentic-workspace-core{suffix}")],
        input=json.dumps({"start": context}),
        cwd=repository,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    assert json.loads(transport.stdout) == native_result
    assert list(repository.iterdir()) == []
    config = repository / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    epoch = native_result["runtime_compatibility"]["observed_runtime"]["reader_epoch"]
    config.write_text(f"schema_version=1\n[cli_compatibility]\nminimum_reader_epoch={epoch + 1}\n", encoding="utf-8")
    selection = repository / ".agentic-workspace/local/planning/owner-selection.json"
    selection.parent.mkdir(parents=True)
    selection.write_bytes(b"unknown content must not be interpreted or rewritten")
    blocked = subprocess.run(
        [
            str(binary_dir / f"agentic-workspace{suffix}"),
            "start",
            "--target",
            str(repository),
            "--task",
            context["task"],
            "--projection",
            "full",
        ],
        cwd=repository,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    rejected = json.loads(blocked.stdout)
    assert rejected["status"] == "blocked"
    assert rejected["failed_checks"] == ["minimum_reader_epoch"]
    assert rejected["managed_state_interpreted"] is False
    assert selection.read_bytes() == b"unknown content must not be interpreted or rewritten"


def test_root_wheel_ships_generated_cli_package_import_dependency(workspace_wheel: Path) -> None:
    inventory = _raw_wheel_inventory(workspace_wheel)

    assert "agentic_workspace/generated_command_adapters.py" not in inventory
    assert "agentic_workspace/generated_cli_package.py" not in inventory
    assert "agentic_workspace/generated_cli_package/__init__.py" not in inventory
    assert "agentic_workspace/_generated_cli_package_impl/__init__.py" in inventory
    assert "agentic_workspace/_generated_cli_package_impl/command_package.json" in inventory
    assert "agentic_workspace/_generated_cli_package_impl/adapter_commands.json" in inventory
    assert "agentic_workspace/_generated_cli_package_impl/external_consumer_profile.json" in inventory
    assert "agentic_workspace/_generated_cli_package_impl/external_operation_conformance_receipts.json" in inventory
    assert "agentic_workspace/client.py" in inventory


def test_root_sdist_ships_generated_cli_package_import_dependency(workspace_sdist: Path) -> None:
    inventory = _raw_sdist_inventory(workspace_sdist)

    assert not any(name.endswith("/src/agentic_workspace/generated_command_adapters.py") for name in inventory)
    assert any(name.endswith("/generated/memory/python/generated_command_adapters.json") for name in inventory)
    assert any(name.endswith("/generated/planning/python/generated_command_adapters.json") for name in inventory)
    assert any(name.endswith("/generated/workspace/python/generated_command_adapters.json") for name in inventory)
    assert not any(name.endswith("/src/agentic_workspace/generated_cli_package.py") for name in inventory)
    assert not any(name.endswith("/src/agentic_workspace/generated_cli_package/__init__.py") for name in inventory)
    assert any(name.endswith("/generated/workspace/python/__init__.py") for name in inventory)
    assert any(name.endswith("/generated/workspace/python/command_package.json") for name in inventory)
    assert any(name.endswith("/generated/workspace/python/adapter_commands.json") for name in inventory)


def test_installed_workspace_wheel_imports_cli_module(workspace_wheel: Path, tmp_path: Path) -> None:
    install_root = tmp_path / "installed"
    subprocess.run(
        ["uv", "pip", "install", "--no-deps", "--target", str(install_root), str(workspace_wheel)],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from agentic_workspace.cli import main; from agentic_workspace.native_core import cli_binary; assert callable(main); print(cli_binary())",
        ],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(install_root)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    native = Path(result.stdout.strip())
    assert native.is_relative_to(install_root) and native.is_file()
    # The wheel's actual product binary works without a language runtime or
    # source-checkout helper on PATH; the Python entry point is optional.
    clean_env = {key: value for key, value in os.environ.items() if key not in {"AGENTIC_WORKSPACE_CORE_BINARY", "PYTHONPATH"}}
    clean_env["PATH"] = ""
    started = subprocess.run(
        [str(native), "start", "--target", str(tmp_path), "--task", "Inspect the installed native artifact", "--format", "json"],
        cwd=tmp_path,
        env=clean_env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert started.returncode == 0, started.stderr
    assert "decision_packet" in json.loads(started.stdout)


def test_installed_workspace_wheel_exposes_public_external_client(workspace_wheel: Path, tmp_path: Path) -> None:
    install_root = tmp_path / "installed-client"
    subprocess.run(
        ["uv", "pip", "install", "--no-deps", "--target", str(install_root), str(workspace_wheel)],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    result = subprocess.run(
        [sys.executable, "-c", "from agentic_workspace import external_consumer_profile; assert external_consumer_profile()['operations']"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(install_root)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_workspace_runtime_entrypoint_stays_off_command_generation() -> None:
    pyproject = tomllib.loads((WORKSPACE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "command-generation" not in pyproject["project"]["dependencies"]
    assert pyproject["project"]["scripts"]["agentic-workspace"] == "agentic_workspace.cli:main"


def test_installed_workspace_stack_runs_fresh_repo_cli_sequence(workspace_wheelhouse: list[Path], tmp_path: Path) -> None:
    workspace_exe = _install_workspace_stack_venv(wheelhouse=workspace_wheelhouse, tmpdir_path=tmp_path)
    assert _venv_site_package_entry_names(tmp_path / ".venv", "command_generation") == []
    _assert_workspace_stack_runs_fresh_repo_cli_sequence(workspace_exe=workspace_exe, tmp_path=tmp_path)


def test_release_root_wheel_installs_workspace_stack_from_same_release_assets(workspace_wheelhouse: list[Path], tmp_path: Path) -> None:
    version = tomllib.loads((WORKSPACE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    release_dist = tmp_path / "release-dist"
    release_dist.mkdir()
    release_wheels = [release_dist / wheel.name for wheel in workspace_wheelhouse]
    for source, target in zip(workspace_wheelhouse, release_wheels, strict=True):
        target.write_bytes(source.read_bytes())

    patcher = _load_release_wheel_patcher()
    patched_root = patcher.patch_workspace_wheel(
        dist_dir=release_dist,
        version=version,
        release_asset_base_url=release_dist.resolve().as_uri(),
    )
    workspace_exe = _install_workspace_root_release_venv(root_wheel=patched_root, tmpdir_path=tmp_path)
    assert _venv_site_package_entry_names(tmp_path / ".venv-release", "agentic_workspace_memory")
    assert _venv_site_package_entry_names(tmp_path / ".venv-release", "agentic_workspace_planning")
    assert _venv_site_package_entry_names(tmp_path / ".venv-release", "agentic_workspace_verification")
    _assert_workspace_stack_runs_fresh_repo_cli_sequence(workspace_exe=workspace_exe, tmp_path=tmp_path)


def _assert_workspace_stack_runs_fresh_repo_cli_sequence(*, workspace_exe: Path, tmp_path: Path) -> None:
    from tests.test_native_planning_create import material

    target = tmp_path / "repo"
    target.mkdir()
    retained = target / "unrelated.txt"
    retained.write_text("Preserve unrelated package-consumer work.")
    task = "Maintain the native packaged Planning owner"

    def call(request=None, invocation=None):
        args = ["invoke" if invocation else "start", "--target", str(target), "--task", task, "--format", "json", "--projection", "full"]
        if request is not None or invocation is not None:
            packet = tmp_path / "native-request.json"
            packet.write_text(json.dumps(invocation if invocation is not None else request))
            args.extend(["--input", str(packet)])
        return _run_workspace_console_json(workspace_exe, tmp_path, *args)

    initial = call()
    create = initial["planning"]["creation_requests"][0]
    create["arguments"] = {"material": material()}
    created = call(invocation=call(create)["decision_packet"]["primary_action"])
    selection = call()["planning"]["created_owner"]["selection_request"]
    call(invocation=call(selection)["decision_packet"]["primary_action"])
    current = call()
    assert current["planning"]["current_owner"]["current"] is True
    update = current["planning"]["update_requests"][0]
    body = json.loads((target / created["value"]["owner_path"]).read_bytes())
    update["arguments"]["material"] = {key: body[key] for key in material()}
    update["arguments"]["material"].update(lifecycle=body["lifecycle"], phase=body["phase"])
    update["arguments"]["material"]["continuation"]["frontier"] = "The installed native writer retained the next outcome."
    call(invocation=call(update)["decision_packet"]["primary_action"])
    recovery = call()["planning"]["requests"][0]
    call(invocation=call(recovery)["decision_packet"]["primary_action"])
    assert call()["planning"]["current_owner"]["current"] is True
    path = target / created["value"]["owner_path"]
    final = json.loads(path.read_bytes())
    assert final["id"] == body["id"] and final["scope"] == body["scope"]
    assert final["continuation"]["frontier"] == "The installed native writer retained the next outcome."
    assert retained.read_text() == "Preserve unrelated package-consumer work."
    assert not (target / ".agentic-workspace/local/cache/generated-cli-fingerprint.json").exists()


def _build_workspace_wheelhouse(tmpdir: str, *, root_wheel: Path) -> list[Path]:
    wheel_paths = [root_wheel]
    wheel_paths.extend(_build_artifact_from(package_dir, tmpdir, "wheel") for package_dir in MODULE_PACKAGE_DIRS)
    names = {path.name for path in wheel_paths}
    assert any(name.startswith("agentic_workspace-") for name in names)
    assert any(name.startswith("agentic_workspace_memory-") for name in names)
    assert any(name.startswith("agentic_workspace_planning-") for name in names)
    assert any(name.startswith("agentic_workspace_verification-") for name in names)
    return wheel_paths


def _install_workspace_stack_venv(*, wheelhouse: list[Path], tmpdir_path: Path) -> Path:
    venv_path = tmpdir_path / ".venv"
    subprocess.run(
        ["uv", "venv", str(venv_path)],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    python_path = _venv_python(venv_path)
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python_path),
            *(str(path) for path in wheelhouse),
        ],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return _venv_script(venv_path, "agentic-workspace")


def _install_workspace_root_release_venv(*, root_wheel: Path, tmpdir_path: Path) -> Path:
    venv_path = tmpdir_path / ".venv-release"
    subprocess.run(
        ["uv", "venv", str(venv_path)],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    python_path = _venv_python(venv_path)
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python_path),
            str(root_wheel),
        ],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return _venv_script(venv_path, "agentic-workspace")


def _load_release_wheel_patcher():
    spec = importlib.util.spec_from_file_location("release_wheel_patcher_under_test", RELEASE_WHEEL_PATCHER)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _run_workspace_console_json(workspace_exe: Path, cwd: Path, *args: str) -> dict[str, object]:
    result = subprocess.run(
        [str(workspace_exe), *args],
        cwd=cwd,
        env={key: value for key, value in os.environ.items() if key not in {"AGENTIC_WORKSPACE_CORE_BINARY", "PYTHONPATH"}},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _venv_python(venv_path: Path) -> Path:
    if os.name == "nt":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def _venv_script(venv_path: Path, name: str) -> Path:
    if os.name == "nt":
        return venv_path / "Scripts" / f"{name}.exe"
    return venv_path / "bin" / name


def _venv_site_package_entry_names(venv_path: Path, prefix: str) -> list[str]:
    if os.name == "nt":
        site_packages = venv_path / "Lib" / "site-packages"
    else:
        candidates = sorted((venv_path / "lib").glob("python*/site-packages"))
        assert candidates, f"site-packages not found under {venv_path}"
        site_packages = candidates[0]
    pattern = f"{prefix}*"
    return sorted(path.name for path in site_packages.glob(pattern) if path.exists())
