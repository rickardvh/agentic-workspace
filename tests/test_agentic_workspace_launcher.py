from __future__ import annotations

import importlib.util
from pathlib import Path

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
