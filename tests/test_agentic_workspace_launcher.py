from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_agentic_workspace.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("run_agentic_workspace", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load launcher from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _minimal_repo(root: Path) -> None:
    _write(root / "pyproject.toml", '[project]\nname = "fixture"\n')
    _write(root / "uv.lock", "# lock\n")
    _write(root / "scripts" / "generate" / "generate_command_packages.py", "print('generate')\n")
    _write(root / "src" / "agentic_workspace" / "runtime.py", "VALUE = 1\n")
    _write(root / "src" / "agentic_workspace" / "contracts" / "command_package_ir.json", "{}\n")
    _write(root / "generated" / "workspace" / "python" / "cli.py", "def main(argv=None):\n    return 0\n")


def _source_manifest(module, root: Path, *, paths: list[str] | None = None, identity: str = "current-index") -> dict[str, object]:
    paths = paths or [module._repo_relative(path, repo_root=root) for path in module._fingerprint_files(repo_root=root)]
    return {
        "schema": module.CACHE_SCHEMA,
        "kind": "generated-cli-source-manifest/v1",
        "file_paths": paths,
        "git_index_entries": {path: "100644 current" for path in paths},
        "git_index_identity": identity,
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


def test_launcher_skips_content_hash_when_manifest_cache_is_fresh(tmp_path: Path) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    cache_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "generated-cli-fingerprint.json"
    fingerprint = module.compute_generated_cli_fingerprint(repo_root=tmp_path)
    module._write_cached_fingerprint(fingerprint, cache_path=cache_path)

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


def test_launcher_uses_source_owned_manifest_on_cold_clean_worktree(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    source_manifest = tmp_path / "generated" / ".agentic-workspace-cli-fingerprint.json"
    manifest = _source_manifest(module, tmp_path)
    source_manifest.write_text(json.dumps(manifest), encoding="utf-8")

    monkeypatch.setattr(module, "_git_input_paths_are_unmodified", lambda **_: True)
    monkeypatch.setattr(module, "_git_index_entries", lambda **_: manifest["git_index_entries"])
    monkeypatch.setattr(module, "_git_index_identity", lambda **_: "current-index")

    def fail_content_hash(repo_root: Path) -> dict[str, object]:
        raise AssertionError(f"unexpected content hash for clean source manifest in {repo_root}")

    module.compute_generated_cli_fingerprint = fail_content_hash
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
    source_manifest = tmp_path / "generated" / ".agentic-workspace-cli-fingerprint.json"
    manifest = _source_manifest(module, tmp_path)
    source_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(module, "_git_input_paths_are_unmodified", lambda **_: True)
    monkeypatch.setattr(module, "_git_index_entries", lambda **_: manifest["git_index_entries"])
    monkeypatch.setattr(module, "_git_index_identity", lambda **_: "current-index")

    def fail_content_hash(*, repo_root: Path) -> dict[str, object]:
        raise AssertionError(f"unrelated dirtiness must not hash inputs in {repo_root}")

    module.compute_generated_cli_fingerprint = fail_content_hash
    refreshed = module.ensure_generated_cli_current(
        repo_root=tmp_path,
        cache_path=tmp_path / ".agentic-workspace" / "local" / "cache" / "missing.json",
        generator_script=tmp_path / "scripts" / "generate" / "generate_command_packages.py",
        run_generator=lambda *_: (_ for _ in ()).throw(AssertionError("unexpected regeneration")),
    )

    assert refreshed is False


def test_launcher_hashes_when_a_manifest_input_is_dirty(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    source_manifest = tmp_path / "generated" / ".agentic-workspace-cli-fingerprint.json"
    manifest = _source_manifest(module, tmp_path)
    source_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(module, "_git_input_paths_are_unmodified", lambda **_: False)
    calls: list[Path] = []
    original = module.compute_generated_cli_fingerprint

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


def test_source_manifest_ignores_unrelated_dirtiness_but_rejects_input_changes(tmp_path: Path) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "fixture@example.invalid")
    _git(tmp_path, "config", "user.name", "Fixture")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "fixture")
    source_manifest = tmp_path / "generated" / ".agentic-workspace-cli-fingerprint.json"
    source_manifest.write_text(json.dumps(module.source_cli_fingerprint_manifest(repo_root=tmp_path)), encoding="utf-8")

    _write(tmp_path / "README.md", "unrelated local note\n")
    assert module._source_manifest_is_trustworthy(repo_root=tmp_path)

    _write(tmp_path / "src" / "agentic_workspace" / "runtime.py", "VALUE = 2\n")
    assert not module._source_manifest_is_trustworthy(repo_root=tmp_path)


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


def test_manifest_status_filter_rejects_renamed_or_malformed_relevant_records(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    for record in ("R  renamed.py\0src/example.py\0", "R  src/example.py\0renamed.py\0", "bad\0"):
        monkeypatch.setattr(module.subprocess, "run", lambda *_args, record=record, **_kwargs: SimpleNamespace(returncode=0, stdout=record))
        assert not module._git_input_paths_are_unmodified(repo_root=tmp_path, paths=["src/example.py"])


def test_launcher_rejects_clean_but_stale_source_manifest(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    source_manifest = tmp_path / "generated" / ".agentic-workspace-cli-fingerprint.json"
    manifest = _source_manifest(module, tmp_path, identity="stale-index")
    source_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(module, "_git_input_paths_are_unmodified", lambda **_: True)
    monkeypatch.setattr(module, "_git_index_entries", lambda **_: manifest["git_index_entries"])
    monkeypatch.setattr(module, "_git_index_identity", lambda **_: "current-index")
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


def test_launcher_rejects_clean_source_manifest_missing_new_input(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _minimal_repo(tmp_path)
    source_manifest = tmp_path / "generated" / ".agentic-workspace-cli-fingerprint.json"
    manifest = _source_manifest(module, tmp_path, paths=["pyproject.toml"])
    source_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(module, "_git_input_paths_are_unmodified", lambda **_: True)
    monkeypatch.setattr(module, "_git_index_entries", lambda **_: manifest["git_index_entries"])
    monkeypatch.setattr(module, "_git_index_identity", lambda **_: "current-index")
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
