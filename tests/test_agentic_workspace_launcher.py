from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_agentic_workspace.py"
GENERATOR_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate" / "generate_command_packages.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("run_agentic_workspace", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load launcher from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_generator_module():
    spec = importlib.util.spec_from_file_location("generate_command_packages", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load generator from {GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _minimal_repo(root: Path) -> None:
    _write(root / ".gitattributes", "*.json text eol=lf\n*.py text eol=lf\n*.toml text eol=lf\nuv.lock text eol=lf\n")
    _write(root / "pyproject.toml", '[project]\nname = "fixture"\n')
    _write(root / "uv.lock", "# lock\n")
    _write(root / "scripts" / "generate" / "generate_command_packages.py", "print('generate')\n")
    _write(root / "scripts" / "generate" / "workspace_command_generation.py", "VALUE = 1\n")
    _write(root / "src" / "agentic_workspace" / "runtime.py", "VALUE = 1\n")
    _write(
        root / "src" / "agentic_workspace" / "contracts" / "command_package_ir.json",
        json.dumps(
            {
                "packages": [
                    {
                        "id": "root-workspace",
                        "operation_contract_root": "src/agentic_workspace/contracts",
                        "commands": [],
                        "targets": [{"generated_root": "generated/workspace/python"}],
                    }
                ]
            }
        )
        + "\n",
    )
    _write(root / "generated" / "workspace" / "python" / "cli.py", "def main(argv=None):\n    return 0\n")
    _write(root / "generated" / "workspace" / "typescript" / "package.json", '{"version":"0.39.2"}\n')


def _source_manifest(module, root: Path, *, paths: list[str] | None = None) -> dict[str, object]:
    if paths is None:
        return module.source_cli_fingerprint_manifest(repo_root=root, owner="workspace")
    content_identity = module.compute_generated_cli_fingerprint(repo_root=root)
    return {
        "schema": module.CACHE_SCHEMA,
        "kind": "generated-cli-owner-source-manifest/v1",
        "owner": "workspace",
        "file_paths": paths,
        "algorithm": "sha256",
        "fingerprint": content_identity["fingerprint"],
    }


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def test_launcher_skips_generation_when_fingerprint_cache_matches(tmp_path: Path) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    cache_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "generated-cli-fingerprint.json"
    fingerprint = module.compute_generated_cli_fingerprint(repo_root=tmp_path)
    module._write_cached_fingerprint(fingerprint, cache_path=cache_path)
    assert not cache_path.with_suffix(".tmp").exists()

    def fail_if_called(repo_root: Path, generator_script: Path) -> None:
        raise AssertionError(f"unexpected regeneration for {repo_root} via {generator_script}")

    refreshed = module.ensure_generated_cli_current(
        repo_root=tmp_path,
        cache_path=cache_path,
        generator_script=tmp_path / "scripts" / "generate" / "generate_command_packages.py",
        run_generator=fail_if_called,
    )

    assert refreshed is False


def test_generated_cli_fingerprint_is_stable_across_text_line_endings(tmp_path: Path) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    source = tmp_path / "scripts" / "generate" / "workspace_command_generation.py"
    source.write_bytes(b"VALUE = 1\n")
    unix_fingerprint = module.compute_generated_cli_fingerprint(repo_root=tmp_path)["fingerprint"]

    source.write_bytes(b"VALUE = 1\r\n")

    assert module.compute_generated_cli_fingerprint(repo_root=tmp_path)["fingerprint"] == unix_fingerprint


def test_launcher_does_not_refresh_generated_cli_for_start(monkeypatch) -> None:
    module = _load_module()

    def fail_refresh() -> bool:
        raise AssertionError("start must not refresh generated CLI before first-contact routing")

    observed: list[list[str]] = []
    monkeypatch.setattr(module, "ensure_generated_cli_current", fail_refresh)
    monkeypatch.setattr(module, "_dispatch_to_source_cli", lambda argv: observed.append(list(argv)) or 0)

    assert module.main(["start", "--target", ".", "--format", "json"]) == 0
    assert observed == [["start", "--target", ".", "--format", "json"]]


def test_launcher_maps_codex_thread_to_portable_session_identity_without_output_leak(monkeypatch, capsys) -> None:
    module = _load_module()
    monkeypatch.setenv(module.CODEX_SESSION_IDENTITY_ENV, "private-codex-thread")
    monkeypatch.delenv(module.AW_SESSION_IDENTITY_ENV, raising=False)
    monkeypatch.setattr(module, "_admit_runtime_identity", lambda: True)
    monkeypatch.setattr(
        module,
        "_dispatch_to_source_cli",
        lambda _argv: 0 if os.environ[module.AW_SESSION_IDENTITY_ENV] == "private-codex-thread" else 1,
    )

    assert module.main(["start", "--target", ".", "--format", "json"]) == 0
    captured = capsys.readouterr()
    assert "private-codex-thread" not in captured.out
    assert "private-codex-thread" not in captured.err


def test_launcher_preserves_existing_portable_session_identity(monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setenv(module.CODEX_SESSION_IDENTITY_ENV, "codex-thread")
    monkeypatch.setenv(module.AW_SESSION_IDENTITY_ENV, "portable-session")
    monkeypatch.setattr(module, "_admit_runtime_identity", lambda: True)
    monkeypatch.setattr(
        module,
        "_dispatch_to_source_cli",
        lambda _argv: 0 if os.environ[module.AW_SESSION_IDENTITY_ENV] == "portable-session" else 1,
    )

    assert module.main(["start", "--target", ".", "--format", "json"]) == 0


def test_launcher_leaves_session_identity_unset_outside_codex(monkeypatch) -> None:
    module = _load_module()
    monkeypatch.delenv(module.CODEX_SESSION_IDENTITY_ENV, raising=False)
    monkeypatch.delenv(module.AW_SESSION_IDENTITY_ENV, raising=False)
    monkeypatch.setattr(module, "_admit_runtime_identity", lambda: True)
    monkeypatch.setattr(
        module,
        "_dispatch_to_source_cli",
        lambda _argv: 0 if module.AW_SESSION_IDENTITY_ENV not in os.environ else 1,
    )

    assert module.main(["start", "--target", ".", "--format", "json"]) == 0


def test_codex_identity_vocabulary_stays_outside_portable_aw_surfaces() -> None:
    module = _load_module()
    repo_root = SCRIPT_PATH.parents[1]
    portable_roots = [repo_root / "src", repo_root / "packages", repo_root / "generated"]
    text_suffixes = {".json", ".md", ".mjs", ".py", ".toml", ".ts"}

    leaked_paths = []
    for root in portable_roots:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in text_suffixes:
                if module.CODEX_SESSION_IDENTITY_ENV in path.read_text(encoding="utf-8-sig"):
                    leaked_paths.append(path.relative_to(repo_root).as_posix())

    assert leaked_paths == []


def test_runtime_identity_rejects_editable_distribution_from_sibling_checkout(tmp_path: Path) -> None:
    module = _load_module()
    target = tmp_path / "target"
    sibling = tmp_path / "sibling"
    target.mkdir()
    sibling.mkdir()

    class Distribution:
        def read_text(self, name: str) -> str | None:
            assert name == "direct_url.json"
            return json.dumps({"url": sibling.as_uri(), "dir_info": {"editable": True}})

    def lookup(name: str):
        if name == "agentic-workspace":
            return Distribution()
        raise module.importlib.metadata.PackageNotFoundError(name)

    identity = module.runtime_identity_admission(repo_root=target, distribution_lookup=lookup)

    assert identity["status"] == "mismatch"
    assert identity["mismatches"] == [
        {
            "distribution": "agentic-workspace",
            "origin": sibling.resolve().as_posix(),
            "expected": target.resolve().as_posix(),
        }
    ]


def test_runtime_identity_accepts_matching_active_editable_distribution(tmp_path: Path) -> None:
    module = _load_module()
    target = tmp_path / "target"
    target.mkdir()

    class Distribution:
        def read_text(self, _name: str) -> str:
            return json.dumps({"url": target.as_uri(), "dir_info": {"editable": True}})

    def lookup(name: str):
        if name == "agentic-workspace":
            return Distribution()
        raise module.importlib.metadata.PackageNotFoundError(name)

    identity = module.runtime_identity_admission(repo_root=target, distribution_lookup=lookup)

    assert identity["status"] == "matched"
    assert identity["mismatches"] == []


def test_runtime_identity_rejection_precedes_refresh_and_dispatch(monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "_admit_runtime_identity", lambda: False)
    monkeypatch.setattr(module, "ensure_generated_cli_current", lambda: pytest.fail("refresh ran before identity admission"))
    monkeypatch.setattr(module, "_dispatch_to_source_cli", lambda _argv: pytest.fail("dispatch ran after identity rejection"))

    assert module.main(["summary", "--target", ".", "--format", "json"]) == 2


def test_active_no_sync_runtime_identity_is_stable_across_two_checkouts(tmp_path: Path) -> None:
    checkout_a = tmp_path / "checkout-a"
    checkout_b = tmp_path / "checkout-b"
    fake_site = tmp_path / "active-site"
    for checkout in (checkout_a, checkout_b):
        for relative in (".", "packages/memory", "packages/planning", "packages/verification"):
            (checkout / relative).mkdir(parents=True, exist_ok=True)
    (checkout_b / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(SCRIPT_PATH, checkout_b / "scripts" / "run_agentic_workspace.py")
    _write(checkout_b / "pyproject.toml", '[project]\nname = "runtime-identity-fixture"\nversion = "0.0.0"\n')
    _write(checkout_b / "src/agentic_workspace/__init__.py", "")
    _write(
        checkout_b / "src/agentic_workspace/cli.py",
        "import os\n"
        "if os.environ.get('AW_TEST_MISSING_RUNTIME_DEPENDENCY') == '1':\n"
        "    import aw_test_dependency_that_is_not_installed\n"
        "def main(argv=None):\n    print('dispatched:' + str((argv or [''])[0]))\n    return 0\n",
    )

    distributions = {
        "agentic-workspace": ".",
        "agentic-workspace-memory": "packages/memory",
        "agentic-workspace-planning": "packages/planning",
        "agentic-workspace-verification": "packages/verification",
    }

    def bind_active_runtime(checkout: Path) -> None:
        for name, relative in distributions.items():
            dist_info = fake_site / f"{name.replace('-', '_')}-0.dist-info"
            _write(dist_info / "METADATA", f"Name: {name}\nVersion: 0\n")
            _write(
                dist_info / "direct_url.json",
                json.dumps({"url": (checkout / relative).resolve().as_uri(), "dir_info": {"editable": True}}),
            )

    def snapshot() -> dict[str, bytes]:
        roots = {"a": checkout_a, "b": checkout_b, "site": fake_site}
        return {
            f"{label}/{path.relative_to(root).as_posix()}": path.read_bytes()
            for label, root in roots.items()
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }

    environment = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join((str(fake_site), str(checkout_b / "src"))),
        "PYTHONDONTWRITEBYTECODE": "1",
        "AW_SKIP_GENERATED_CLI_REFRESH": "1",
    }

    def invoke(command: str, *, extra_environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "uv",
                "run",
                "--active",
                "--no-sync",
                "python",
                "scripts/run_agentic_workspace.py",
                command,
                "--target",
                ".",
                "--format",
                "json",
            ],
            cwd=checkout_b,
            env={**environment, **(extra_environment or {})},
            capture_output=True,
            text=True,
            check=False,
        )

    bind_active_runtime(checkout_a)
    mismatch_before = snapshot()
    for command in ("start", "summary", "report", "doctor"):
        result = invoke(command)
        assert result.returncode == 2
        assert "refused a runtime from another checkout before command effects" in result.stderr
    assert snapshot() == mismatch_before

    bind_active_runtime(checkout_b)
    missing_dependency = invoke("start", extra_environment={"AW_TEST_MISSING_RUNTIME_DEPENDENCY": "1"})
    assert missing_dependency.returncode == 2
    recovery = json.loads(missing_dependency.stdout)
    assert recovery["reason_code"] == "unsynchronized-source-runtime"
    assert recovery["missing_module"] == "aw_test_dependency_that_is_not_installed"
    assert recovery["recovery_argv"] == ["uv", "sync", "--frozen", "--project", checkout_b.as_posix()]
    assert recovery["recovery_command"].startswith("uv sync --frozen --project ")

    matching_before = snapshot()
    for command in ("start", "summary", "report", "doctor"):
        result = invoke(command)
        assert result.returncode == 0, result.stderr
        assert f"dispatched:{command}" in result.stdout
    assert snapshot() == matching_before


def test_repo_configured_active_invocation_forbids_dependency_sync() -> None:
    config = (SCRIPT_PATH.parents[1] / ".agentic-workspace" / "config.toml").read_text(encoding="utf-8")

    assert 'cli_invoke = "uv run --frozen --active --no-sync python scripts/run_agentic_workspace.py"' in config


def test_launcher_force_refresh_still_applies_to_start(monkeypatch) -> None:
    module = _load_module()
    calls: list[str] = []
    monkeypatch.setenv("AW_FORCE_GENERATED_CLI_REFRESH", "1")
    monkeypatch.setattr(module, "ensure_generated_cli_current", lambda: calls.append("refresh") or False)
    monkeypatch.setattr(module, "_dispatch_to_source_cli", lambda _argv: 0)

    assert module.main(["start", "--target", ".", "--format", "json"]) == 0
    assert calls == ["refresh"]


def test_launcher_skips_content_hash_when_manifest_cache_is_fresh(tmp_path: Path) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "fixture@example.invalid")
    _git(tmp_path, "config", "user.name", "Fixture")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "fixture")
    cache_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "generated-cli-fingerprint.json"
    fingerprint = module.compute_generated_cli_fingerprint(repo_root=tmp_path)
    module._write_cached_fingerprint(fingerprint, cache_path=cache_path, repo_root=tmp_path)

    def fail_content_hash(repo_root: Path) -> dict[str, object]:
        raise AssertionError(f"unexpected content hash for fresh cache in {repo_root}")

    def fail_if_called(repo_root: Path, generator_script: Path) -> None:
        raise AssertionError(f"unexpected regeneration for {repo_root} via {generator_script}")

    module.compute_generated_cli_fingerprint = fail_content_hash
    refreshed = module.ensure_generated_cli_current(
        repo_root=tmp_path,
        cache_path=cache_path,
        generator_script=tmp_path / "scripts" / "generate" / "generate_command_packages.py",
        run_generator=fail_if_called,
    )

    assert refreshed is False


def test_semantic_admission_populates_local_git_fast_path(tmp_path: Path) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    manifest = module.source_cli_fingerprint_manifest(repo_root=tmp_path, owner="workspace")
    source_manifest = tmp_path / "generated/workspace/.agentic-workspace-cli-fingerprint.json"
    source_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "fixture@example.invalid")
    _git(tmp_path, "config", "user.name", "Fixture")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "fixture")
    cache_path = tmp_path / ".agentic-workspace/local/cache/generated-cli-fingerprint.json"

    assert not module.ensure_generated_cli_current(repo_root=tmp_path, cache_path=cache_path)
    assert json.loads(cache_path.read_text(encoding="utf-8"))["local_git_index_identity"]

    module.compute_generated_cli_fingerprint = lambda **_: (_ for _ in ()).throw(AssertionError("content hash used"))
    module._fingerprint_payload = lambda **_: (_ for _ in ()).throw(AssertionError("owner content hash used"))
    assert not module.ensure_generated_cli_current(repo_root=tmp_path, cache_path=cache_path)


def test_launcher_uses_source_owned_manifest_on_cold_clean_worktree(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    source_manifest = tmp_path / "generated" / "workspace" / ".agentic-workspace-cli-fingerprint.json"
    manifest = _source_manifest(module, tmp_path)
    source_manifest.write_text(json.dumps(manifest), encoding="utf-8")

    refreshed = module.ensure_generated_cli_current(
        repo_root=tmp_path,
        cache_path=tmp_path / ".agentic-workspace" / "local" / "cache" / "missing.json",
        generator_script=tmp_path / "scripts" / "generate" / "generate_command_packages.py",
        run_generator=lambda *_: (_ for _ in ()).throw(AssertionError("unexpected regeneration")),
    )

    assert refreshed is False


def test_launcher_uses_source_manifest_with_unrelated_dirty_worktree(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    source_manifest = tmp_path / "generated" / "workspace" / ".agentic-workspace-cli-fingerprint.json"
    manifest = _source_manifest(module, tmp_path)
    source_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    refreshed = module.ensure_generated_cli_current(
        repo_root=tmp_path,
        cache_path=tmp_path / ".agentic-workspace" / "local" / "cache" / "missing.json",
        generator_script=tmp_path / "scripts" / "generate" / "generate_command_packages.py",
        run_generator=lambda *_: (_ for _ in ()).throw(AssertionError("unexpected regeneration")),
    )

    assert refreshed is False


def test_launcher_accepts_semantically_current_manifest_when_input_witness_is_dirty(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    source_manifest = tmp_path / "generated" / "workspace" / ".agentic-workspace-cli-fingerprint.json"
    manifest = _source_manifest(module, tmp_path)
    source_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(module, "_git_index_entries", lambda **_: {path: "current" for path in manifest["file_paths"]})
    monkeypatch.setattr(module, "_git_input_paths_are_unmodified", lambda **_: False)
    calls: list[Path] = []
    original = module.compute_generated_cli_fingerprint

    def count_content_hash(*, repo_root: Path) -> dict[str, object]:
        calls.append(repo_root)
        return original(repo_root=repo_root)

    module.compute_generated_cli_fingerprint = count_content_hash
    assert not module.ensure_generated_cli_current(
        repo_root=tmp_path,
        cache_path=tmp_path / ".agentic-workspace" / "local" / "cache" / "missing.json",
        generator_script=tmp_path / "scripts" / "generate" / "generate_command_packages.py",
        run_generator=lambda *_: (_ for _ in ()).throw(AssertionError("unexpected regeneration")),
    )
    assert calls == [tmp_path]


def test_source_manifest_ignores_unrelated_dirtiness_but_rejects_input_changes(tmp_path: Path) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "fixture@example.invalid")
    _git(tmp_path, "config", "user.name", "Fixture")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "fixture")
    source_manifest = tmp_path / "generated" / "workspace" / ".agentic-workspace-cli-fingerprint.json"
    source_manifest.write_text(json.dumps(module.source_cli_fingerprint_manifest(repo_root=tmp_path, owner="workspace")), encoding="utf-8")

    _write(tmp_path / "README.md", "unrelated local note\n")
    assert module._source_manifest_is_trustworthy(repo_root=tmp_path)

    _write(tmp_path / "src" / "agentic_workspace" / "runtime.py", "VALUE = 2\n")
    assert module._source_manifest_is_trustworthy(repo_root=tmp_path)

    _write(tmp_path / "scripts" / "generate" / "workspace_command_generation.py", "VALUE = 2\n")
    assert not module._source_manifest_is_trustworthy(repo_root=tmp_path)


def test_source_manifest_survives_generate_then_stage_and_commit(tmp_path: Path) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "fixture@example.invalid")
    _git(tmp_path, "config", "user.name", "Fixture")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "fixture")

    source = tmp_path / "scripts" / "generate" / "workspace_command_generation.py"
    source_manifest = tmp_path / "generated" / "workspace" / ".agentic-workspace-cli-fingerprint.json"
    _write(source, "VALUE = 2\n")
    manifest = module.source_cli_fingerprint_manifest(repo_root=tmp_path, owner="workspace")
    source_manifest.write_text(json.dumps(manifest), encoding="utf-8")

    indexed_before_staging = module._git_index_entries(repo_root=tmp_path, paths=manifest["file_paths"])
    assert indexed_before_staging is not None
    assert indexed_before_staging[source.relative_to(tmp_path).as_posix()]
    assert "git_index_entries" not in manifest
    assert "git_index_identity" not in manifest

    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "regenerate after source edit")

    assert module._source_manifest_is_trustworthy(repo_root=tmp_path)
    assert module.source_cli_fingerprint_manifest(repo_root=tmp_path, owner="workspace") == manifest


def test_source_manifest_uses_same_semantic_identity_without_git(tmp_path: Path) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    source_manifest = tmp_path / "generated" / "workspace" / ".agentic-workspace-cli-fingerprint.json"
    manifest = module.source_cli_fingerprint_manifest(repo_root=tmp_path, owner="workspace")
    assert "git_index_entries" not in manifest
    assert "git_index_identity" not in manifest
    assert manifest["identity_role"] == "owner-scoped-semantic-content"
    source_manifest.write_text(json.dumps(manifest), encoding="utf-8")

    assert module._source_manifest_is_trustworthy(repo_root=tmp_path)

    _write(tmp_path / "scripts" / "generate" / "workspace_command_generation.py", "VALUE = 2\n")
    assert not module._source_manifest_is_trustworthy(repo_root=tmp_path)


def test_source_manifest_rejects_branch_carried_git_witness(tmp_path: Path) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    manifest = module.source_cli_fingerprint_manifest(repo_root=tmp_path, owner="workspace")
    manifest["git_index_entries"] = {}
    source_manifest = tmp_path / "generated" / "workspace" / ".agentic-workspace-cli-fingerprint.json"
    source_manifest.write_text(json.dumps(manifest), encoding="utf-8")

    assert module.source_cli_fingerprint_manifest_status(repo_root=tmp_path) == {
        "status": "invalid",
        "reason": "workspace:branch-carried-git-witness",
        "auxiliary_witness": "not-evaluated",
    }


def test_source_manifest_rejects_orphaned_owner_receipt(tmp_path: Path) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    manifest = module.source_cli_fingerprint_manifest(repo_root=tmp_path, owner="workspace")
    _write(tmp_path / "generated/workspace/.agentic-workspace-cli-fingerprint.json", json.dumps(manifest))
    _write(tmp_path / "generated/orphan/.agentic-workspace-cli-fingerprint.json", json.dumps({"owner": "orphan"}))

    assert module.source_cli_fingerprint_manifest_status(repo_root=tmp_path)["reason"] == "owner-manifest-set-drift"


def test_manifest_status_filter_is_bounded_and_rejects_relevant_records(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    calls: list[list[str]] = []

    def status(command, **_kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout=" M README.md\0")

    monkeypatch.setattr(module.subprocess, "run", status)
    assert module._git_input_paths_are_unmodified(repo_root=tmp_path, paths=["src/example.py"])
    assert calls == [["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"]]

    for record in ("M  src/example.py\0", " M src/example.py\0", "?? src/example.py\0", "D  src/example.py\0"):
        monkeypatch.setattr(module.subprocess, "run", lambda *_args, record=record, **_kwargs: SimpleNamespace(returncode=0, stdout=record))
        assert not module._git_input_paths_are_unmodified(repo_root=tmp_path, paths=["src/example.py"])


def test_manifest_status_filter_rejects_renamed_copied_or_malformed_relevant_records(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    for record in ("R  renamed.py\0src/example.py\0", "R  src/example.py\0renamed.py\0", "C  copied.py\0src/example.py\0", "bad\0"):
        monkeypatch.setattr(module.subprocess, "run", lambda *_args, record=record, **_kwargs: SimpleNamespace(returncode=0, stdout=record))
        assert not module._git_input_paths_are_unmodified(repo_root=tmp_path, paths=["src/example.py"])


def test_manifest_status_filter_fails_closed_when_git_fails(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout=""))
    assert not module._git_input_paths_are_unmodified(repo_root=tmp_path, paths=["src/example.py"])


def test_launcher_accepts_semantic_match_with_derived_git_witness(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    source_manifest = tmp_path / "generated" / "workspace" / ".agentic-workspace-cli-fingerprint.json"
    manifest = _source_manifest(module, tmp_path)
    source_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(module, "_git_input_paths_are_unmodified", lambda **_: True)
    monkeypatch.setattr(module, "_git_index_entries", lambda **_: {path: "current" for path in manifest["file_paths"]})
    original = module.compute_generated_cli_fingerprint
    calls: list[Path] = []

    def count_content_hash(*, repo_root: Path) -> dict[str, object]:
        calls.append(repo_root)
        return original(repo_root=repo_root)

    module.compute_generated_cli_fingerprint = count_content_hash
    assert not module.ensure_generated_cli_current(
        repo_root=tmp_path,
        cache_path=tmp_path / ".agentic-workspace" / "local" / "cache" / "missing.json",
        generator_script=tmp_path / "scripts" / "generate" / "generate_command_packages.py",
        run_generator=lambda *_: (_ for _ in ()).throw(AssertionError("unexpected regeneration")),
    )
    assert calls == [tmp_path]


@pytest.mark.parametrize("publication_shape", ["ordinary-maintainer-2507", "coordinated-release-2501"])
def test_source_manifest_publication_orders_converge_on_committed_head(tmp_path: Path, publication_shape: str) -> None:
    module = _load_module()
    generator = _load_generator_module()
    fingerprints: dict[str, str] = {}

    for publication_order in ("generate-before-stage", "stage-before-generation"):
        repo = tmp_path / publication_order
        _minimal_repo(repo)
        _git(repo, "init")
        _git(repo, "config", "user.email", "fixture@example.invalid")
        _git(repo, "config", "user.name", "Fixture")
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "initial")

        if publication_shape == "ordinary-maintainer-2507":
            _write(repo / "scripts" / "generate" / "workspace_command_generation.py", "VALUE = 2\n")
        else:
            # Model coordinated_release.py prepare, its generated package
            # version mutation, and the subsequent `uv lock` update.
            _write(repo / "pyproject.toml", '[project]\nname = "fixture"\nversion = "0.39.3"\n')
            _write(repo / "generated" / "workspace" / "typescript" / "package.json", '{"version":"0.39.3"}\n')
            _write(repo / "uv.lock", "# coordinated release lock for 0.39.3\n")

        if publication_order == "stage-before-generation":
            _git(repo, "add", ".")
        source_manifest = repo / "generated" / "workspace" / ".agentic-workspace-cli-fingerprint.json"
        manifest = module.source_cli_fingerprint_manifest(repo_root=repo, owner="workspace")
        source_manifest.write_text(json.dumps(manifest), encoding="utf-8")
        fingerprints[publication_order] = str(manifest["fingerprint"])

        before_staging = module.source_cli_fingerprint_manifest_status(repo_root=repo)
        assert before_staging["status"] == "current"
        _git(repo, "add", ".")
        after_staging = module.source_cli_fingerprint_manifest_status(repo_root=repo)
        assert after_staging["status"] == "current"
        _git(repo, "commit", "-m", f"publish {publication_shape}")

        canonical_check = generator._source_cli_fingerprint_manifest_status(repo_root=repo, launcher=module)
        assert canonical_check == {
            "status": "current",
            "reason": "owner-manifests-current",
            "auxiliary_witness": "derived-clean-index",
        }
        assert not module.ensure_generated_cli_current(
            repo_root=repo,
            cache_path=repo / ".agentic-workspace" / "local" / "cache" / "missing.json",
            generator_script=repo / "scripts" / "generate" / "generate_command_packages.py",
            run_generator=lambda *_: (_ for _ in ()).throw(AssertionError("committed publication head regenerated")),
        )

    assert fingerprints["generate-before-stage"] == fingerprints["stage-before-generation"]


def test_source_manifest_rejects_semantic_drift_even_when_git_witness_matches(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    manifest = _source_manifest(module, tmp_path)
    source_manifest = tmp_path / "generated" / "workspace" / ".agentic-workspace-cli-fingerprint.json"
    source_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    _write(tmp_path / "scripts" / "generate" / "workspace_command_generation.py", "VALUE = 2\n")
    monkeypatch.setattr(module, "_git_index_entries", lambda **_: {path: "current" for path in manifest["file_paths"]})
    monkeypatch.setattr(module, "_git_input_paths_are_unmodified", lambda **_: False)

    assert module.source_cli_fingerprint_manifest_status(repo_root=tmp_path) == {
        "status": "stale",
        "reason": "workspace:semantic-content-drift",
        "auxiliary_witness": "dirty-inputs",
    }


def test_canonical_fingerprint_regeneration_clears_stale_source_manifest(tmp_path: Path) -> None:
    module = _load_module()
    generator = _load_generator_module()
    _minimal_repo(tmp_path)
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "fixture@example.invalid")
    _git(tmp_path, "config", "user.name", "Fixture")

    _git(tmp_path, "add", ".")
    generator._write_source_cli_fingerprint_manifests(repo_root=tmp_path, launcher=module)
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "publish generated fingerprint")
    fingerprint_path = tmp_path / "generated" / "workspace" / ".agentic-workspace-cli-fingerprint.json"
    prior_fingerprint = fingerprint_path.read_bytes()

    _write(tmp_path / "scripts" / "generate" / "workspace_command_generation.py", "VALUE = 2\n")
    stale = generator._source_cli_fingerprint_manifest_status(repo_root=tmp_path, launcher=module)
    assert stale == {
        "status": "stale",
        "reason": "workspace:semantic-content-drift",
        "auxiliary_witness": "dirty-inputs",
    }

    generator._write_source_cli_fingerprint_manifests(repo_root=tmp_path, launcher=module)
    regenerated_fingerprint = fingerprint_path.read_bytes()
    assert regenerated_fingerprint != prior_fingerprint
    assert generator._source_cli_fingerprint_manifest_status(repo_root=tmp_path, launcher=module)["status"] == "current"

    generator._write_source_cli_fingerprint_manifests(repo_root=tmp_path, launcher=module)
    assert fingerprint_path.read_bytes() == regenerated_fingerprint


def test_launcher_rejects_clean_source_manifest_missing_new_input(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    source_manifest = tmp_path / "generated" / "workspace" / ".agentic-workspace-cli-fingerprint.json"
    manifest = _source_manifest(module, tmp_path, paths=["pyproject.toml"])
    source_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(module, "_git_input_paths_are_unmodified", lambda **_: True)
    monkeypatch.setattr(module, "_git_index_entries", lambda **_: {path: "current" for path in manifest["file_paths"]})
    original = module.compute_generated_cli_fingerprint
    calls: list[Path] = []

    def count_content_hash(*, repo_root: Path) -> dict[str, object]:
        calls.append(repo_root)
        return original(repo_root=repo_root)

    module.compute_generated_cli_fingerprint = count_content_hash
    assert module.ensure_generated_cli_current(
        repo_root=tmp_path,
        cache_path=tmp_path / ".agentic-workspace" / "local" / "cache" / "missing.json",
        generator_script=tmp_path / "scripts" / "generate" / "generate_command_packages.py",
        run_generator=lambda *_: None,
    )
    assert calls == [tmp_path, tmp_path]


def test_launcher_regenerates_and_recaches_when_fingerprint_changes(tmp_path: Path) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    cache_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "generated-cli-fingerprint.json"
    module._write_cached_fingerprint(
        {
            "schema": module.CACHE_SCHEMA,
            "algorithm": "sha256",
            "fingerprint": "stale",
            "file_count": 0,
        },
        cache_path=cache_path,
    )
    calls: list[tuple[Path, Path]] = []

    def regenerate(repo_root: Path, generator_script: Path) -> None:
        calls.append((repo_root, generator_script))
        _write(repo_root / "generated" / "workspace" / "python" / "cli.py", "def main(argv=None):\n    return 1\n")

    refreshed = module.ensure_generated_cli_current(
        repo_root=tmp_path,
        cache_path=cache_path,
        generator_script=tmp_path / "scripts" / "generate" / "generate_command_packages.py",
        run_generator=regenerate,
    )

    assert refreshed is True
    assert calls == [(tmp_path, tmp_path / "scripts" / "generate" / "generate_command_packages.py")]
    assert (
        module._read_cached_fingerprint(cache_path=cache_path)
        == module.compute_generated_cli_fingerprint(repo_root=tmp_path)["fingerprint"]
    )


def test_launcher_retries_transient_permission_error_when_writing_fingerprint(tmp_path: Path) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    cache_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "generated-cli-fingerprint.json"
    fingerprint = module.compute_generated_cli_fingerprint(repo_root=tmp_path)
    calls: list[tuple[Path, Path]] = []
    sleeps: list[float] = []

    def flaky_replace(source: Path, target: Path) -> object:
        calls.append((source, target))
        if len(calls) == 1:
            raise PermissionError("target cache was briefly locked")
        return source.replace(target)

    module._write_cached_fingerprint(
        fingerprint,
        cache_path=cache_path,
        replace_path=flaky_replace,
        sleep=sleeps.append,
    )

    assert len(calls) == 2
    assert sleeps == [0.05]
    assert module._read_cached_fingerprint(cache_path=cache_path) == fingerprint["fingerprint"]
    assert not list(cache_path.parent.glob(f"{cache_path.name}.*.tmp"))
