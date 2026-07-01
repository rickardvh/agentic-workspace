"""Run black-box model CLI dogfooding scenarios in disposable fixtures."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from agentic_workspace.config import DEFAULT_AGENT_INSTRUCTIONS_FILE, WORKSPACE_LOCAL_SCRATCH_ROOT_PATH

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUITE = REPO_ROOT / "tools" / "model-cli-harness" / "suites" / "copilot-workflow-smoke.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / WORKSPACE_LOCAL_SCRATCH_ROOT_PATH / "runs"
EPHEMERAL_MUTATION_PATHS = (
    ".git/",
    ".coverage",
    ".mypy_cache/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".tox/",
    ".venv/",
    "__pycache__/",
    "build/",
    "dist/",
    "env/",
    "htmlcov/",
    "node_modules/",
    "site/",
    "uv.lock",
    "venv/",
)
EPHEMERAL_MUTATION_GLOBS = (
    "*.egg-info/*",
    "*.egg-info",
)
HARNESS_SETUP_MUTATION_PATHS = (
    ".agentic-workspace/",
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".cursorrules",
    "pyproject.toml",
    "scripts/run_agentic_workspace.py",
)
SANDBOX_ADAPTER_KIND = "agentic-workspace/model-cli-sandbox-adapter/v1"
LOCAL_AW_WHEEL_PACKAGES = {
    "agentic-workspace": "agentic_workspace",
    "agentic-memory": "agentic_memory",
    "agentic-planning": "agentic_planning",
    "agentic-verification": "agentic_verification",
}
FINAL_ANSWER_PATH_RULE = (
    "Final answer path rule: cite changed files and evidence using repo-relative paths only. "
    "Before writing the final answer, convert any absolute cwd, fixture, run_root, session, prompt-file, "
    "or .agentic-workspace/local/scratch path to a repo-relative path when it is inside the copied repository. "
    "Prefer plain file names such as `README.md`; do not use Markdown file links in the final answer because "
    "some runtimes auto-fill local absolute link targets. If an artifact is outside the copied repository, "
    "describe it by role instead of printing the local absolute path."
)


@dataclass(frozen=True)
class HarnessPaths:
    run_root: Path
    fixture_root: Path
    repo_path: Path
    transcript_path: Path
    share_path: Path


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def _now_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _write_scratch_run_manifest(
    run_root: Path,
    *,
    purpose: str,
    producer: str = "model-cli-harness",
    retention: str = "ephemeral",
    aw_runs_root: Path | None = None,
) -> Path | None:
    aw_runs_root = (aw_runs_root or REPO_ROOT / WORKSPACE_LOCAL_SCRATCH_ROOT_PATH / "runs").resolve()
    try:
        run_root.resolve().relative_to(aw_runs_root)
    except ValueError:
        return None
    manifest = run_root / ".aw-scratch.toml"
    created_at = datetime.now(UTC).isoformat()
    manifest.write_text(
        "\n".join(
            [
                'owner = "agentic-workspace"',
                f"created_at = {_toml_string(created_at)}",
                f"purpose = {_toml_string(purpose)}",
                f"producer = {_toml_string(producer)}",
                f"retention = {_toml_string(retention)}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return manifest


def _replace_placeholders(value: str, *, replacements: dict[str, str]) -> str:
    rendered = value
    for key, replacement in replacements.items():
        rendered = rendered.replace("{" + key + "}", replacement)
    return rendered


def _render_list(values: list[str], *, replacements: dict[str, str]) -> list[str]:
    return [_replace_placeholders(value, replacements=replacements) for value in values]


def _string_list_config(value: Any, *, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be a string list")
    return value


def _adapter_model_args(adapter: dict[str, Any], *, model: str) -> list[str]:
    args = _string_list_config(adapter.get("model_args"), field="adapter.model_args")
    by_model = adapter.get("model_args_by_model", {})
    if by_model is None:
        return args
    if not isinstance(by_model, dict):
        raise ValueError("adapter.model_args_by_model must be an object")
    if model not in by_model:
        return args
    return _string_list_config(by_model[model], field=f"adapter.model_args_by_model.{model}")


def _safe_prompt_stem(value: str) -> str:
    rendered = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-._")
    return (rendered or "prompt")[:80]


def _prompt_transport(
    adapter: dict[str, Any],
    *,
    prompt: str,
    run_root: Path,
    prompt_id: str,
    replacements: dict[str, str],
) -> tuple[str, list[str], dict[str, Any]]:
    config = adapter.get("prompt_transport")
    prompt_length = len(prompt)
    if config is None:
        return (
            prompt,
            [],
            {
                "mode": "inline",
                "prompt_length": prompt_length,
                "threshold_chars": None,
                "prompt_file": "",
            },
        )
    if not isinstance(config, dict):
        raise ValueError("adapter.prompt_transport must be an object")
    threshold = int(config.get("threshold_chars", 8000))
    if prompt_length <= threshold:
        return (
            prompt,
            [],
            {
                "mode": "inline",
                "prompt_length": prompt_length,
                "threshold_chars": threshold,
                "prompt_file": "",
            },
        )

    prompt_dir = run_root / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = (prompt_dir / f"{_safe_prompt_stem(prompt_id)}.txt").resolve()
    prompt_file.write_text(prompt, encoding="utf-8")
    transport_replacements = {
        **replacements,
        "prompt_file": str(prompt_file),
        "prompt_length": str(prompt_length),
    }
    file_prompt_template = str(
        config.get("file_prompt") or "Read the attached prompt file and follow it exactly. Treat it as the complete task prompt."
    )
    inline_prompt = _replace_placeholders(file_prompt_template, replacements=transport_replacements)
    file_args = _render_list(
        _string_list_config(config.get("file_args"), field="adapter.prompt_transport.file_args"),
        replacements=transport_replacements,
    )
    mode = str(config.get("mode") or "file")
    return (
        inline_prompt,
        file_args,
        {
            "mode": mode,
            "prompt_length": prompt_length,
            "inline_prompt_length": len(inline_prompt),
            "threshold_chars": threshold,
            "prompt_file": str(prompt_file),
        },
    )


def _render_command_template(
    values: list[str],
    *,
    replacements: dict[str, str],
    expansion_args: dict[str, list[str]] | None = None,
) -> list[str]:
    expansion_args = expansion_args or {}
    rendered: list[str] = []
    for value in values:
        if value == "{model_args}":
            rendered.extend(_render_list(expansion_args.get("model_args", []), replacements=replacements))
            continue
        if value == "{prompt_transport_args}":
            rendered.extend(_render_list(expansion_args.get("prompt_transport_args", []), replacements=replacements))
            continue
        rendered.append(_replace_placeholders(value, replacements=replacements))
    return rendered


def _adapter_invocation_command(
    adapter: dict[str, Any],
    *,
    adapter_id: str,
    model: str,
    replacements: dict[str, str],
    run_root: Path,
    prompt_id: str,
    command_key: str = "command",
) -> tuple[list[str], dict[str, Any], dict[str, str]]:
    command_template = adapter.get(command_key)
    if command_template is None and command_key != "command":
        command_template = adapter.get("command")
    if not isinstance(command_template, list) or not all(isinstance(item, str) for item in command_template):
        raise ValueError(f"adapter '{adapter_id}' must define {command_key} as a string list")
    prompt = str(replacements.get("prompt", ""))
    model_args = _adapter_model_args(adapter, model=model)
    command_prompt, prompt_transport_args, prompt_transport = _prompt_transport(
        adapter,
        prompt=prompt,
        run_root=run_root,
        prompt_id=prompt_id,
        replacements={**replacements, "model": model},
    )
    command_replacements = {**replacements, "model": model, "prompt": command_prompt}
    if prompt_transport.get("prompt_file"):
        command_replacements["prompt_file"] = str(prompt_transport["prompt_file"])
    if prompt_transport.get("prompt_length") is not None:
        command_replacements["prompt_length"] = str(prompt_transport["prompt_length"])
    command = _render_command_template(
        command_template,
        replacements=command_replacements,
        expansion_args={
            "model_args": model_args,
            "prompt_transport_args": prompt_transport_args,
        },
    )
    return command, prompt_transport, command_replacements


def _render_prompt(template: str, *, replacements: dict[str, str]) -> str:
    return _replace_placeholders(template, replacements=replacements)


def startup_instructions_file(repo_path: Path) -> str:
    startup_file = DEFAULT_AGENT_INSTRUCTIONS_FILE
    for relative_path in (".agentic-workspace/config.toml", ".agentic-workspace/config.local.toml"):
        config_path = repo_path / relative_path
        if not config_path.is_file():
            continue
        try:
            payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            continue
        if relative_path.endswith("config.local.toml") and payload.get("schema_version") != 1:
            continue
        workspace = payload.get("workspace")
        if not isinstance(workspace, dict):
            continue
        configured = workspace.get("agent_instructions_file")
        if isinstance(configured, str) and configured.strip():
            startup_file = configured.strip()
    return startup_file


def _startup_instruction_prompt(*, repo_path: Path, prompt: str) -> str:
    startup_file = startup_instructions_file(repo_path)
    agents_path = repo_path / startup_file
    if not agents_path.exists():
        return prompt
    startup_text = agents_path.read_text(encoding="utf-8").strip()
    if not startup_text:
        return prompt
    compact_startup = " ".join(line.strip() for line in startup_text.splitlines() if line.strip())
    return (
        f"{prompt}\n\n"
        "Harness isolation rule: evaluate this copied repository only. "
        "Use the repository startup instruction below as the startup authority for this fixture. "
        "Do not use caller/source-checkout commands such as `uv run python scripts/run_agentic_workspace.py ...` "
        "unless that exact command appears in the copied repository startup instruction below. "
        "When reporting files, use repo-relative paths only, never local absolute scratch paths. "
        f"{FINAL_ANSWER_PATH_RULE}\n\n"
        f"Repository startup instruction from {startup_file or DEFAULT_AGENT_INSTRUCTIONS_FILE} to apply before non-trivial requests: "
        f"{compact_startup}\n"
    )


def _prompt_variants(scenario: dict[str, Any], *, requested: str | None = None) -> list[dict[str, str]]:
    raw_variants = scenario.get("prompt_variants")
    if raw_variants is None:
        variants = [{"id": "default", "prompt": str(scenario.get("prompt", ""))}]
    else:
        if not isinstance(raw_variants, list) or not raw_variants:
            raise ValueError(f"scenario '{scenario.get('id', '<unknown>')}' prompt_variants must be a non-empty list")
        variants = []
        for index, raw_variant in enumerate(raw_variants):
            if isinstance(raw_variant, str):
                variant_id = "default" if index == 0 else f"variant-{index + 1}"
                variants.append({"id": variant_id, "prompt": raw_variant})
                continue
            if not isinstance(raw_variant, dict):
                raise ValueError(f"scenario '{scenario.get('id', '<unknown>')}' prompt variant entries must be strings or objects")
            variant_id = str(raw_variant.get("id") or f"variant-{index + 1}")
            prompt_text = raw_variant.get("prompt", raw_variant.get("text"))
            if not isinstance(prompt_text, str):
                raise ValueError(f"scenario '{scenario.get('id', '<unknown>')}' prompt variant '{variant_id}' needs text")
            variants.append({"id": variant_id, "prompt": prompt_text})
    if requested is None:
        return variants[:1]
    if requested == "all":
        return variants
    selected = [variant for variant in variants if variant["id"] == requested]
    if not selected:
        available = ", ".join(variant["id"] for variant in variants)
        raise ValueError(f"prompt variant '{requested}' is not defined; available variants: {available}")
    return selected


def _scenario_paths(
    *,
    output_root: Path,
    suite_id: str,
    scenario_id: str,
    adapter_id: str,
    model: str,
    prompt_variant_id: str | None = None,
) -> HarnessPaths:
    safe_model = model.replace("/", "_").replace(":", "_").replace(" ", "_")
    variant_suffix = ""
    if prompt_variant_id and prompt_variant_id != "default":
        safe_variant = prompt_variant_id.replace("/", "_").replace(":", "_").replace(" ", "_")
        variant_suffix = f"-{safe_variant}"
    readable = f"{suite_id}-{scenario_id}{variant_suffix}-{adapter_id}-{safe_model}"
    digest = hashlib.sha1(readable.encode("utf-8")).hexdigest()[:10]
    run_root = output_root / f"{_now_id()}-{scenario_id[:36]}-{adapter_id}-{safe_model[:24]}-{digest}"
    fixture_root = run_root / "fixture"
    repo_path = run_root / "repo"
    transcript_path = run_root / "transcript.jsonl"
    share_path = run_root / "session.md"
    return HarnessPaths(
        run_root=run_root,
        fixture_root=fixture_root,
        repo_path=repo_path,
        transcript_path=transcript_path,
        share_path=share_path,
    )


def _safe_sandbox_name(*, adapter_id: str, run_root: Path) -> str:
    digest = hashlib.sha1(str(run_root).encode("utf-8")).hexdigest()[:10]
    safe_adapter = re.sub(r"[^A-Za-z0-9.+-]+", "-", adapter_id).strip(".+-") or "adapter"
    return f"aw-{safe_adapter}-{digest}"[:63]


def _adapter_fixture_dependencies(adapter: dict[str, Any]) -> list[str]:
    dependencies = adapter.get("fixture_dependencies")
    if isinstance(dependencies, list) and all(isinstance(item, str) and item.strip() for item in dependencies):
        return dependencies
    dependency = adapter.get("fixture_dependency")
    if isinstance(dependency, str) and dependency.strip():
        return [dependency]
    return ["agentic-workspace"]


def _adapter_declares_fixture_dependency(adapter: dict[str, Any]) -> bool:
    dependencies = adapter.get("fixture_dependencies")
    if isinstance(dependencies, list) and all(isinstance(item, str) and item.strip() for item in dependencies):
        return True
    dependency = adapter.get("fixture_dependency")
    return isinstance(dependency, str) and bool(dependency.strip())


def _local_aw_version() -> str:
    return str(tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"])


def _build_local_aw_wheelhouse(output_root: Path) -> Path:
    wheelhouse = output_root / "_local-aw-wheelhouse"
    if wheelhouse.exists():
        shutil.rmtree(wheelhouse)
    wheelhouse.mkdir(parents=True)
    for package_root in (REPO_ROOT, REPO_ROOT / "packages" / "memory", REPO_ROOT / "packages" / "planning", REPO_ROOT / "packages" / "verification"):
        subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(wheelhouse), str(package_root)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    return wheelhouse


def _sandbox_file_url(path: Path) -> str:
    resolved = path.resolve()
    if os.name == "nt":
        return _windows_host_path_as_sandbox_file_url(resolved.as_posix())
    return resolved.as_uri()


def _windows_host_path_as_sandbox_file_url(path: str) -> str:
    rendered = path.replace("\\", "/")
    drive_match = re.match(r"^([A-Za-z]):/(.*)$", rendered)
    if not drive_match:
        raise ValueError(f"expected a drive-qualified Windows host path for Docker sandbox file URL: {path}")
    return f"file:///{drive_match.group(1).lower()}/{drive_match.group(2)}"


def _host_file_url(path: Path) -> str:
    return path.resolve().as_uri()


def _fixture_file_url(path: Path, *, adapter: dict[str, Any]) -> str:
    sandbox = adapter.get("sandbox")
    if isinstance(sandbox, dict) and sandbox.get("backend") == "docker-sandbox":
        return _sandbox_file_url(path)
    return _host_file_url(path)


def _find_wheel(wheelhouse: Path, prefix: str, version: str) -> Path:
    matches = sorted(wheelhouse.glob(f"{prefix}-{version}-*.whl"))
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one {prefix} {version} wheel in {wheelhouse}, found {len(matches)}")
    return matches[0]


def _patch_local_aw_wheelhouse(*, source_wheelhouse: Path, target_wheelhouse: Path, release_asset_base_url: str, version: str) -> None:
    if target_wheelhouse.exists():
        shutil.rmtree(target_wheelhouse)
    shutil.copytree(source_wheelhouse, target_wheelhouse)
    subprocess.run(
        [
            "uv",
            "run",
            "python",
            "scripts/release/patch_workspace_release_wheel.py",
            "--dist-dir",
            str(target_wheelhouse),
            "--version",
            version,
            "--release-asset-base-url",
            release_asset_base_url,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )


def _relative_project_source_path(*, path: Path, repo_path: Path) -> str:
    try:
        return path.relative_to(repo_path).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _fixture_local_wheel_metadata(
    *,
    repo_path: Path,
    source_wheelhouse: Path,
    adapter: dict[str, Any],
) -> tuple[list[str], dict[str, Any]]:
    version = _local_aw_version()
    target_wheelhouse = repo_path / ".agentic-workspace" / "local" / "model-cli-harness" / "wheelhouse"
    sandbox = adapter.get("sandbox")
    if os.name == "nt" and isinstance(sandbox, dict) and sandbox.get("backend") == "docker-sandbox":
        host_wheelhouse = target_wheelhouse / "host"
        sandbox_wheelhouse = target_wheelhouse / "sandbox"
        if target_wheelhouse.exists():
            shutil.rmtree(target_wheelhouse)
        shutil.copytree(source_wheelhouse, host_wheelhouse)
        shutil.copytree(source_wheelhouse, sandbox_wheelhouse)
        uv_sources: dict[str, Any] = {}
        for package_name, wheel_prefix in LOCAL_AW_WHEEL_PACKAGES.items():
            host_wheel = _find_wheel(host_wheelhouse, wheel_prefix, version)
            sandbox_wheel = _find_wheel(sandbox_wheelhouse, wheel_prefix, version)
            uv_sources[package_name] = [
                {
                    "path": _relative_project_source_path(path=host_wheel, repo_path=repo_path),
                    "marker": "sys_platform == 'win32'",
                },
                {
                    "path": _relative_project_source_path(path=sandbox_wheel, repo_path=repo_path),
                    "marker": "sys_platform != 'win32'",
                },
            ]
        return list(LOCAL_AW_WHEEL_PACKAGES), uv_sources

    release_asset_base_url = _fixture_file_url(target_wheelhouse, adapter=adapter)
    _patch_local_aw_wheelhouse(
        source_wheelhouse=source_wheelhouse,
        target_wheelhouse=target_wheelhouse,
        release_asset_base_url=release_asset_base_url,
        version=version,
    )
    root_wheel = _find_wheel(target_wheelhouse, "agentic_workspace", version)
    return [f"agentic-workspace @ {_fixture_file_url(root_wheel, adapter=adapter)}"], {}


def _fixture_local_wheel_dependencies(*, repo_path: Path, source_wheelhouse: Path, adapter: dict[str, Any]) -> list[str]:
    dependencies, _sources = _fixture_local_wheel_metadata(repo_path=repo_path, source_wheelhouse=source_wheelhouse, adapter=adapter)
    return dependencies


def _fixture_local_wheel_dependency(*, repo_path: Path, source_wheelhouse: Path, adapter: dict[str, Any]) -> str:
    dependencies = _fixture_local_wheel_dependencies(repo_path=repo_path, source_wheelhouse=source_wheelhouse, adapter=adapter)
    if len(dependencies) != 1:
        raise RuntimeError("local wheelhouse produced platform-specific dependencies; use _fixture_local_wheel_dependencies")
    return dependencies[0]


def _prepare_fixture(
    *,
    suite_path: Path,
    scenario: dict[str, Any],
    paths: HarnessPaths,
    adapter: dict[str, Any],
    dependency_specs: list[str] | None = None,
    local_aw_wheelhouse: Path | None = None,
    source_checkout_path: str | None = None,
) -> None:
    fixture = scenario.get("fixture")
    if not isinstance(fixture, str) or not fixture.strip():
        raise ValueError(f"scenario {scenario.get('id', '<unknown>')} must specify fixture")
    fixture_path = (suite_path.parent / ".." / "fixtures" / fixture).resolve()
    if not fixture_path.exists():
        fixture_path = (REPO_ROOT / fixture).resolve()
    if not fixture_path.exists():
        raise FileNotFoundError(f"fixture not found: {fixture}")
    paths.run_root.mkdir(parents=True, exist_ok=False)
    shutil.copytree(fixture_path, paths.repo_path)
    uv_sources = None
    if local_aw_wheelhouse is not None:
        dependency_specs, uv_sources = _fixture_local_wheel_metadata(
            repo_path=paths.repo_path,
            source_wheelhouse=local_aw_wheelhouse,
            adapter=adapter,
        )
    _prepare_source_checkout_invocation(
        paths.repo_path,
        dependency_specs=dependency_specs,
        source_checkout_path=source_checkout_path,
        uv_sources=uv_sources,
    )
    _prepare_fixture_git_repository(paths.repo_path)


def _prepare_fixture_git_repository(repo_path: Path) -> None:
    if not (repo_path / ".git").exists():
        init = subprocess.run(  # noqa: S603
            ["git", "init"],
            cwd=repo_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if init.returncode != 0:
            return
    subprocess.run(  # noqa: S603
        ["git", "config", "core.longpaths", "true"],
        cwd=repo_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if _git_has_commits(repo_path):
        return
    subprocess.run(["git", "add", "."], cwd=repo_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)  # noqa: S603
    subprocess.run(  # noqa: S603
        [
            "git",
            "-c",
            "user.name=Model CLI Harness",
            "-c",
            "user.email=model-cli-harness@example.invalid",
            "commit",
            "-m",
            "Initialize harness fixture",
        ],
        cwd=repo_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def _git_has_commits(repo_path: Path) -> bool:
    result = subprocess.run(  # noqa: S603
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=repo_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _prepare_source_checkout_invocation(
    repo_path: Path,
    *,
    dependency_specs: list[str] | None = None,
    source_checkout_path: str | None = None,
    uv_sources: dict[str, Any] | None = None,
) -> None:
    if not (repo_path / ".agentic-workspace").exists():
        return

    scripts_dir = repo_path / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    script_shim = scripts_dir / "run_agentic_workspace.py"
    if not script_shim.exists():
        script_shim.write_text(
            "\n".join(
                [
                    '"""Compatibility entrypoint for source-checkout-backed harness fixtures."""',
                    "",
                    "from agentic_workspace.cli import main",
                    "",
                    "",
                    'if __name__ == "__main__":',
                    "    raise SystemExit(main())",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    pyproject = repo_path / "pyproject.toml"
    if not pyproject.exists():
        dependencies = dependency_specs or ["agentic-workspace"]
        lines = [
            "[project]",
            'name = "agentic-workspace-eval-fixture"',
            'version = "0.0.0"',
            'requires-python = ">=3.11"',
            "dependencies = [",
            *[f'  "{dependency}",' for dependency in dependencies],
            "]",
            "",
        ]
        source_entries = dict(uv_sources or {})
        if source_checkout_path:
            source_checkout_path = source_checkout_path.replace("\\", "/")
            source_entries["agentic-workspace"] = {"path": source_checkout_path, "editable": True}
        if source_entries:
            lines.extend(
                [
                    "[tool.uv.sources]",
                    *[f"{package} = {_uv_source_toml_value(source)}" for package, source in sorted(source_entries.items())],
                    "",
                ]
            )
        pyproject.write_text("\n".join(lines), encoding="utf-8")

    local_config = repo_path / ".agentic-workspace" / "config.local.toml"
    if not local_config.exists():
        local_config.write_text('schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n', encoding="utf-8")


def _uv_source_toml_value(source: Any) -> str:
    def inline_table(item: dict[str, Any]) -> str:
        return "{ " + ", ".join(f"{key} = {json.dumps(value)}" for key, value in item.items()) + " }"

    if isinstance(source, list):
        return "[" + ", ".join(inline_table(item) for item in source if isinstance(item, dict)) + "]"
    if isinstance(source, dict):
        return inline_table(source)
    return json.dumps(source)


def _terminate_process_tree(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(  # noqa: S603
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    try:
        os.killpg(pid, signal.SIGKILL)
    except (AttributeError, ProcessLookupError, PermissionError):
        try:
            os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def _run_command(command: list[str], *, cwd: Path, timeout_seconds: int, env: dict[str, str] | None = None) -> dict[str, Any]:
    resolved_command = list(command)
    executable = shutil.which(resolved_command[0])
    if executable is not None:
        resolved_command[0] = executable
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    start_new_session = os.name != "nt"
    process = subprocess.Popen(  # noqa: S603
        resolved_command,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        creationflags=creationflags,
        start_new_session=start_new_session,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_process_tree(process.pid)
        stdout, stderr = process.communicate()
    return {
        "command": resolved_command,
        "original_command": command,
        "cwd": str(cwd),
        "returncode": process.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "status": "adapter_blocked" if timed_out else "completed",
        "timed_out": timed_out,
    }


def _json_objects_from_lines(text: str) -> Iterable[dict[str, Any]]:
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            yield event


def _json_document(text: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _has_usable_model_output(result: dict[str, Any]) -> bool:
    return bool(str(result.get("stdout") or "").strip() or str(result.get("final_message") or "").strip())


def _adapter_configuration_rejected(result: dict[str, Any]) -> bool:
    combined = f"{result.get('stdout') or ''}\n{result.get('stderr') or ''}\n{result.get('final_message') or ''}".lower()
    markers = (
        "does not support reasoning effort",
        "unsupported reasoning effort",
        "unsupported adapter option",
        "unknown option",
        "invalid option",
        "unrecognized option",
        "doesn't support reasoning effort",
    )
    return isinstance(result.get("returncode"), int) and result["returncode"] != 0 and any(marker in combined for marker in markers)


def _classify_result_status(result: dict[str, Any]) -> str:
    if result.get("timed_out"):
        return "adapter_blocked"
    if _adapter_configuration_rejected(result):
        return "adapter_configuration_rejected"
    if isinstance(result.get("returncode"), int) and result["returncode"] != 0 and not _has_usable_model_output(result):
        return "runtime_failed"
    return str(result.get("status") or "completed")


def _with_git_ceiling(env: dict[str, str], *, run_root: Path) -> dict[str, str]:
    isolated = dict(env)
    ceiling = str(run_root.resolve())
    existing = isolated.get("GIT_CEILING_DIRECTORIES")
    isolated["GIT_CEILING_DIRECTORIES"] = f"{existing}{os.pathsep}{ceiling}" if existing else ceiling
    return isolated


def _is_ephemeral_mutation_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    if any(
        part in {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".venv", "__pycache__", "node_modules"} for part in parts
    ):
        return True
    return any(normalized.startswith(prefix) or normalized == prefix.rstrip("/") for prefix in EPHEMERAL_MUTATION_PATHS) or any(
        fnmatch.fnmatch(normalized, pattern) for pattern in EPHEMERAL_MUTATION_GLOBS
    )


def _is_harness_setup_mutation_path(path: str, *, patterns: Iterable[str] | None = None) -> bool:
    if patterns is None:
        return False
    normalized = path.replace("\\", "/")
    candidates = tuple(patterns)
    return any(
        normalized.startswith(pattern) or normalized == pattern.rstrip("/") or fnmatch.fnmatch(normalized, pattern)
        for pattern in candidates
    )


def _file_snapshot(root: Path, *, include_ignored: bool = False) -> dict[str, dict[str, Any]]:
    snapshot: dict[str, dict[str, Any]] = {}
    if not root.exists():
        return snapshot
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative.startswith(".git/"):
            continue
        if not include_ignored and _is_ephemeral_mutation_path(relative):
            continue
        data = path.read_bytes()
        snapshot[relative] = {
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    return snapshot


def _path_changes(
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
    *,
    paths: Iterable[str],
) -> dict[str, list[str]]:
    selected = set(paths)
    before_paths = set(before) & selected
    after_paths = set(after) & selected
    return {
        "created": sorted(after_paths - before_paths),
        "deleted": sorted(before_paths - after_paths),
        "modified": sorted(path for path in before_paths & after_paths if before[path] != after[path]),
    }


def _snapshot_diff(
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
    *,
    harness_setup_patterns: Iterable[str] | None = None,
) -> dict[str, Any]:
    before_paths = set(before)
    after_paths = set(after)
    raw_created = sorted(after_paths - before_paths)
    raw_deleted = sorted(before_paths - after_paths)
    raw_modified = sorted(path for path in before_paths & after_paths if before[path] != after[path])
    changed_paths = sorted(set(raw_created + raw_deleted + raw_modified))
    ignored_paths = [path for path in changed_paths if _is_ephemeral_mutation_path(path)]
    setup_paths = [
        path
        for path in changed_paths
        if path not in ignored_paths and _is_harness_setup_mutation_path(path, patterns=harness_setup_patterns)
    ]
    source_paths = [path for path in changed_paths if path not in set(ignored_paths) and path not in set(setup_paths)]
    source_changes = _path_changes(before, after, paths=source_paths)
    ignored_changes = _path_changes(before, after, paths=ignored_paths)
    setup_changes = _path_changes(before, after, paths=setup_paths)
    raw_status = "changed" if changed_paths else "clean"
    return {
        "status": "changed" if source_paths else "clean",
        "raw_status": raw_status,
        "created_count": len(source_changes["created"]),
        "modified_count": len(source_changes["modified"]),
        "deleted_count": len(source_changes["deleted"]),
        "created": source_changes["created"],
        "modified": source_changes["modified"],
        "deleted": source_changes["deleted"],
        "source_created": source_changes["created"],
        "source_modified": source_changes["modified"],
        "source_deleted": source_changes["deleted"],
        "raw_created_count": len(raw_created),
        "raw_modified_count": len(raw_modified),
        "raw_deleted_count": len(raw_deleted),
        "raw_created": raw_created,
        "raw_modified": raw_modified,
        "raw_deleted": raw_deleted,
        "ignored_noise_count": len(ignored_paths),
        "ignored_created": ignored_changes["created"],
        "ignored_modified": ignored_changes["modified"],
        "ignored_deleted": ignored_changes["deleted"],
        "harness_setup_count": len(setup_paths),
        "harness_setup_created": setup_changes["created"],
        "harness_setup_modified": setup_changes["modified"],
        "harness_setup_deleted": setup_changes["deleted"],
    }


def _candidate_path(value: str, *, replacements: dict[str, str]) -> str:
    return os.path.expandvars(_replace_placeholders(value, replacements=replacements))


def _resolve_requirement(name: str, *, candidate_paths: list[str] | None = None, replacements: dict[str, str] | None = None) -> str | None:
    for candidate in candidate_paths or []:
        candidate_path = Path(_candidate_path(candidate, replacements=replacements or {}))
        if candidate_path.exists():
            return str(candidate_path)
    resolved = shutil.which(name)
    if resolved:
        return resolved
    return None


def _preflight_requirement(
    requirement: str | dict[str, Any],
    *,
    kind: str,
    replacements: dict[str, str] | None = None,
) -> dict[str, Any]:
    if isinstance(requirement, str):
        name = requirement
        candidate_paths: list[str] = []
        add_parent_to_path = False
    elif isinstance(requirement, dict):
        raw_name = requirement.get("name")
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise ValueError(f"{kind} requirement objects must include a string name")
        name = raw_name
        raw_candidates = requirement.get("candidate_paths", [])
        if not isinstance(raw_candidates, list) or not all(isinstance(item, str) for item in raw_candidates):
            raise ValueError(f"{kind} requirement candidate_paths must be a string list")
        candidate_paths = raw_candidates
        add_parent_to_path = bool(requirement.get("add_parent_to_path", False))
    else:
        raise ValueError(f"{kind} requirements must be strings or objects")
    resolved = _resolve_requirement(name, candidate_paths=candidate_paths, replacements=replacements)
    return {
        "kind": kind,
        "name": name,
        "status": "present" if resolved else "missing",
        "resolved_path": resolved or "",
        "add_parent_to_path": add_parent_to_path,
        "blocking": resolved is None,
    }


def _adapter_preflight(adapter: dict[str, Any], *, command: list[str], replacements: dict[str, str]) -> dict[str, Any]:
    requirements: list[dict[str, Any]] = []
    if command:
        adapter_executable = adapter.get("adapter_executable", command[0])
        requirements.append(_preflight_requirement(adapter_executable, kind="adapter_executable", replacements=replacements))
    for requirement in adapter.get("required_executables", []):
        requirements.append(_preflight_requirement(requirement, kind="required_executable", replacements=replacements))
    for requirement in adapter.get("required_shells", []):
        requirements.append(_preflight_requirement(requirement, kind="required_shell", replacements=replacements))

    missing = [item for item in requirements if item["status"] == "missing"]
    block_on_failure = bool(adapter.get("block_on_preflight_failure", True))
    status = "environment-blocked" if block_on_failure and missing else "ready"
    return {
        "status": status,
        "block_on_failure": block_on_failure,
        "requirements": requirements,
        "missing_count": len(missing),
        "missing": missing,
        "path_prepend": [
            str(Path(item["resolved_path"]).parent) for item in requirements if item.get("add_parent_to_path") and item.get("resolved_path")
        ],
    }


def _execution_command(command: list[str], preflight: dict[str, Any]) -> list[str]:
    if not command:
        return command
    requirements = preflight.get("requirements", [])
    if not isinstance(requirements, list):
        return command
    adapter_requirement = next(
        (item for item in requirements if isinstance(item, dict) and item.get("kind") == "adapter_executable"),
        None,
    )
    if not isinstance(adapter_requirement, dict):
        return command
    resolved = adapter_requirement.get("resolved_path")
    if not isinstance(resolved, str) or not resolved:
        return command
    requirement_name = str(adapter_requirement.get("name") or "")
    command_name = Path(command[0]).name
    if requirement_name and command_name.lower() != requirement_name.lower():
        return command
    return [resolved, *command[1:]]


def _adapter_sandbox_report(
    adapter: dict[str, Any],
    *,
    adapter_id: str,
    model: str,
    repo_path: Path,
    preflight: dict[str, Any],
    command: list[str],
) -> dict[str, Any] | None:
    config = adapter.get("sandbox")
    if config is None:
        return None
    if not isinstance(config, dict):
        raise ValueError("adapter.sandbox must be an object")
    backend = config.get("backend")
    agent = config.get("agent")
    if not isinstance(backend, str) or not backend.strip():
        raise ValueError("adapter.sandbox.backend must be a string")
    if not isinstance(agent, str) or not agent.strip():
        raise ValueError("adapter.sandbox.agent must be a string")
    sandbox_name = ""
    if "--sandbox-name" in command:
        index = command.index("--sandbox-name")
        if index + 1 < len(command):
            sandbox_name = str(command[index + 1])
    return {
        "kind": SANDBOX_ADAPTER_KIND,
        "enabled": True,
        "backend": backend,
        "agent": agent,
        "adapter_id": adapter_id,
        "model": model,
        "identity": f"{backend}:{agent}:{adapter_id}",
        "sandbox_name": sandbox_name,
        "template": str(config.get("template") or ""),
        "repo_path": str(repo_path),
        "evidence": "sandbox-backed",
        "setup_status": preflight.get("status", "unknown"),
        "setup_failures": preflight.get("missing", []),
        "command": command,
        "fail_closed": True,
    }


def _sandbox_runtime_report(sandbox_report: dict[str, Any] | None, result: dict[str, Any]) -> dict[str, Any] | None:
    if not sandbox_report:
        return sandbox_report
    updated = dict(sandbox_report)
    updated["runtime_status"] = str(result.get("status") or "")
    updated["runtime_returncode"] = result.get("returncode")
    stderr = str(result.get("stderr") or "").strip()
    returncode = result.get("returncode")
    if stderr and (updated["runtime_status"] != "completed" or (isinstance(returncode, int) and returncode != 0)):
        error_line = next((line for line in stderr.splitlines() if "error" in line.lower() or "unauthorized" in line.lower()), "")
        updated["runtime_error"] = (error_line or stderr.splitlines()[0])[:500]
    return updated


def _sandbox_runtime_warnings(sandbox_report: dict[str, Any] | None, result: dict[str, Any]) -> list[dict[str, Any]]:
    if not sandbox_report or not sandbox_report.get("enabled"):
        return []
    status = str(result.get("status") or "")
    returncode = result.get("returncode")
    if status not in {"completed", "dry-run"} or (isinstance(returncode, int) and returncode != 0):
        return [
            {
                "warning_class": "model_cli_sandbox_runtime_failed",
                "message": "The sandbox-backed adapter failed before producing usable model output.",
                "sandbox": sandbox_report.get("identity", ""),
                "returncode": returncode,
            }
        ]
    return []


def _capture_adapter_artifacts(
    adapter: dict[str, Any],
    *,
    replacements: dict[str, str],
    share_path: Path,
) -> dict[str, Any]:
    config = adapter.get("artifact_capture", {})
    if config is None:
        config = {}
    if not isinstance(config, dict):
        raise ValueError("adapter.artifact_capture must be an object")
    candidates = _string_list_config(config.get("share_path_candidates"), field="adapter.artifact_capture.share_path_candidates")
    cleanup = bool(config.get("cleanup_captured", False))
    captured_from = ""
    candidate_reports: list[dict[str, str]] = []
    if not share_path.exists():
        for candidate in candidates:
            rendered = Path(_replace_placeholders(candidate, replacements=replacements))
            status = "present" if rendered.exists() else "missing"
            candidate_reports.append({"path": str(rendered), "status": status})
            if not rendered.is_file():
                continue
            share_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(rendered, share_path)
            captured_from = str(rendered)
            if cleanup and rendered.resolve() != share_path.resolve():
                rendered.unlink(missing_ok=True)
            break
    return {
        "kind": "agentic-workspace/model-cli-adapter-artifact-capture/v1",
        "share_path": str(share_path),
        "share_captured": share_path.exists(),
        "share_captured_from": captured_from,
        "share_path_candidates": candidate_reports,
    }


def _adapter_environment(
    adapter: dict[str, Any],
    *,
    replacements: dict[str, str],
    isolate_provider_home: bool,
) -> dict[str, str]:
    env = dict(os.environ)
    configured = adapter.get("env", {})
    if configured:
        if not isinstance(configured, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in configured.items()
        ):
            raise ValueError("adapter.env must be an object of string values")
        env.update({key: _replace_placeholders(value, replacements=replacements) for key, value in configured.items()})
    provider_home_env = adapter.get("provider_home_env")
    if isolate_provider_home and provider_home_env:
        if not isinstance(provider_home_env, str):
            raise ValueError("adapter.provider_home_env must be a string")
        env[provider_home_env] = _replace_placeholders(
            str(adapter.get("provider_home_path", "{run_root}/provider-home")), replacements=replacements
        )
    return env


def _prepend_env_path(env: dict[str, str], entries: list[str]) -> dict[str, str]:
    if not entries:
        return env
    updated = dict(env)
    current_path = updated.get("PATH", "")
    unique_entries = []
    seen = set()
    for entry in entries:
        normalized = str(Path(entry))
        key = normalized.lower()
        if key not in seen:
            unique_entries.append(normalized)
            seen.add(key)
    updated["PATH"] = os.pathsep.join(unique_entries + ([current_path] if current_path else []))
    return updated


def _copy_transcript(stdout: str, transcript_path: Path) -> None:
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.write_text(stdout, encoding="utf-8")


def _usage_summary_from_stdout(stdout: str) -> dict[str, Any]:
    totals = {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_output_tokens": 0,
    }
    event_count = 0
    provider_stats: dict[str, Any] | None = None
    document = _json_document(stdout.strip())
    if document is not None:
        stats = document.get("stats")
        if isinstance(stats, dict):
            provider_stats = stats
    for event in _json_objects_from_lines(stdout):
        stats = event.get("stats")
        if provider_stats is None and isinstance(stats, dict):
            provider_stats = stats
    provider_total_tokens = 0
    if provider_stats is not None:
        token_candidates = (
            ("input_tokens", ("input_tokens", "inputTokens", "promptTokenCount")),
            ("output_tokens", ("output_tokens", "outputTokens", "candidatesTokenCount")),
        )
        for output_key, candidate_keys in token_candidates:
            for candidate_key in candidate_keys:
                value = provider_stats.get(candidate_key)
                if isinstance(value, int | float):
                    totals[output_key] += int(value)
                    break
        for candidate_key in ("total_tokens", "totalTokens", "totalTokenCount"):
            value = provider_stats.get(candidate_key)
            if isinstance(value, int | float):
                provider_total_tokens = int(value)
                break
    for event in _json_objects_from_lines(stdout):
        if event.get("type") != "turn.completed":
            continue
        usage = event.get("usage")
        if not isinstance(usage, dict):
            continue
        event_count += 1
        for key in totals:
            value = usage.get(key)
            if isinstance(value, int | float):
                totals[key] += int(value)
    uncached_input = max(0, totals["input_tokens"] - totals["cached_input_tokens"])
    summary = {
        "status": "present" if event_count else "absent",
        "turn_count": event_count,
        **totals,
        "uncached_input_tokens": uncached_input,
        "total_billable_proxy_tokens": uncached_input + totals["output_tokens"] + totals["reasoning_output_tokens"],
    }
    if provider_stats is not None:
        summary["status"] = "present"
        summary["provider_stats"] = provider_stats
        if provider_total_tokens:
            summary["provider_total_tokens"] = provider_total_tokens
    return summary


def _is_agentic_workspace_command(command: str) -> bool:
    normalized = command.replace("\\", "/").lower()
    return any(
        marker in normalized
        for marker in (
            "agentic-workspace",
            "agentic-planning",
            "agentic-memory",
            "repo_planning_bootstrap",
            "repo_memory_bootstrap",
        )
    )


def _is_mixed_package_shell_command(command: str) -> bool:
    raw_read_pattern = r"\b(Get-Content|cat|type|Write-Output)\b"
    command_separator_pattern = (
        r"(;|&&|\|\|)\s*"
        r"(uv\s+run\s+)?"
        r"(agentic-workspace|agentic-planning|agentic-memory|repo-planning|repo-memory|"
        r"Get-Content|cat\b|type\b|Write-Output)"
    )
    return bool(re.search(raw_read_pattern, command, flags=re.IGNORECASE)) or bool(
        re.search(command_separator_pattern, command, flags=re.IGNORECASE)
    )


def _package_read_surface_summary_from_stdout(stdout: str) -> dict[str, Any]:
    """Separate package command payload size from provider/runtime token accounting."""
    command_count = 0
    output_bytes = 0
    output_lines = 0
    mixed_command_count = 0
    commands: list[dict[str, Any]] = []
    for event in _json_objects_from_lines(stdout):
        item = event.get("item")
        if not isinstance(item, dict) or item.get("type") != "command_execution":
            continue
        if item.get("status") != "completed":
            continue
        command = str(item.get("command", ""))
        if not _is_agentic_workspace_command(command):
            continue
        mixed_shell_command = _is_mixed_package_shell_command(command)
        output = str(item.get("aggregated_output", ""))
        encoded = output.encode("utf-8", errors="replace")
        line_count = 0 if not output else len(output.splitlines())
        command_count += 1
        output_bytes += len(encoded)
        output_lines += line_count
        if mixed_shell_command:
            mixed_command_count += 1
        commands.append(
            {
                "command_excerpt": command[:180],
                "output_bytes": len(encoded),
                "output_lines": line_count,
                "exit_code": item.get("exit_code"),
                "status": item.get("status"),
                "mixed_shell_command": mixed_shell_command,
            }
        )
    largest = max((item["output_bytes"] for item in commands), default=0)
    return {
        "kind": "agentic-workspace/package-read-surface-summary/v1",
        "status": "present" if command_count else "absent",
        "command_count": command_count,
        "output_bytes": output_bytes,
        "output_lines": output_lines,
        "largest_command_output_bytes": largest,
        "mixed_command_count": mixed_command_count,
        "commands": commands[:10],
        "omitted_command_count": max(0, len(commands) - 10),
        "precision": "approximate" if mixed_command_count else "direct",
        "metric_role": "package command output size only when commands are direct; mixed shell commands are marked approximate",
    }


def _aggregate_package_read_surface_summaries(results: list[dict[str, Any]]) -> dict[str, Any]:
    present_count = 0
    command_count = 0
    output_bytes = 0
    output_lines = 0
    largest = 0
    mixed_command_count = 0
    for result in results:
        summary = result.get("package_read_surface_summary")
        if not isinstance(summary, dict) or summary.get("status") != "present":
            continue
        present_count += 1
        command_count += int(summary.get("command_count", 0) or 0)
        output_bytes += int(summary.get("output_bytes", 0) or 0)
        output_lines += int(summary.get("output_lines", 0) or 0)
        largest = max(largest, int(summary.get("largest_command_output_bytes", 0) or 0))
        mixed_command_count += int(summary.get("mixed_command_count", 0) or 0)
    return {
        "kind": "agentic-workspace/package-read-surface-aggregate/v1",
        "status": "present" if present_count else "absent",
        "result_count": present_count,
        "command_count": command_count,
        "output_bytes": output_bytes,
        "output_lines": output_lines,
        "largest_command_output_bytes": largest,
        "mixed_command_count": mixed_command_count,
        "precision": "approximate" if mixed_command_count else "direct",
        "metric_role": "aggregate Agentic Workspace command output size; provider token summaries remain separate",
    }


PROPORTIONALITY_GUARDRAIL_SCENARIOS = {
    "direct-task-minimal-overhead",
    "next-decision-output-profile",
    "config-closeout-obligation",
}


def _is_proportionality_guardrail_scenario(scenario: dict[str, Any]) -> bool:
    return bool(scenario.get("proportionality_guardrail")) or str(scenario.get("id", "")) in PROPORTIONALITY_GUARDRAIL_SCENARIOS


def _command_contains_any(command_text: str, markers: list[str]) -> bool:
    normalized = _normalized_command_text(command_text)
    return any(_normalized_command_text(marker) in normalized for marker in markers)


def _proportionality_metrics(
    *,
    scenario: dict[str, Any],
    result: dict[str, Any],
    mutation_summary: dict[str, Any] | None,
    package_read_surface_summary: dict[str, Any] | None,
    completion_loop: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not _is_proportionality_guardrail_scenario(scenario):
        return {"kind": "agentic-workspace/model-cli-proportionality-metrics/v1", "status": "not-applicable"}
    changed_paths = _changed_paths(mutation_summary)
    created = [path.replace("\\", "/") for path in (mutation_summary or {}).get("created", []) if isinstance(path, str)]
    executed_command_text = _normalized_command_text(_executed_command_text(result))
    scored_response_text = _scored_agent_response_text(result)
    mentioned_paths = sorted(
        dict.fromkeys([*_mentioned_workspace_paths(scored_response_text), *_mentioned_workspace_paths(executed_command_text)])
    )
    scored_text = _normalized_command_text(scored_response_text)
    combined_agent_text = f"{executed_command_text}\n{scored_text}"
    workspace_mentions = [path for path in mentioned_paths if path.startswith(".agentic-workspace/")]
    memory_mentions = [path for path in workspace_mentions if path.startswith(".agentic-workspace/memory/")]
    planning_created = [path for path in created if path.startswith(".agentic-workspace/planning/")]
    memory_created = [path for path in created if path.startswith(".agentic-workspace/memory/")]
    diagnostic_markers = (
        "--verbose",
        "agentic-workspace report",
        "agentic-workspace doctor",
        "agentic-workspace preflight",
        "agentic-workspace summary --verbose",
        "agentic-workspace implement --verbose",
        "agentic-workspace proof --verbose",
    )
    broad_diagnostic_markers = (
        "agentic-workspace report",
        "agentic-workspace doctor",
        "agentic-workspace preflight",
        "agentic-workspace summary",
    )
    raw_workspace_read_patterns = (
        r"\b(get-content|cat|type|read_file|open)\b[^\n;|&]*\.agentic-workspace/",
        r"\.agentic-workspace/[^\s`'\"),;]+[^\n.]*\b(read|opened|inspected)\b",
    )
    raw_workspace_read_count = sum(
        1 for pattern in raw_workspace_read_patterns for _match in re.finditer(pattern, combined_agent_text, flags=re.IGNORECASE)
    )
    package_summary = package_read_surface_summary if isinstance(package_read_surface_summary, dict) else {}
    return {
        "kind": "agentic-workspace/model-cli-proportionality-metrics/v1",
        "status": "present",
        "scenario_id": str(scenario.get("id", "")),
        "package_command_count": int(package_summary.get("command_count", 0) or 0),
        "package_output_bytes": int(package_summary.get("output_bytes", 0) or 0),
        "package_output_lines": int(package_summary.get("output_lines", 0) or 0),
        "workspace_command_count": int(package_summary.get("command_count", 0) or 0),
        "raw_workspace_file_mentions": len(workspace_mentions),
        "raw_workspace_read_count": raw_workspace_read_count,
        "files_read_or_mentioned_count": len(mentioned_paths),
        "files_read_or_mentioned": mentioned_paths[:20],
        "changed_files_count": len(changed_paths),
        "planning_files_created": len(planning_created),
        "memory_files_created": len(memory_created),
        "memory_files_read_or_mentioned": len(memory_mentions),
        "verbose_or_full_diagnostic_count": sum(combined_agent_text.count(marker) for marker in diagnostic_markers),
        "broad_workspace_diagnostic_count": sum(combined_agent_text.count(marker) for marker in broad_diagnostic_markers),
        "requests_to_completion": int((completion_loop or {}).get("requests_to_completion", 0) or 0),
        "final_answer_length": len(_scored_agent_response_text(result)),
    }


def _proportionality_warnings(
    *,
    scenario: dict[str, Any],
    result: dict[str, Any],
    metrics: dict[str, Any],
) -> list[dict[str, str]]:
    if metrics.get("status") != "present":
        return []
    limits = scenario.get("proportionality_limits", {})
    if not isinstance(limits, dict):
        limits = {}
    warnings: list[dict[str, str]] = []

    def add(warning_class: str, message: str, *, evidence: str = "", mistake_class: str = "") -> None:
        warning: dict[str, str] = {"warning_class": warning_class, "message": message}
        if evidence:
            warning["evidence"] = evidence
        if mistake_class:
            warning["mistake_class"] = mistake_class
        warnings.append(warning)

    if metrics["planning_files_created"]:
        add(
            "model_cli_proportionality_over_planning",
            "Tiny bounded work created Planning residue without scenario justification.",
            evidence=f"planning_files_created={metrics['planning_files_created']}",
            mistake_class="over_planning",
        )
    if metrics["memory_files_created"] or metrics["memory_files_read_or_mentioned"]:
        add(
            "model_cli_proportionality_memory_ceremony",
            "Tiny bounded work used Memory despite no durable anti-rediscovery need in the scenario.",
            evidence=(
                f"memory_files_created={metrics['memory_files_created']}; "
                f"memory_files_read_or_mentioned={metrics['memory_files_read_or_mentioned']}"
            ),
            mistake_class="memory_ceremony",
        )
    max_workspace_commands = limits.get("workspace_command_count")
    if isinstance(max_workspace_commands, int) and metrics["workspace_command_count"] > max_workspace_commands:
        add(
            "model_cli_proportionality_over_reading",
            "Tiny bounded work used more Agentic Workspace commands than the scenario budget allows.",
            evidence=f"workspace_command_count={metrics['workspace_command_count']}; limit={max_workspace_commands}",
            mistake_class="over_reading",
        )
    max_verbose = limits.get("verbose_or_full_diagnostic_count", 0)
    if isinstance(max_verbose, int) and metrics["verbose_or_full_diagnostic_count"] > max_verbose:
        add(
            "model_cli_proportionality_over_reading",
            "Tiny bounded work used verbose or full diagnostics where compact output should suffice.",
            evidence=f"verbose_or_full_diagnostic_count={metrics['verbose_or_full_diagnostic_count']}; limit={max_verbose}",
            mistake_class="verbose_diagnostics_for_tiny_task",
        )
    if metrics["raw_workspace_read_count"]:
        add(
            "model_cli_proportionality_over_reading",
            "Tiny bounded work appears to read raw `.agentic-workspace` files instead of compact command surfaces.",
            evidence=f"raw_workspace_read_count={metrics['raw_workspace_read_count']}",
            mistake_class="raw_workspace_spelunking",
        )
    avoid_broad_proof = scenario.get("proportionality_avoid_broad_proof_commands", [])
    if isinstance(avoid_broad_proof, list) and all(isinstance(item, str) for item in avoid_broad_proof):
        command_text = _executed_command_text(result)
        broad_proof = [marker for marker in avoid_broad_proof if _command_contains_any(command_text, [marker])]
        if broad_proof:
            add(
                "model_cli_proportionality_over_proofing",
                "Tiny bounded work used broad proof where the scenario expects narrow local proof.",
                evidence=", ".join(broad_proof[:8]),
                mistake_class="over_proofing",
            )
    max_final = limits.get("final_answer_length")
    if isinstance(max_final, int) and metrics["final_answer_length"] > max_final:
        add(
            "model_cli_proportionality_closeout_ceremony",
            "Tiny bounded work produced a longer closeout than the scenario budget allows.",
            evidence=f"final_answer_length={metrics['final_answer_length']}; limit={max_final}",
            mistake_class="closeout_ceremony",
        )
    return warnings


def _aggregate_proportionality_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    present = [
        result.get("proportionality_metrics")
        for result in results
        if isinstance(result.get("proportionality_metrics"), dict) and result["proportionality_metrics"].get("status") == "present"
    ]
    numeric_fields = (
        "package_command_count",
        "package_output_bytes",
        "package_output_lines",
        "workspace_command_count",
        "raw_workspace_file_mentions",
        "raw_workspace_read_count",
        "changed_files_count",
        "planning_files_created",
        "memory_files_created",
        "memory_files_read_or_mentioned",
        "verbose_or_full_diagnostic_count",
        "broad_workspace_diagnostic_count",
        "requests_to_completion",
        "final_answer_length",
    )
    totals = {field: sum(int(metrics.get(field, 0) or 0) for metrics in present) for field in numeric_fields}
    return {
        "kind": "agentic-workspace/model-cli-proportionality-summary/v1",
        "status": "present" if present else "absent",
        "result_count": len(present),
        "scenario_ids": sorted({str(metrics.get("scenario_id", "")) for metrics in present if metrics.get("scenario_id")}),
        "totals": totals,
    }


def _aggregate_usage_summaries(results: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_output_tokens": 0,
        "uncached_input_tokens": 0,
        "total_billable_proxy_tokens": 0,
    }
    present_count = 0
    for result in results:
        usage = result.get("usage_summary")
        if not isinstance(usage, dict) or usage.get("status") != "present":
            continue
        present_count += 1
        for key in totals:
            value = usage.get(key)
            if isinstance(value, int | float):
                totals[key] += int(value)
    return {"status": "present" if present_count else "absent", "result_count": present_count, **totals}


def _response_text(result: dict[str, Any]) -> str:
    final_message = result.get("final_message")
    stdout = result.get("stdout")
    stderr = result.get("stderr")
    parts: list[str] = []
    if isinstance(final_message, str) and final_message.strip():
        parts.append(_last_copilot_transcript_answer(final_message))
    if isinstance(stdout, str):
        stripped = stdout.strip()
        if stripped.startswith("{"):
            payload = _json_document(stripped)
            if isinstance(payload, dict) and isinstance(payload.get("response"), str):
                parts.append(payload["response"])
        for event in _json_objects_from_lines(stdout):
            data = event.get("data")
            if isinstance(data, dict) and isinstance(data.get("content"), str):
                parts.append(data["content"])
            message = event.get("message")
            if isinstance(message, str):
                parts.append(message)
            elif isinstance(message, dict) and isinstance(message.get("content"), str):
                parts.append(message["content"])
        if not parts:
            parts.append(stdout)
    if isinstance(stderr, str):
        parts.append(stderr)
    return "\n".join(parts)


def _scored_agent_response_text(result: dict[str, Any]) -> str:
    """Return model-authored response text without command payload or injected prompt echoes."""
    parts: list[str] = []
    final_message = result.get("final_message")
    if isinstance(final_message, str) and final_message.strip():
        parts.append(_last_copilot_transcript_answer(final_message))
    stdout = result.get("stdout")
    if isinstance(stdout, str):
        stripped = stdout.strip()
        if stripped.startswith("{"):
            payload = _json_document(stripped)
            if isinstance(payload, dict) and isinstance(payload.get("response"), str):
                parts.append(payload["response"])
        for event in _json_objects_from_lines(stdout):
            if isinstance(event.get("response"), str):
                parts.append(event["response"])
            data = event.get("data")
            if isinstance(data, dict) and isinstance(data.get("content"), str):
                parts.append(data["content"])
            message = event.get("message")
            if isinstance(message, str):
                parts.append(message)
            elif isinstance(message, dict) and isinstance(message.get("content"), str):
                parts.append(message["content"])
    return "\n".join(part for part in parts if part.strip())


def _full_response_text(result: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("final_message", "stdout", "stderr"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value)
    return "\n".join(parts)


_LOCAL_ABSOLUTE_PATH_PATTERNS = (
    re.compile(r"\b[A-Za-z]:[\\/][^\s)`>\"']+"),
    re.compile(r"(?<![\w/.-])/(?:Users|home|tmp|var/tmp|private/tmp)/[^\s)`>\"']+"),
)


def _path_from_local_evidence(evidence: str) -> Path | None:
    candidate = evidence.strip().rstrip(".,;:")
    if not candidate:
        return None
    try:
        return Path(candidate)
    except (OSError, ValueError):
        return None


def _repair_local_absolute_paths_in_text(*, text: str, repo_path: Path, run_root: Path) -> dict[str, Any]:
    repairs: list[dict[str, str]] = []

    def replacement(match: re.Match[str]) -> str:
        evidence = match.group(0)
        path = _path_from_local_evidence(evidence)
        if path is None:
            return "<local path>"
        replacement_text = "<local path>"
        repair_kind = "local_path_redacted"
        if _is_relative_to(path, repo_path):
            replacement_text = path.resolve().relative_to(repo_path.resolve()).as_posix()
            repair_kind = "repo_relative"
        elif _is_relative_to(path, run_root):
            replacement_text = "<harness artifact>"
            repair_kind = "harness_artifact_role"
        repairs.append({"kind": repair_kind, "replacement": replacement_text})
        return replacement_text

    repaired = text
    for pattern in _LOCAL_ABSOLUTE_PATH_PATTERNS:
        repaired = pattern.sub(replacement, repaired)
    return {
        "kind": "agentic-workspace/model-cli-final-message-local-path-repair/v1",
        "status": "repaired" if repairs and repaired != text else "not-needed",
        "repair_count": len(repairs),
        "repairs": repairs,
        "rule": "Raw model text remains the scoring source; exported final_message text must not expose local absolute paths.",
        "text": repaired,
    }


def _repair_result_final_message_local_paths(*, result: dict[str, Any], repo_path: Path, run_root: Path, share_path: Path) -> dict[str, Any]:
    final_message = result.get("final_message")
    if not isinstance(final_message, str) or not final_message:
        return {
            "kind": "agentic-workspace/model-cli-final-message-local-path-repair/v1",
            "status": "not-needed",
            "repair_count": 0,
            "repairs": [],
            "rule": "Raw model text remains the scoring source; exported final_message text must not expose local absolute paths.",
        }
    repair = _repair_local_absolute_paths_in_text(text=final_message, repo_path=repo_path, run_root=run_root)
    repaired_text = str(repair.pop("text"))
    if repair["status"] == "repaired":
        result["final_message"] = repaired_text
        share_path.write_text(repaired_text, encoding="utf-8")
    return repair


def _last_copilot_transcript_answer(text: str) -> str:
    matches = list(re.finditer(r"^### .+ Copilot\s*$", text, flags=re.MULTILINE))
    if not matches:
        return text
    tail = text[matches[-1].end() :]
    for marker in ("---\n\n<sub>Generated by", "\n\n---\n\n<sub>Generated by"):
        if marker in tail:
            tail = tail.split(marker, 1)[0]
    return tail.strip()


def _created_path_is_misplaced_planning_artifact(path: str) -> bool:
    normalized = path.replace("\\", "/").strip()
    suffixes = (".json", ".md")
    if not normalized.endswith(suffixes):
        return False
    canonical_decomposition_prefix = ".agentic-workspace/planning/decompositions/"
    canonical_execplan_prefix = ".agentic-workspace/planning/execplans/"
    if normalized.startswith(canonical_decomposition_prefix) and normalized.endswith(".decomposition.json"):
        return False
    if normalized.startswith(canonical_execplan_prefix) and normalized.endswith(".plan.json"):
        return False
    planning_markers = ("decomposition", "planning", "plan", "epic", "roadmap")
    name = Path(normalized).name.lower()
    return (
        normalized.startswith("planning/")
        or normalized.startswith(".agentic-workspace/planning/")
        and any(marker in normalized.lower() for marker in planning_markers)
        or any(marker in name for marker in planning_markers)
    )


def _created_path_is_planning_only_side_doc(path: str) -> bool:
    normalized = path.replace("\\", "/").strip()
    name = Path(normalized).name.lower()
    if not normalized.endswith(".md"):
        return False
    if normalized.startswith(".agentic-workspace/planning/"):
        return False
    return normalized.startswith(".agentic-workspace/") and (
        name in {"architecture.md", "adr.md", "handoff.md"} or "architecture" in name or "adr" in name or "handoff" in name
    )


def _changed_paths(mutation_summary: dict[str, Any] | None) -> list[str]:
    if not isinstance(mutation_summary, dict):
        return []
    paths: list[str] = []
    for key in ("created", "modified", "deleted"):
        values = mutation_summary.get(key, [])
        if isinstance(values, list):
            paths.extend(value.replace("\\", "/") for value in values if isinstance(value, str))
    return sorted(dict.fromkeys(paths))


def _matches_any(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pattern.replace("\\", "/")) for pattern in patterns)


def _contains_forbidden_phrase(text: str, phrase: str) -> bool:
    lowered_phrase = phrase.lower()
    if lowered_phrase.startswith("/"):
        return re.search(rf"(?<![\w.-]){re.escape(lowered_phrase)}(?![\w.-])", text) is not None
    return lowered_phrase in text


def _strip_local_path_targets_for_scoring(text: str) -> str:
    without_markdown_targets = re.sub(r"\]\([A-Za-z]:[/\\][^)]+\)", "]", text)
    return re.sub(r"\b[A-Za-z]:[/\\]\S+", "<local-path>", without_markdown_targets)


def _normalized_signal_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[._-]+", " ", text.lower())).strip()


def _contains_required_signal(text: str, required: str) -> bool:
    lowered_required = required.lower()
    return lowered_required in text or _normalized_signal_text(lowered_required) in _normalized_signal_text(text)


def _normalized_command_text(text: str) -> str:
    normalized = text.lower().replace("\\", "/")
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    return normalized


def _command_requirement_satisfied(*, required: str, executed_command_text: str) -> bool:
    normalized_required = _normalized_command_text(required)
    return any(candidate in executed_command_text for candidate in _equivalent_command_requirements(normalized_required))


def _equivalent_command_requirements(normalized_required: str) -> list[str]:
    equivalents = [normalized_required]
    package_prefix = "uv run agentic-workspace "
    if normalized_required.startswith(package_prefix):
        suffix = normalized_required[len(package_prefix) :]
        equivalents.append(f"uv run python scripts/run_agentic_workspace.py {suffix}")
    return equivalents


def _provider_did_not_run(result: dict[str, Any]) -> bool:
    returncode = result.get("returncode")
    stdout = str(result.get("stdout") or "").strip()
    final_message = str(result.get("final_message") or "").strip()
    return isinstance(returncode, int) and returncode != 0 and not stdout and not final_message


def _agentic_workspace_tooling_unavailable(result: dict[str, Any]) -> bool:
    combined = _full_response_text(result)
    if "agentic-workspace" not in combined:
        return False
    return (
        "Permission denied and could not request permission from user" in combined
        or 'Tool "run_shell_command" not found' in combined
        or 'Tool "run_shell_command" not found' in combined
    )


def _raw_planning_before_fallback_workflow(result: dict[str, Any]) -> bool:
    text = _full_response_text(result).lower().replace("\\", "/")
    raw_markers = [
        ".agentic-workspace/planning",
        "planning/execplans",
        "planning/decompositions",
        "planning/schemas",
    ]
    raw_markers.extend(match.group(0) for match in re.finditer(r"`planning`\s+directory|\bplanning\s+directory\b", text))
    raw_positions = [text.find(marker) for marker in raw_markers if text.find(marker) >= 0]
    if not raw_positions:
        return False
    workflow_positions = [text.find(marker) for marker in (".agentic-workspace/workflow.md", "workflow.md") if text.find(marker) >= 0]
    first_raw = min(raw_positions)
    first_workflow = min(workflow_positions) if workflow_positions else -1
    return first_workflow == -1 or first_raw < first_workflow


def _invented_cli_unavailable_validation_commands(result: dict[str, Any]) -> bool:
    text = _scored_agent_response_text(result)
    if not text.strip():
        text = str(result.get("stdout") or "")
    normalized = text.lower()
    if "validation command" not in normalized:
        return False
    if re.search(r"validation commands?\s+(?:are|is)\s+unavailable until|unavailable until the command can run", normalized):
        return False
    substitute_markers = (
        "`grep",
        "`rg",
        "`read_file",
        "`get-content",
        "`cat",
        "`ls",
        "grep ",
        "rg ",
        "read_file",
        "get-content",
    )
    return any(marker in normalized for marker in substitute_markers)


def _is_diagnostic_command_output(path: str) -> bool:
    name = Path(path.replace("\\", "/")).name.lower()
    return bool(re.fullmatch(r"summary(?:[_-]full|[_-]?\d*)?\.json", name))


def _created_execplans_without_state_registration(mutation_summary: dict[str, Any] | None) -> list[str]:
    if not isinstance(mutation_summary, dict):
        return []
    created = [path for path in mutation_summary.get("created", []) if isinstance(path, str)]
    changed = _changed_paths(mutation_summary)
    state_changed = ".agentic-workspace/planning/state.toml" in changed
    execplans = [
        path.replace("\\", "/")
        for path in created
        if path.replace("\\", "/").startswith(".agentic-workspace/planning/execplans/") and path.replace("\\", "/").endswith(".plan.json")
    ]
    return [] if state_changed else execplans


def _mentioned_workspace_paths(text: str) -> list[str]:
    matches = re.findall(r"\.agentic-workspace/[A-Za-z0-9_./*-]+", text.replace("\\", "/"))
    normalized: list[str] = []
    for match in matches:
        path = match.rstrip(".,;:)'\"`]")
        if "*" in path:
            continue
        normalized.append(path)
    return sorted(dict.fromkeys(normalized))


def _missing_mentioned_paths(*, text: str, repo_path: Path, prefix: str | None = None) -> list[str]:
    missing: list[str] = []
    for mentioned in _mentioned_workspace_paths(text):
        if prefix and not mentioned.startswith(prefix):
            continue
        if not (repo_path / mentioned).exists():
            missing.append(mentioned)
    return missing


def _string_list(value: Any, *, field: str, scenario_id: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"scenario '{scenario_id}' {field} must be a string list")
    return value


def _metadata_workflow_warnings(
    *,
    scenario: dict[str, Any],
    result: dict[str, Any],
    mutation_summary: dict[str, Any] | None,
    repo_path: Path,
) -> list[dict[str, str]]:
    scenario_id = str(scenario.get("id", "<unknown>"))
    changed_paths = _changed_paths(mutation_summary)
    final_response_lower = _strip_local_path_targets_for_scoring(_scored_agent_response_text(result)).lower()
    full_response_lower = _full_response_text(result).lower()
    warnings: list[dict[str, str]] = []
    if _provider_did_not_run(result):
        return warnings
    adapter_could_not_execute_workspace_command = _agentic_workspace_tooling_unavailable(result)

    def add(message: str, *, evidence: str = "") -> None:
        warning: dict[str, str] = {
            "warning_class": "model_cli_metadata_scoring_failure",
            "message": message,
        }
        if evidence:
            warning["evidence"] = evidence
        warnings.append(warning)

    allowed_write_patterns = _string_list(scenario.get("allowed_write_patterns"), field="allowed_write_patterns", scenario_id=scenario_id)
    ignored_write_patterns = _string_list(scenario.get("ignored_write_patterns"), field="ignored_write_patterns", scenario_id=scenario_id)
    forbidden_write_patterns = _string_list(
        scenario.get("forbidden_write_patterns"), field="forbidden_write_patterns", scenario_id=scenario_id
    )
    scored_changed_paths = [path for path in changed_paths if not _matches_any(path, ignored_write_patterns)]
    if allowed_write_patterns:
        unexpected = [path for path in scored_changed_paths if not _matches_any(path, allowed_write_patterns)]
        if unexpected:
            add("The agent changed files outside the scenario's allowed write patterns.", evidence=", ".join(unexpected[:12]))
    if forbidden_write_patterns:
        forbidden = [path for path in scored_changed_paths if _matches_any(path, forbidden_write_patterns)]
        if forbidden:
            add("The agent changed files matching the scenario's forbidden write patterns.", evidence=", ".join(forbidden[:12]))

    no_workspace_baseline = bool(scenario.get("no_agentic_workspace_baseline", False))
    if no_workspace_baseline:
        if (repo_path / ".agentic-workspace").exists():
            add("The no-AW baseline fixture contains an `.agentic-workspace` directory.")
        agents_path = repo_path / "AGENTS.md"
        if not agents_path.exists():
            add("The no-AW baseline fixture lacks explicit plain-repo agent instructions.")
        elif "does not use agentic workspace" not in agents_path.read_text(encoding="utf-8", errors="replace").lower():
            add("The no-AW baseline fixture does not explicitly say the repo does not use Agentic Workspace.")

    for required in _string_list(
        scenario.get("required_command_mentions"),
        field="required_command_mentions",
        scenario_id=scenario_id,
    ):
        if not _contains_required_signal(full_response_lower, required):
            add("The agent did not report a required command or workflow surface.", evidence=required)
    executed_command_text = _normalized_command_text(_executed_command_text(result))
    for required in _string_list(
        scenario.get("required_executed_commands"),
        field="required_executed_commands",
        scenario_id=scenario_id,
    ):
        if not _command_requirement_satisfied(required=required, executed_command_text=executed_command_text):
            if adapter_could_not_execute_workspace_command and "agentic-workspace" in required:
                continue
            add("The agent did not execute a required command.", evidence=required)
    for forbidden in _string_list(
        scenario.get("forbidden_executed_commands"),
        field="forbidden_executed_commands",
        scenario_id=scenario_id,
    ):
        if _command_requirement_satisfied(required=forbidden, executed_command_text=executed_command_text):
            add("The agent executed a command this scenario marks as avoidable or forbidden.", evidence=forbidden)
    if no_workspace_baseline and any(
        command in executed_command_text
        for command in (
            "agentic-workspace",
            "agentic-planning",
            "repo-planning",
            "repo-memory",
        )
    ):
        add(
            "The no-AW baseline was contaminated by Agentic Workspace command usage.",
            evidence="agentic-workspace/agentic-planning command observed",
        )
    for forbidden in _string_list(
        scenario.get("forbidden_response_phrases"),
        field="forbidden_response_phrases",
        scenario_id=scenario_id,
    ):
        if _contains_forbidden_phrase(final_response_lower, forbidden):
            add("The agent reported a forbidden response phrase for this scenario.", evidence=forbidden)
    local_path_evidence = _local_absolute_path_evidence(_scored_agent_response_text(result))
    if local_path_evidence:
        warnings.append(
            {
                "warning_class": "model_cli_local_path_leak",
                "message": "The agent exposed a local absolute path in the final response.",
                "evidence": local_path_evidence,
                "owner_surface": "harness",
                "failure_id": "LOCAL_ABSOLUTE_PATH_LEAK",
                "remediation_ref": "#1616",
            }
        )
    for pattern in _string_list(
        scenario.get("required_artifact_patterns"),
        field="required_artifact_patterns",
        scenario_id=scenario_id,
    ):
        if not any(repo_path.glob(pattern)):
            add("The scenario's required artifact pattern was not present after the run.", evidence=pattern)

    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for warning in warnings:
        key = (warning["warning_class"], warning["message"], warning.get("evidence", ""))
        if key not in seen:
            deduped.append(warning)
            seen.add(key)
    return deduped


def _local_absolute_path_evidence(text: str) -> str:
    if not text:
        return ""
    for pattern in _LOCAL_ABSOLUTE_PATH_PATTERNS:
        match = pattern.search(text)
        if match:
            evidence = match.group(0)
            return evidence[:160]
    return ""


def _executed_command_text(result: dict[str, Any]) -> str:
    command_fragments: list[str] = []
    for source in (result.get("stdout"), result.get("stderr"), result.get("final_message")):
        if not isinstance(source, str):
            continue
        command_fragments.extend(_copilot_markdown_shell_commands(source))
        command_fragments.extend(_copilot_plain_shell_commands(source))
        for event in _json_objects_from_lines(source):
            command = event.get("command")
            if isinstance(command, str):
                command_fragments.append(command)
            item = event.get("item")
            if isinstance(item, dict):
                item_command = item.get("command")
                if isinstance(item_command, str):
                    command_fragments.append(item_command)
        payload = _json_document(source)
        if payload is None:
            continue
        if isinstance(payload, dict):
            response = payload.get("response")
            stats = payload.get("stats")
            if isinstance(stats, dict):
                tools = stats.get("tools")
                if isinstance(tools, dict):
                    by_name = tools.get("byName")
                    if isinstance(by_name, dict):
                        command_fragments.extend(str(name) for name in by_name)
                        if "run_shell_command" in by_name and isinstance(response, str):
                            command_fragments.append(response)
    return "\n".join(command_fragments)


def _copilot_plain_shell_commands(text: str) -> list[str]:
    commands: list[str] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not re.match(r"^[●✗]\s+.*\((?:shell|powershell|bash|cmd)\)\s*$", line):
            index += 1
            continue
        index += 1
        command_parts: list[str] = []
        while index < len(lines):
            body_line = lines[index]
            if re.match(r"^[●✗]\s+", body_line) or re.match(r"^\s*└", body_line):
                break
            command_match = re.match(r"^\s*│\s?(?P<part>.*)$", body_line)
            if command_match:
                part = command_match.group("part").strip()
                if part:
                    command_parts.append(part)
            index += 1
        if command_parts:
            commands.append(" ".join(command_parts))
    return commands


def _copilot_markdown_shell_commands(text: str) -> list[str]:
    commands: list[str] = []
    tool_block_pattern = re.compile(
        r"^###\s+[^\n]*`(?P<tool>powershell|shell|bash|cmd)`\s*$"
        r"(?P<body>.*?)(?=^---\s*$|^###\s+|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    for match in tool_block_pattern.finditer(text):
        body = match.group("body")
        args_match = re.search(r"```json\s*(?P<payload>\{.*?\})\s*```", body, flags=re.DOTALL)
        if not args_match:
            continue
        try:
            payload = json.loads(args_match.group("payload"))
        except json.JSONDecodeError:
            continue
        command = payload.get("command")
        if isinstance(command, str) and command.strip():
            commands.append(command)
    return commands


def _quality_signals(
    *,
    scenario_id: str,
    mutation_summary: dict[str, Any] | None,
    warnings: list[dict[str, Any]],
    result: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    if not isinstance(mutation_summary, dict) or mutation_summary.get("status") == "not-run":
        return []
    changed_paths = _changed_paths(mutation_summary)
    warning_messages = "\n".join(str(warning.get("message", "")) for warning in warnings).lower()
    canonical_planning = [
        path
        for path in changed_paths
        if path.startswith(".agentic-workspace/planning/execplans/")
        or path.startswith(".agentic-workspace/planning/decompositions/")
        or path == ".agentic-workspace/planning/state.toml"
    ]
    non_planning_changes = [path for path in changed_paths if not path.startswith(".agentic-workspace/planning/")]
    signals: list[dict[str, str]] = []
    signals.extend(
        _read_surface_quality_signals(
            scenario_id=scenario_id,
            result=result or {},
            warnings=warnings,
        )
    )
    if scenario_id == "direct-task-minimal-overhead":
        direct_only = bool(changed_paths) and all(path == "README.md" for path in changed_paths)
        signals.append(
            {
                "id": "direct_task_stayed_direct",
                "status": "satisfied" if direct_only and "direct wording edit" not in warning_messages else "weak",
                "evidence": ", ".join(changed_paths) or "no mutation captured",
            }
        )
    if scenario_id == "broad-work-decomposition":
        diagnostic_outputs = [path for path in non_planning_changes if _is_diagnostic_command_output(path)]
        product_or_handoff_changes = [path for path in non_planning_changes if path not in diagnostic_outputs]
        signals.append(
            {
                "id": "broad_task_created_durable_planning",
                "status": "satisfied" if canonical_planning else "weak",
                "evidence": ", ".join(canonical_planning) or "no canonical planning artifact captured",
            }
        )
        signals.append(
            {
                "id": "planning_only_avoided_product_scaffold",
                "status": "satisfied" if not product_or_handoff_changes else "weak",
                "evidence": ", ".join(product_or_handoff_changes) or "no product or handoff files changed",
            }
        )
        if diagnostic_outputs:
            signals.append(
                {
                    "id": "diagnostic_output_not_persisted",
                    "status": "weak",
                    "evidence": ", ".join(diagnostic_outputs),
                }
            )
        else:
            signals.append(
                {
                    "id": "diagnostic_output_not_persisted",
                    "status": "satisfied",
                    "evidence": "no summary output files changed",
                }
            )
    if scenario_id in {"planning-artifact-integrity", "native-plan-bridge"}:
        unregistered_execplans = _created_execplans_without_state_registration(mutation_summary)
        signals.append(
            {
                "id": "durable_decision_uses_canonical_surface",
                "status": "satisfied"
                if canonical_planning and not unregistered_execplans and "outside canonical" not in warning_messages
                else "weak",
                "evidence": ", ".join(canonical_planning) or "no canonical planning artifact captured",
            }
        )
    return signals


def _read_surface_quality_signals(
    *,
    scenario_id: str,
    result: dict[str, Any],
    warnings: list[dict[str, Any]],
) -> list[dict[str, str]]:
    executed = _normalized_command_text(_executed_command_text(result))
    response = _full_response_text(result).lower()
    warning_text = "\n".join(str(warning.get("message", "")) for warning in warnings).lower()
    used_start = "agentic-workspace start" in executed or "agentic-workspace start" in response
    used_implement = "agentic-workspace implement" in executed or "agentic-workspace implement" in response
    used_summary = "agentic-workspace summary" in executed or "agentic-workspace summary" in response
    used_full = "--verbose" in executed or "--verbose" in response
    raw_workspace_reads = len(re.findall(r"\.agentic-workspace/(?:planning|memory|docs|workflow|config)", response))
    signals: list[dict[str, str]] = [
        {
            "id": "read_surface_entrypoint_used",
            "status": "satisfied" if used_start or used_implement or used_summary else "weak",
            "evidence": "start/implement/summary observed"
            if used_start or used_implement or used_summary
            else "no package routing command observed",
        }
    ]
    if scenario_id == "direct-task-minimal-overhead":
        over_read = used_summary or used_full or raw_workspace_reads > 2
        signals.append(
            {
                "id": "read_surface_over_read",
                "status": "weak" if over_read else "satisfied",
                "evidence": f"summary={used_summary}; full={used_full}; raw_workspace_mentions={raw_workspace_reads}",
            }
        )
    else:
        unclear = "did not report" in warning_text or "not report" in warning_text
        raw_before_fallback = "raw workspace before fallback" in warning_text or "raw planning surfaces before" in warning_text
        signals.append(
            {
                "id": "read_surface_under_read",
                "status": "weak"
                if raw_before_fallback or (unclear and not (used_start or used_implement or used_summary))
                else "satisfied",
                "evidence": (
                    "raw Planning surface was inspected before fallback workflow"
                    if raw_before_fallback
                    else "warnings suggested missing workflow evidence"
                    if unclear
                    else "no missing-workflow warning signal"
                ),
            }
        )
        signals.append(
            {
                "id": "read_surface_detail_escalation",
                "status": "satisfied" if used_full or not used_summary else "neutral",
                "evidence": "full/detail context used or broad summary not needed",
            }
        )
    return signals


def _postmortem_feedback_prompt(*, scenario: dict[str, Any], invocation: dict[str, Any]) -> str:
    result = invocation.get("result", {})
    if not isinstance(result, dict):
        result = {}
    mutation_summary = invocation.get("mutation_summary", {})
    warnings = invocation.get("warnings", [])
    final_message = _response_text(result)[-700:]
    warning_messages = []
    if isinstance(warnings, list):
        for warning in warnings[:6]:
            if isinstance(warning, dict):
                message = str(warning.get("message") or warning.get("warning_class") or "").strip()
                evidence = str(warning.get("evidence") or "").strip()
                warning_messages.append(f"{message} ({evidence})" if evidence else message)
    warning_text = "; ".join(message for message in warning_messages if message) or "none"
    if isinstance(mutation_summary, dict):
        mutation_bits = [
            f"status={mutation_summary.get('status', 'unknown')}",
            f"created={mutation_summary.get('created_count', 0)}",
            f"modified={mutation_summary.get('modified_count', 0)}",
            f"deleted={mutation_summary.get('deleted_count', 0)}",
        ]
        mutation_text = ", ".join(mutation_bits)
    else:
        mutation_text = "status=unknown"
    original_prompt = str(invocation.get("prompt", "")).split("\n\nRepository startup instruction", maxsplit=1)[0]
    if len(original_prompt) > 350:
        original_prompt = original_prompt[:350].rstrip() + "..."
    questions = scenario.get("postmortem_feedback_questions")
    if not isinstance(questions, list) or not questions:
        questions = [
            "Why did you choose the workflow and commands you used?",
            "What was ambiguous, missing, or more verbose than necessary?",
            "What package output, instruction, or command would have made the correct next step more obvious?",
            "What would have reduced token usage without reducing safety or proof quality?",
            "Did the package make you read too much, too little, or the right amount for this task?",
        ]
    question_lines = "\n".join(f"- {question}" for question in questions if str(question).strip())
    return (
        "TASK: Analyze a completed model-run transcript from the evidence below.\n"
        "This is not a repository task. Do not run startup commands, inspect paths, read files, search, or edit.\n"
        "If the evidence mentions commands or files, discuss those choices only; do not execute or inspect them.\n\n"
        "EVIDENCE BLOCK START\n"
        f"Scenario: {invocation.get('scenario_id', '')} / {invocation.get('prompt_variant_id', '')}\n"
        f"Warnings: {warning_text}\n"
        f"Mutation: {mutation_text}\n"
        f"Final answer excerpt: {final_message or 'none'}\n"
        f"Scenario prompt excerpt: {original_prompt or 'none'}\n"
        "EVIDENCE BLOCK END\n\n"
        "Use only the evidence block above. The evidence block is complete for this analysis. "
        "If a field says none or missing, name that field instead of looking elsewhere.\n\n"
        "Answer these questions:\n"
        f"{question_lines}\n\n"
        "Keep the answer under 200 words. Separate model/provider limitations from product or harness improvements."
    )


def _postmortem_feedback_warnings(*, result: dict[str, Any]) -> list[dict[str, str]]:
    response = _full_response_text(result).lower()
    warnings: list[dict[str, str]] = []

    def add(message: str, *, evidence: str = "") -> None:
        warning: dict[str, str] = {
            "warning_class": "model_cli_postmortem_feedback_failure",
            "message": message,
        }
        if evidence:
            warning["evidence"] = evidence
        warnings.append(warning)

    if any(marker in response for marker in ("evidence block is missing", "provide the complete evidence", "provide these directly")):
        add("The postmortem agent claimed supplied evidence was missing.")
    inspection_markers = (
        "● read ",
        "● list directory",
        "● search ",
        "shell)",
        "permission denied",
        "get-childitem",
    )
    if any(marker in response for marker in inspection_markers):
        add("The postmortem agent inspected files or attempted commands despite the no-inspection rule.")
    return warnings


def _semantic_workflow_warnings(
    *,
    scenario_id: str,
    prompt_variant_id: str | None = None,
    result: dict[str, Any],
    mutation_summary: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    if result.get("returncode") not in (None, 0) and not str(result.get("final_message") or result.get("stdout") or "").strip():
        return []
    response = _response_text(result)
    response_lower = response.lower()
    full_response_lower = _full_response_text(result).lower()
    full_response_path_normalized = full_response_lower.replace("\\", "/")
    warnings: list[dict[str, str]] = []

    def add(message: str, *, evidence: str = "") -> None:
        warning: dict[str, str] = {
            "warning_class": "model_cli_semantic_workflow_failure",
            "message": message,
        }
        if evidence:
            warning["evidence"] = evidence
        warnings.append(warning)

    if scenario_id == "startup-orientation":
        if ".agentic-workspace/workflow.md" in response_lower and any(
            fragment in response_lower
            for fragment in (
                "not accessible",
                "cannot access",
                "permission restrictions",
                "no `.agentic-workspace`",
                "no .agentic-workspace",
            )
        ):
            add("The agent treated the workspace startup surface as unavailable instead of using the copied fixture surfaces.")

    if scenario_id == "cli-discovery-before-planning":
        runtime_native_markers = ("/plan", "shift+tab", "ctrl+x", "plan mode")
        if any(marker in response_lower for marker in runtime_native_markers):
            add("The agent reported runtime-native planning commands among verified Agentic Workspace CLI commands.")
        if "agentic-workspace --help" not in response_lower and "agentic-workspace planning" not in response_lower:
            add("The agent did not report verifying Agentic Workspace CLI help before naming planning commands.")

    planning_only_scenario = scenario_id in {
        "planning-artifact-integrity",
        "broad-work-decomposition",
        "native-plan-bridge",
    } or scenario_id.endswith("-handoff-aw")

    if planning_only_scenario:
        created = mutation_summary.get("created", []) if isinstance(mutation_summary, dict) else []
        deleted = mutation_summary.get("deleted", []) if isinstance(mutation_summary, dict) else []
        deleted_templates = [
            path
            for path in deleted
            if isinstance(path, str)
            and path.replace("\\", "/").startswith(".agentic-workspace/planning/")
            and "/TEMPLATE." in path.replace("\\", "/")
        ]
        if deleted_templates:
            add(
                "The agent deleted shipped planning templates instead of copying them to task-specific records.",
                evidence=", ".join(deleted_templates[:8]),
            )
        misplaced = [path for path in created if isinstance(path, str) and _created_path_is_misplaced_planning_artifact(path)]
        if misplaced:
            add(
                "The agent created likely planning artifacts outside canonical Agentic Workspace planning surfaces.",
                evidence=", ".join(misplaced),
            )
        side_docs = [path for path in created if isinstance(path, str) and _created_path_is_planning_only_side_doc(path)]
        if side_docs:
            add(
                "The agent created separate architecture or handoff docs during planning-only preparation instead of keeping that content in Planning records.",
                evidence=", ".join(side_docs[:8]),
            )
        unregistered_execplans = _created_execplans_without_state_registration(mutation_summary)
        if unregistered_execplans:
            add(
                "The agent created canonical execplan files without registering them in planning state.",
                evidence=", ".join(unregistered_execplans[:8]),
            )
        if "agentic-planning promote-lane" in response_lower:
            add("The agent recommended unsupported planning lifecycle command `agentic-planning promote-lane`.")
        if scenario_id == "planning-artifact-integrity":
            missing_planning_refs = _missing_mentioned_paths(
                text=response,
                repo_path=Path(result.get("cwd") or "."),
                prefix=".agentic-workspace/planning/execplans/",
            )
            if missing_planning_refs and any(
                marker in response_lower
                for marker in (
                    "all referenced paths are valid",
                    "references only files that exist",
                    "next action references only files that exist",
                )
            ):
                add(
                    "The agent claimed next-action planning references were valid while naming missing execplan files.",
                    evidence=", ".join(missing_planning_refs[:8]),
                )
        if scenario_id == "broad-work-decomposition" or scenario_id.endswith("-handoff-aw"):
            modified = mutation_summary.get("modified", []) if isinstance(mutation_summary, dict) else []
            product_files = [
                path
                for path in [*created, *modified]
                if isinstance(path, str)
                and not path.replace("\\", "/").startswith(".agentic-workspace/planning/")
                and not _is_diagnostic_command_output(path)
                and path.replace("\\", "/") not in {"TODO.md", "ROADMAP.md"}
            ]
            if product_files:
                add(
                    "The agent created product or handoff files during a planning-only broad-work preparation scenario.",
                    evidence=", ".join(product_files[:8]),
                )
            diagnostic_outputs = [path for path in [*created, *modified] if isinstance(path, str) and _is_diagnostic_command_output(path)]
            if diagnostic_outputs:
                add(
                    "The agent persisted diagnostic command output in the repository instead of keeping it in the transcript.",
                    evidence=", ".join(diagnostic_outputs[:8]),
                )
            canonical_planning_created = [
                path
                for path in created
                if isinstance(path, str)
                and (
                    path.replace("\\", "/").startswith(".agentic-workspace/planning/execplans/")
                    or path.replace("\\", "/").startswith(".agentic-workspace/planning/decompositions/")
                    or path.replace("\\", "/") == ".agentic-workspace/planning/state.toml"
                )
            ]
            proposal_markers = ("i'll wait", "i will wait", "proposed strategy", "please let me know", "before drafting")
            if not canonical_planning_created and any(marker in response_lower for marker in proposal_markers):
                add("The agent left broad preparation as a proposal instead of creating durable repo-visible planning state.")
            if ".agentic-workspace/planning/records/" in response_lower:
                add("The agent routed durable planning to non-canonical `.agentic-workspace/planning/records/`.")
        if scenario_id == "planning-artifact-integrity" and any(
            fragment in response_lower
            for fragment in (
                "no automatic summary warnings could be generated",
                "no specific cli tool available",
                "could not be generated or inspected",
            )
        ):
            add("The agent claimed planning summary inspection was unavailable instead of running Agentic Workspace summary.")
        if scenario_id == "planning-artifact-integrity" and "agentic-workspace summary" not in full_response_lower:
            add("The agent did not report running `agentic-workspace summary` after creating planning state.")

    if scenario_id == "direct-task-minimal-overhead":
        created = mutation_summary.get("created", []) if isinstance(mutation_summary, dict) else []
        planning_created = [
            path for path in created if isinstance(path, str) and path.replace("\\", "/").startswith(".agentic-workspace/planning/")
        ]
        if planning_created:
            add(
                "The agent created planning artifacts for a direct wording edit where workspace overhead should stay minimal.",
                evidence=", ".join(planning_created),
            )
        if (
            any(marker in response_lower for marker in ("execplan", "decomposition", "epic", "lane"))
            and "README.md".lower() not in response_lower
        ):
            add("The agent appeared to escalate a direct wording edit into planning-shaped work.")

    if scenario_id == "native-plan-bridge":
        modified = mutation_summary.get("modified", []) if isinstance(mutation_summary, dict) else []
        workflow_modified = [
            path for path in modified if isinstance(path, str) and path.replace("\\", "/") == ".agentic-workspace/WORKFLOW.md"
        ]
        if workflow_modified:
            add(
                "The agent modified workflow instructions instead of leaving durable execution state for future agents.",
                evidence=", ".join(workflow_modified),
            )
        created = mutation_summary.get("created", []) if isinstance(mutation_summary, dict) else []
        freehand = [path for path in created if isinstance(path, str) and _created_path_is_misplaced_planning_artifact(path)]
        if freehand:
            add(
                "The agent created a freehand planning or handoff artifact instead of using canonical repo workflow surfaces.",
                evidence=", ".join(freehand),
            )
        if any(marker in response_lower for marker in ("/plan", "todo", "task list", "private plan")) and not any(
            marker in response_lower
            for marker in (
                ".agentic-workspace/planning",
                "agentic workspace planning",
                "checked-in workspace planning",
                "repo-shared",
            )
        ):
            add("The agent used or described runtime-native planning without clearly bridging durable decisions to Agentic Workspace.")

    if scenario_id == "invalid-planning-recovery":
        if "agentic-workspace summary" not in response_lower and "planning_surface_health" not in response_lower:
            add("The agent did not report using Agentic Workspace summary diagnostics before recommending recovery.")
        normalized_response = response_lower.replace("\\", "/")
        if (
            "execplans = []" in response_lower
            or "remove-item" in response_lower
            or "rm .agentic-workspace/planning" in normalized_response
            or "rm -r .agentic-workspace/planning" in normalized_response
        ):
            add("The agent recommended manual planning-state clearing before using an explicit package recovery path.")
        destructive_vcs_markers = ("git restore .", "git reset --hard", "git checkout -- .")
        if any(marker in response_lower for marker in destructive_vcs_markers):
            add("The agent recommended destructive VCS cleanup instead of planning-state recovery diagnostics.")
        false_safe_markers = (
            "safe to proceed",
            "safely proceed",
            "no recovery command needed",
            "working as intended",
            "safe to continue",
        )
        safe_claim = any(re.search(rf"(?<!not )(?:{re.escape(marker)})", response_lower) for marker in false_safe_markers)
        if safe_claim and "unsupported" not in response_lower:
            add("The agent reported invalid planning state as safe instead of identifying the unsupported planning shape.")

    if scenario_id == "capability-fit-routing":
        created = mutation_summary.get("created", []) if isinstance(mutation_summary, dict) else []
        modified = mutation_summary.get("modified", []) if isinstance(mutation_summary, dict) else []
        deleted = mutation_summary.get("deleted", []) if isinstance(mutation_summary, dict) else []
        changed_paths = [
            path for path in [*created, *modified, *deleted] if isinstance(path, str) and not _is_diagnostic_command_output(path)
        ]
        if changed_paths:
            add(
                "The agent edited files during a no-edit capability-fit routing scenario.",
                evidence=", ".join(changed_paths[:8]),
            )
        variant = prompt_variant_id or ""
        escalation_markers = (
            "escalat",
            "stronger planner",
            "strong planner",
            "handoff",
            "manual review",
            "not safe",
            "cannot safely",
            "should not implement",
            "must not implement",
            "ask the human",
        )
        inspection_markers = (
            "inspect",
            "proof",
            "authority",
            "changed path",
            "summary",
            "preflight",
            "context",
        )
        direct_implementation_markers = (
            "i will implement",
            "i'll implement",
            "i can implement",
            "i would implement",
            "implement directly",
            "proceed with implementation",
            "start coding",
        )
        downroute_markers = (
            "down-route",
            "down route",
            "delegate",
            "cheaper",
            "bounded executor",
            "lesser",
            "weaker",
            "mechanical",
            "token",
        )
        stay_direct_without_route_markers = (
            "no configured",
            "no cheaper",
            "no safe",
            "not configured",
            "stay local because",
        )
        if variant == "weak-target-high-judgment":
            if not any(marker in response_lower for marker in escalation_markers):
                add("The weak-target variant did not make escalation or handoff the safe action for high-judgment work.")
            if any(marker in response_lower for marker in direct_implementation_markers) and not any(
                marker in response_lower for marker in escalation_markers
            ):
                add("The weak-target variant offered direct implementation without an escalation guardrail.")
        if variant == "weak-target-ambiguous-inspection":
            if not any(marker in response_lower for marker in inspection_markers):
                add("The weak ambiguous variant did not require inspection before deciding capability fit.")
            if not any(marker in response_lower for marker in escalation_markers):
                add("The weak ambiguous variant did not preserve escalation or compact handoff as the safe route.")
            if any(marker in response_lower for marker in direct_implementation_markers) and not any(
                marker in response_lower for marker in escalation_markers
            ):
                add("The weak ambiguous variant offered direct implementation before inspection and escalation routing.")
        if variant == "strong-target-mechanical":
            if not any(marker in response_lower for marker in downroute_markers):
                add("The strong-target variant did not consider down-routing safe mechanical work to a cheaper fit.")
            if "keep the strong" in response_lower and not any(marker in response_lower for marker in stay_direct_without_route_markers):
                add("The strong-target variant kept strong-agent budget without a no-safe-route justification.")
        if variant == "strong-target-mechanical-unclear-proof":
            if not any(marker in response_lower for marker in inspection_markers):
                add("The unclear-proof variant did not require proof/source-authority inspection before down-routing.")
            if any(marker in response_lower for marker in downroute_markers) and not any(
                marker in response_lower for marker in inspection_markers
            ):
                add("The unclear-proof variant down-routed without proof or generated-source guardrails.")
        if variant == "post-run-self-review":
            review_markers = ("why", "because", "evidence", "prevent", "future", "trust", "guardrail")
            if not any(marker in response_lower for marker in review_markers):
                add("The post-run review variant did not ask for rationale, evidence, or prevention signals.")
            if "everything is fine" in response_lower and not any(
                marker in response_lower for marker in ("lower trust", "low trust", "not trust")
            ):
                add("The post-run review variant accepted weak-agent confidence without trust qualification.")
        if variant == "handoff-packet-contents":
            packet_markers = (
                "intent",
                "constraint",
                "read",
                "scope",
                "proof",
                "stop",
                "return",
                "posture",
            )
            missing = [marker for marker in packet_markers if marker not in response_lower]
            if missing:
                add(
                    "The handoff packet variant omitted key worker-packet fields.",
                    evidence=", ".join(missing),
                )

    if scenario_id in {"config-closeout-obligation", "local-delegation-posture", "config-output-posture"}:
        if "agentic-workspace config" not in full_response_lower and ".agentic-workspace/config" not in full_response_lower:
            add("The agent answered a config-sensitive scenario without reporting use of the effective config surface.")
        generic_config_markers = (
            "based on general best practices",
            "assuming default",
            "i assume",
            "should probably",
            "without seeing",
        )
        if any(marker in response_lower for marker in generic_config_markers) and "agentic-workspace config" not in full_response_lower:
            add("The agent relied on generic assumptions where repo/local config should provide the answer.")
        if scenario_id == "config-closeout-obligation":
            created = mutation_summary.get("created", []) if isinstance(mutation_summary, dict) else []
            planning_created = [
                path for path in created if isinstance(path, str) and path.replace("\\", "/").startswith(".agentic-workspace/planning/")
            ]
            if planning_created:
                add(
                    "The agent created planning artifacts for a direct config-closeout wording edit.",
                    evidence=", ".join(planning_created[:8]),
                )
        if scenario_id == "local-delegation-posture":
            if "config.local" not in full_response_lower and "local-override" not in full_response_lower:
                add("The agent did not identify local config as the authority for delegation posture.")
            if any(marker in response_lower for marker in ("auto-delegate", "automatically delegate", "spawn", "hand off now")) and not any(
                marker in response_lower
                for marker in ("not permitted", "disabled", "manual", "suggest", "human", "safe_to_auto_run_commands")
            ):
                add("The agent treated delegation as executable despite local safety controls.")
        if scenario_id == "config-output-posture":
            if "execution method" in response_lower and "must not" not in response_lower and "does not" not in response_lower:
                add("The agent blurred output-posture settings into execution-method control.")

    if scenario_id == "intent-satisfaction-review":
        is_vague_intent_variant = prompt_variant_id in {"vague-outcome-trust", "vague-outcome-less-rework"}
        distinction_markers = (
            "validation",
            "proof",
            "tests",
            "intent",
            "larger",
            "durable",
            "residue",
            "follow-up",
            "follow up",
        )
        if not is_vague_intent_variant and sum(1 for marker in distinction_markers if marker in response_lower) < 4:
            add("The agent did not clearly separate proof, local completion, larger intent, and residue/follow-up.")
        full_satisfaction_markers = (
            "fully satisfied",
            "original intent is satisfied",
            "intent is satisfied",
            "no follow-up",
            "no follow up",
            "nothing else",
            "complete",
        )
        partial_markers = (
            "partial",
            "partially",
            "not fully",
            "not enough",
            "not satisfied",
            "follow-up",
            "follow up",
            "repo-visible",
            "planning",
            "issue",
        )
        if (
            not is_vague_intent_variant
            and any(marker in response_lower for marker in full_satisfaction_markers)
            and not any(marker in response_lower for marker in partial_markers)
        ):
            add("The agent treated local proof or a narrow wording change as full satisfaction of the broader human intent.")
        if "tests passed" in response_lower and "intent" not in response_lower:
            add("The agent reported validation proof without judging whether the original intent was satisfied.")
        if prompt_variant_id == "passed-tests-partial-intent" and not any(marker in response_lower for marker in partial_markers):
            add("The partial-intent variant did not route the broader docs/product-positioning intent to follow-up.")
        if is_vague_intent_variant:
            outcome_markers = ("intended outcome", "intent", "goal", "trust", "rework", "handoff", "preserve")
            inspect_markers = ("inspect", "preflight", "summary", "report", "config", "planning", "memory", "closeout")
            satisfaction_markers = ("satisfied", "done when", "know", "evidence", "criteria", "proof", "measure")
            compact_command_markers = (
                "agentic-workspace preflight",
                "agentic-workspace start",
                "agentic-workspace defaults",
                "agentic-workspace summary",
                "agentic-workspace config",
                "agentic-workspace skills",
            )
            raw_workspace_markers = (
                ".agentic-workspace/workflow.md",
                ".agentic-workspace/planning/schemas/",
                ".agentic-workspace/planning/state.toml",
                "planning-review.schema.json",
                "planning-external-intent-evidence.schema.json",
                "planning-finished-work-evidence.schema.json",
            )
            solution_markers = (
                "i will implement",
                "i'll implement",
                "implement now",
                "edit ",
                "change the readme",
                "add a doc",
                "create a script",
                "write code",
            )
            if not any(marker in response_lower for marker in outcome_markers):
                add("The vague-outcome variant did not restate the intended outcome before choosing next actions.")
            if not any(marker in response_lower for marker in inspect_markers):
                add("The vague-outcome variant did not name the first repo-visible surface to inspect.")
            if not any(marker in response_lower for marker in satisfaction_markers):
                add("The vague-outcome variant did not define how satisfaction would be judged.")
            raw_marker_positions = [
                full_response_path_normalized.find(marker) for marker in raw_workspace_markers if marker in full_response_path_normalized
            ]
            compact_marker_positions = [
                full_response_lower.find(marker) for marker in compact_command_markers if marker in full_response_lower
            ]
            first_raw_marker = min(raw_marker_positions) if raw_marker_positions else None
            first_compact_marker = min(compact_marker_positions) if compact_marker_positions else None
            if first_raw_marker is not None and (first_compact_marker is None or first_raw_marker < first_compact_marker):
                add("The vague-outcome variant inspected raw workspace files before using compact startup or summary surfaces.")
            if (
                any(marker in response_lower for marker in solution_markers)
                and "rather than" not in response_lower
                and "not jump" not in response_lower
            ):
                add("The vague-outcome variant jumped to a solution without preserving intent separately.")

    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for warning in warnings:
        key = (warning["warning_class"], warning["message"], warning.get("evidence", ""))
        if key not in seen:
            deduped.append(warning)
            seen.add(key)
    return deduped


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _execution_warnings(*, result: dict[str, Any], repo_path: Path, mutation_summary: dict[str, Any] | None = None) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    returncode = result.get("returncode")
    stdout = result.get("stdout")
    stderr = result.get("stderr")
    stdout_text = stdout if isinstance(stdout, str) else ""
    stderr_text = stderr if isinstance(stderr, str) else ""
    final_message_text = result.get("final_message") if isinstance(result.get("final_message"), str) else ""
    combined_text = f"{stdout_text}\n{stderr_text}\n{final_message_text}"
    if isinstance(returncode, int) and returncode != 0:
        warnings.append(
            {
                "warning_class": "model_cli_nonzero_exit",
                "message": f"The model CLI exited with status {returncode}.",
            }
        )
    if result.get("timed_out") or result.get("status") == "adapter_blocked":
        warnings.append(
            {
                "warning_class": "model_cli_adapter_blocked",
                "message": "The model CLI adapter timed out or could not produce a usable run result.",
            }
        )
    if result.get("status") == "runtime_failed":
        warnings.append(
            {
                "warning_class": "model_cli_runtime_failed",
                "message": "The model CLI process failed before producing usable model output.",
            }
        )
    if result.get("status") == "adapter_configuration_rejected" or _adapter_configuration_rejected(result):
        warnings.append(
            {
                "warning_class": "model_cli_adapter_configuration_rejected",
                "message": "The model CLI rejected the configured adapter/model options.",
            }
        )
    if result.get("capture_warning"):
        warnings.append(
            {
                "warning_class": "model_cli_output_capture_degraded",
                "message": str(result["capture_warning"]),
            }
        )
    if stdout is None:
        warnings.append(
            {
                "warning_class": "model_cli_stdout_missing",
                "message": "The model CLI result did not include captured stdout.",
            }
        )
    if "ModelNotFoundError" in combined_text or "Requested entity was not found" in combined_text:
        warnings.append(
            {
                "warning_class": "model_cli_model_not_found",
                "message": "The model provider rejected the configured model name.",
            }
        )
    if "AttachConsole failed" in combined_text:
        warnings.append(
            {
                "warning_class": "model_cli_runtime_stderr",
                "message": "The model CLI emitted AttachConsole failures on stderr.",
            }
        )
    if "GaxiosError" in combined_text or "Internal error encountered" in combined_text:
        warnings.append(
            {
                "warning_class": "model_cli_provider_error",
                "message": "The model CLI reported provider or API errors during execution.",
            }
        )
    if "Permission denied and could not request permission from user" in combined_text:
        warnings.append(
            {
                "warning_class": "model_cli_permission_denied",
                "message": "The model CLI attempted an operation outside its granted permissions.",
            }
        )
        if "agentic-workspace" in combined_text:
            warnings.append(
                {
                    "warning_class": "model_cli_adapter_tooling_limitation",
                    "message": "The model CLI could not execute an Agentic Workspace command through its tool layer.",
                }
            )
    if _agentic_workspace_tooling_unavailable(result):
        warnings.append(
            {
                "warning_class": "model_cli_adapter_tooling_limitation",
                "message": "The model CLI could not execute an Agentic Workspace command through its tool layer.",
            }
        )
        if _raw_planning_before_fallback_workflow(result):
            warnings.append(
                {
                    "warning_class": "model_cli_raw_workspace_before_fallback",
                    "message": "The model inspected raw Planning surfaces before using the fallback workflow after the workspace CLI was unavailable.",
                }
            )
        if _invented_cli_unavailable_validation_commands(result):
            warnings.append(
                {
                    "warning_class": "model_cli_cli_unavailable_substitute_validation",
                    "message": "The model invented substitute validation commands instead of reporting validation as unavailable until the workspace CLI can run.",
                }
            )
    if re.search(r"\b[A-Za-z]:\\temp\\", combined_text, flags=re.IGNORECASE):
        warnings.append(
            {
                "warning_class": "model_cli_external_output_attempt",
                "message": "The model CLI attempted to write temporary output outside the copied scenario repository.",
                "paths": "drive-root-temp",
            }
        )
    if mutation_summary and mutation_summary.get("status") == "changed":
        warnings.append(
            {
                "warning_class": "model_cli_fixture_mutation",
                "message": (
                    "The model CLI changed the copied scenario repository "
                    f"({mutation_summary.get('created_count', 0)} created, "
                    f"{mutation_summary.get('modified_count', 0)} modified, "
                    f"{mutation_summary.get('deleted_count', 0)} deleted)."
                ),
            }
        )
    failed_commands: list[str] = []
    for event in _json_objects_from_lines(stdout_text):
        event_text = json.dumps(event)
        if "pwsh.exe" in event_text and "not recognized" in event_text:
            warnings.append(
                {
                    "warning_class": "model_cli_shell_unavailable",
                    "message": "The model CLI could not run shell commands because pwsh.exe was unavailable.",
                }
            )
        item = event.get("item")
        if isinstance(item, dict) and item.get("type") == "command_execution":
            status = item.get("status")
            exit_code = item.get("exit_code")
            aggregated_output = item.get("aggregated_output")
            if status == "failed" or (isinstance(exit_code, int) and exit_code != 0):
                command = str(item.get("command", "<unknown command>"))
                evidence_parts = [command[:160]]
                if isinstance(exit_code, int):
                    evidence_parts.append(f"exit_code={exit_code}")
                if isinstance(aggregated_output, str) and aggregated_output.strip():
                    evidence_parts.append(aggregated_output.strip()[:160])
                failed_commands.append(" | ".join(evidence_parts))
        if event.get("type") != "result":
            continue
        usage = event.get("usage", {})
        if not isinstance(usage, dict):
            continue
        code_changes = usage.get("codeChanges", {})
        if not isinstance(code_changes, dict):
            continue
        modified = code_changes.get("filesModified", [])
        if not isinstance(modified, list):
            continue
        external_paths = [
            str(path) for item in modified if isinstance(item, str) for path in [Path(item)] if not _is_relative_to(path, repo_path)
        ]
        if external_paths:
            warnings.append(
                {
                    "warning_class": "model_cli_external_write",
                    "message": "The model CLI reported modified files outside the copied scenario repository.",
                    "paths": "; ".join(external_paths),
                }
            )
    if failed_commands:
        warnings.append(
            {
                "warning_class": "model_cli_command_execution_failed",
                "message": "The model CLI had failed command executions inside the run transcript.",
                "evidence": "; ".join(failed_commands[:3]),
            }
        )
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for warning in warnings:
        key = (warning["warning_class"], warning["message"])
        if key not in seen:
            deduped.append(warning)
            seen.add(key)
    return deduped


def _warning_key(warning: dict[str, Any]) -> str:
    return "|".join(str(warning.get(key, "")) for key in ("warning_class", "message", "evidence", "paths", "owner_surface", "failure_id"))


def _finding_base_classes(warning_key: str) -> list[str]:
    warning_class = warning_key.split("|", 1)[0]
    if warning_class in {
        "model_cli_provider_error",
        "model_cli_runtime_stderr",
        "model_cli_runtime_failed",
        "model_cli_adapter_tooling_limitation",
        "model_cli_adapter_blocked",
        "model_cli_adapter_configuration_rejected",
        "model_cli_permission_denied",
    }:
        return ["environment_or_provider"]
    if warning_class == "model_cli_local_path_leak":
        return ["ownership_boundary", "harness_owned"]
    return ["first_seen"]


def _classify_suite_findings(results: list[dict[str, Any]]) -> dict[str, Any]:
    occurrences: dict[str, list[dict[str, str]]] = {}
    for result in results:
        for warning in result.get("warnings", []):
            if not isinstance(warning, dict):
                continue
            if warning.get("warning_class") == "model_cli_fixture_mutation":
                continue
            occurrences.setdefault(_warning_key(warning), []).append(
                {
                    "scenario_id": str(result.get("scenario_id", "")),
                    "prompt_variant_id": str(result.get("prompt_variant_id", "default")),
                    "adapter_id": str(result.get("adapter_id", "")),
                    "model": str(result.get("model", "")),
                }
            )
    findings: list[dict[str, Any]] = []
    for key, refs in sorted(occurrences.items()):
        models = {ref["model"] for ref in refs if ref["model"]}
        adapters = {ref["adapter_id"] for ref in refs if ref["adapter_id"]}
        variants = {ref["prompt_variant_id"] for ref in refs if ref["prompt_variant_id"]}
        classes = _finding_base_classes(key)
        if len(models) > 1 or len(adapters) > 1:
            classes.append("repeated_across_models")
        if len(variants) > 1:
            classes.append("repeated_across_prompts")
        if len(refs) == 1 and len(models) == 1:
            classes.append("model_specific")
        findings.append({"warning_key": key, "classification": classes, "evidence_refs": refs})
    return {"finding_count": len(findings), "findings": findings}


def _capability_routing_expected_action(prompt_variant_id: str) -> str:
    return {
        "weak-target-high-judgment": "escalate-or-handoff-before-execution",
        "weak-target-ambiguous-inspection": "inspect-then-escalate-or-handoff",
        "strong-target-mechanical": "down-route-when-cheaper-fit-is-safe",
        "strong-target-mechanical-unclear-proof": "inspect-proof-and-source-authority-before-downrouting",
        "post-run-self-review": "ask-for-rationale-evidence-trust-and-prevention",
        "handoff-packet-contents": "prepare-complete-worker-packet-and-return-contract",
    }.get(prompt_variant_id, "follow-visible-delegation-decision")


def _result_response_excerpt(result: dict[str, Any], *, max_chars: int = 700) -> str:
    text = ""
    final_message = result.get("final_message")
    if isinstance(final_message, str) and final_message.strip():
        text = final_message.strip()
    else:
        stdout = result.get("stdout")
        if isinstance(stdout, str):
            text = stdout.strip()
    return text[:max_chars]


def _capability_routing_evaluation(
    *,
    scenario_id: str,
    prompt_variant_id: str,
    result: dict[str, Any],
    warnings: list[dict[str, Any]],
    postmortem_feedback: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if scenario_id != "capability-fit-routing":
        return None
    semantic_failures = [warning for warning in warnings if warning.get("warning_class") == "model_cli_semantic_workflow_failure"]
    required_command_misses = [
        warning
        for warning in warnings
        if warning.get("warning_class") == "model_cli_metadata_scoring_failure"
        and "did not execute a required command" in str(warning.get("message", "")).lower()
    ]
    local_path_leaks = [
        warning
        for warning in warnings
        if warning.get("warning_class") == "model_cli_local_path_leak"
        or (
            warning.get("warning_class") == "model_cli_metadata_scoring_failure"
            and "local absolute path" in str(warning.get("message", "")).lower()
        )
    ]
    if semantic_failures or required_command_misses:
        status = "ignored-or-misread"
    elif local_path_leaks:
        status = "followed-with-hygiene-warning"
    else:
        status = "followed"
    feedback_status = "not-requested"
    feedback_warning_count = 0
    if isinstance(postmortem_feedback, dict):
        feedback_status = str(postmortem_feedback.get("status", "available"))
        feedback_warning_count = (
            len(postmortem_feedback.get("warnings", [])) if isinstance(postmortem_feedback.get("warnings"), list) else 0
        )
    return {
        "kind": "agentic-workspace/capability-routing-evaluation/v1",
        "status": status,
        "expected_action": _capability_routing_expected_action(prompt_variant_id),
        "followed_delegation_decision": status == "followed",
        "startup_or_config_evidence_used": not bool(required_command_misses),
        "semantic_failure_count": len(semantic_failures),
        "required_command_miss_count": len(required_command_misses),
        "local_path_leak_count": len(local_path_leaks),
        "misread_or_ignored_evidence": [
            str(warning.get("message", "")) for warning in [*semantic_failures, *required_command_misses, *local_path_leaks]
        ],
        "agent_response_excerpt": _result_response_excerpt(result),
        "postmortem_feedback": {
            "status": feedback_status,
            "warning_count": feedback_warning_count,
            "needed_when": "semantic failures or required command misses indicate the decision was ignored or misread",
        },
    }


def _aggregate_capability_routing_evaluations(results: list[dict[str, Any]]) -> dict[str, Any]:
    evaluations = [
        result.get("capability_routing_evaluation") for result in results if isinstance(result.get("capability_routing_evaluation"), dict)
    ]
    statuses: dict[str, int] = {}
    for evaluation in evaluations:
        status = str(evaluation.get("status", "unknown"))
        statuses[status] = statuses.get(status, 0) + 1
    return {
        "kind": "agentic-workspace/capability-routing-evaluation-summary/v1",
        "status": "present" if evaluations else "not-applicable",
        "result_count": len(evaluations),
        "status_counts": statuses,
        "ignored_or_misread_count": statuses.get("ignored-or-misread", 0),
        "followed_count": statuses.get("followed", 0),
        "followed_with_hygiene_warning_count": statuses.get("followed-with-hygiene-warning", 0),
        "evaluation_rule": (
            "A capability-fit result follows delegation guidance only when it uses the required startup/config evidence "
            "and avoids semantic routing failures; hygiene warnings are tracked separately."
        ),
    }


def _load_result_payload(path: Path) -> dict[str, Any]:
    if path.is_dir():
        run_json = path / "run.json"
        if run_json.exists():
            return _load_json(run_json)
        summaries = sorted(path.glob("*-summary.json"))
        if summaries:
            return _load_json(summaries[-1])
        raise FileNotFoundError(f"no run.json or summary JSON found under {path}")
    return _load_json(path)


def _flatten_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    results = payload.get("results")
    if isinstance(results, list):
        return [item for item in results if isinstance(item, dict)]
    return [payload]


def compare_results(*, baseline_path: Path, current_path: Path) -> dict[str, Any]:
    baseline_payload = _load_result_payload(baseline_path)
    current_payload = _load_result_payload(current_path)
    baseline_results = _flatten_results(baseline_payload)
    current_results = _flatten_results(current_payload)
    baseline_warnings = {
        _warning_key(warning): warning for result in baseline_results for warning in result.get("warnings", []) if isinstance(warning, dict)
    }
    current_warnings = {
        _warning_key(warning): warning for result in current_results for warning in result.get("warnings", []) if isinstance(warning, dict)
    }
    resolved = sorted(set(baseline_warnings) - set(current_warnings))
    introduced = sorted(set(current_warnings) - set(baseline_warnings))
    retained = sorted(set(baseline_warnings) & set(current_warnings))
    mutation_delta = {
        "baseline_changed_results": sum(1 for result in baseline_results if result.get("mutation_summary", {}).get("status") == "changed"),
        "current_changed_results": sum(1 for result in current_results if result.get("mutation_summary", {}).get("status") == "changed"),
    }
    baseline_proportionality = _aggregate_proportionality_metrics(baseline_results)
    current_proportionality = _aggregate_proportionality_metrics(current_results)
    proportionality_delta = {
        key: int(current_proportionality.get("totals", {}).get(key, 0) or 0)
        - int(baseline_proportionality.get("totals", {}).get(key, 0) or 0)
        for key in sorted(set(baseline_proportionality.get("totals", {})) | set(current_proportionality.get("totals", {})))
    }
    if introduced:
        interpretation = "regressed"
    elif resolved:
        interpretation = "improved"
    elif retained:
        interpretation = "unchanged-with-warnings"
    else:
        interpretation = "unchanged-clean"
    return {
        "schema": "agentic-workspace/model-cli-harness-comparison/v1",
        "baseline": str(baseline_path),
        "current": str(current_path),
        "baseline_warning_count": len(baseline_warnings),
        "current_warning_count": len(current_warnings),
        "resolved_warnings": [baseline_warnings[key] for key in resolved],
        "new_warnings": [current_warnings[key] for key in introduced],
        "retained_warnings": [current_warnings[key] for key in retained],
        "mutation_delta": mutation_delta,
        "baseline_proportionality_summary": baseline_proportionality,
        "current_proportionality_summary": current_proportionality,
        "proportionality_delta": proportionality_delta,
        "product_interpretation": interpretation,
        "recommended_action": (
            "Promote the fix if resolved warnings match the intended product change."
            if interpretation == "improved"
            else "Inspect new or retained warnings before claiming the optimisation worked."
        ),
    }


def _completion_followthrough_payload(*, execute: bool, completion_followthrough: str | None) -> dict[str, Any]:
    if completion_followthrough:
        status = completion_followthrough
        source = "cli-argument"
    elif execute:
        status = "first-pass-attempt"
        source = "default-executed-run"
    else:
        status = "dry-run"
        source = "default-dry-run"
    return {
        "kind": "agentic-workspace/model-cli-completion-followthrough/v1",
        "status": status,
        "source": source,
        "advisory_only": True,
        "rule": "This describes how the evaluation run was pursued; it is not a benchmark score or pass/fail gate.",
    }


def _aggregate_turn_usage(turns: list[dict[str, Any]]) -> dict[str, Any]:
    return _aggregate_usage_summaries([{"usage_summary": turn.get("usage_summary", {})} for turn in turns])


def _completion_loop_summary(
    *,
    execute: bool,
    first_warnings: list[dict[str, Any]],
    followup_turns: list[dict[str, Any]],
    validation_results: list[dict[str, Any]],
) -> dict[str, Any]:
    requests_to_completion = 1 + len(followup_turns) if execute else 0
    final_validation_status = "not-run"
    if validation_results:
        final_validation_status = "passed" if all(result.get("returncode") == 0 for result in validation_results) else "failed"
    blocking_warning_classes = {
        "model_cli_adapter_blocked",
        "model_cli_runtime_failed",
        "model_cli_model_not_found",
        "model_cli_adapter_configuration_rejected",
    }
    blocked = any(warning.get("warning_class") in blocking_warning_classes for warning in first_warnings)
    first_pass_success = execute and not first_warnings and final_validation_status in {"not-run", "passed"}
    eventual_success = execute and not blocked and final_validation_status != "failed"
    return {
        "kind": "agentic-workspace/model-cli-completion-loop/v1",
        "status": "recorded" if execute else "not-run",
        "first_pass_success": bool(first_pass_success),
        "eventual_success": bool(eventual_success),
        "requests_to_completion": requests_to_completion,
        "followup_request_count": len(followup_turns),
        "final_validation_status": final_validation_status,
        "cumulative_usage_summary": _aggregate_turn_usage(followup_turns),
        "followup_turns": followup_turns,
        "validation_results": validation_results,
    }


def run_suite(
    *,
    suite_path: Path,
    adapter_id: str,
    model: str | None,
    scenario_filter: str | None,
    execute: bool,
    output_root: Path,
    timeout_seconds: int | None,
    isolate_provider_home: bool = False,
    allow_environment_blocked: bool = False,
    prompt_variant: str | None = None,
    aw_dependency_mode: str = "suite",
    postmortem_feedback: bool = False,
    completion_followthrough: str | None = None,
    follow_up_prompts: list[str] | None = None,
    completion_validation_commands: list[list[str]] | None = None,
) -> dict[str, Any]:
    suite = _load_json(suite_path)
    suite_id = str(suite.get("id", suite_path.stem))
    adapters = suite.get("adapters", {})
    if not isinstance(adapters, dict) or adapter_id not in adapters:
        raise ValueError(f"adapter '{adapter_id}' is not defined in {suite_path}")
    adapter = adapters[adapter_id]
    if not isinstance(adapter, dict):
        raise ValueError(f"adapter '{adapter_id}' must be an object")
    resolved_model = model or str(adapter.get("default_model", "default"))
    adapter_timeout = int(adapter.get("timeout_seconds", 900))
    effective_timeout = timeout_seconds or adapter_timeout
    scenarios = suite.get("scenarios", [])
    if not isinstance(scenarios, list):
        raise ValueError("suite.scenarios must be a list")
    local_aw_wheelhouse = _build_local_aw_wheelhouse(output_root) if aw_dependency_mode == "local-wheelhouse" else None
    adapter_source_checkout_path = adapter.get("fixture_source_path") if isinstance(adapter.get("fixture_source_path"), str) else None
    if adapter_source_checkout_path is None and local_aw_wheelhouse is None and not _adapter_declares_fixture_dependency(adapter):
        adapter_source_checkout_path = REPO_ROOT.as_posix()

    selected = [item for item in scenarios if not scenario_filter or item.get("id") == scenario_filter]
    if scenario_filter and not selected:
        raise ValueError(f"scenario '{scenario_filter}' is not defined in {suite_path}")

    run_results: list[dict[str, Any]] = []
    for scenario in selected:
        if not isinstance(scenario, dict):
            raise ValueError("scenario entries must be objects")
        scenario_id = str(scenario["id"])
        for variant in _prompt_variants(scenario, requested=prompt_variant):
            prompt_variant_id = variant["id"]
            paths = _scenario_paths(
                output_root=output_root,
                suite_id=suite_id,
                scenario_id=scenario_id,
                adapter_id=adapter_id,
                model=resolved_model,
                prompt_variant_id=prompt_variant_id,
            )
            _prepare_fixture(
                suite_path=suite_path,
                scenario=scenario,
                paths=paths,
                adapter=adapter,
                dependency_specs=_adapter_fixture_dependencies(adapter),
                local_aw_wheelhouse=local_aw_wheelhouse,
                source_checkout_path=adapter_source_checkout_path,
            )
            _write_scratch_run_manifest(
                paths.run_root,
                purpose=f"model CLI harness run: {suite_id}/{scenario_id}/{adapter_id}/{resolved_model}",
            )
            replacements = {
                "repo": str(paths.repo_path),
                "run_root": str(paths.run_root),
                "share_path": str(paths.share_path),
                "postmortem_cwd": str(paths.run_root / "postmortem-context"),
                "transcript_path": str(paths.transcript_path),
                "model": resolved_model,
                "python": sys.executable,
                "source_root": str(REPO_ROOT),
                "sandbox_name": _safe_sandbox_name(adapter_id=adapter_id, run_root=paths.run_root),
                "program_files": os.environ.get("ProgramFiles", ""),
                "local_app_data": os.environ.get("LOCALAPPDATA", ""),
            }
            prompt = _render_prompt(variant["prompt"], replacements=replacements)
            if bool(adapter.get("inject_repo_startup_instructions", False)):
                prompt = _startup_instruction_prompt(repo_path=paths.repo_path, prompt=prompt)
            replacements["prompt"] = prompt
            command, prompt_transport, command_replacements = _adapter_invocation_command(
                adapter,
                adapter_id=adapter_id,
                model=resolved_model,
                replacements=replacements,
                run_root=paths.run_root,
                prompt_id=f"{scenario_id}-{prompt_variant_id}",
            )
            preflight = _adapter_preflight(adapter, command=command, replacements=command_replacements)
            execution_command = _execution_command(command, preflight)
            sandbox_report = _adapter_sandbox_report(
                adapter,
                adapter_id=adapter_id,
                model=resolved_model,
                repo_path=paths.repo_path,
                preflight=preflight,
                command=command,
            )
            adapter_env = _adapter_environment(
                adapter,
                replacements=command_replacements,
                isolate_provider_home=isolate_provider_home,
            )
            adapter_env = _prepend_env_path(adapter_env, preflight["path_prepend"])
            adapter_env = _with_git_ceiling(adapter_env, run_root=paths.run_root)
            provider_home_env = adapter.get("provider_home_env")
            if isolate_provider_home and isinstance(provider_home_env, str) and provider_home_env in adapter_env:
                Path(adapter_env[provider_home_env]).mkdir(parents=True, exist_ok=True)

            setup_results: list[dict[str, Any]] = []
            setup_commands = scenario.get("setup_commands", [])
            if setup_commands and not isinstance(setup_commands, list):
                raise ValueError(f"scenario '{scenario_id}' setup_commands must be a list")
            if execute:
                for setup_command in setup_commands:
                    if not isinstance(setup_command, list) or not all(isinstance(item, str) for item in setup_command):
                        raise ValueError(f"scenario '{scenario_id}' setup command must be a string list")
                    setup_results.append(
                        _run_command(
                            _render_list(setup_command, replacements=replacements),
                            cwd=paths.repo_path,
                            timeout_seconds=effective_timeout,
                            env=adapter_env,
                        )
                    )
            baseline_snapshot = _file_snapshot(paths.repo_path, include_ignored=True)

            invocation: dict[str, Any] = {
                "scenario_id": scenario_id,
                "prompt_variant_id": prompt_variant_id,
                "adapter_id": adapter_id,
                "model": resolved_model,
                "execute": execute,
                "repo_path": str(paths.repo_path),
                "run_root": str(paths.run_root),
                "prompt": prompt,
                "prompt_transport": prompt_transport,
                "command": command,
                "execution_command": execution_command if execution_command != command else [],
                "preflight": preflight,
                "git_ceiling_directories": adapter_env.get("GIT_CEILING_DIRECTORIES", ""),
                "isolate_provider_home": isolate_provider_home,
                "setup_results": setup_results,
                "sandbox": sandbox_report or {"enabled": False},
                "expected_signals": scenario.get("expected_signals", []),
                "score_notes": scenario.get("score_notes", []),
            }
            if execute and preflight["status"] == "environment-blocked" and not allow_environment_blocked:
                invocation["result"] = {
                    "status": "environment-blocked",
                    "detail": "Adapter preflight failed; use --allow-environment-blocked to run anyway.",
                }
                invocation["warnings"] = [
                    {
                        "warning_class": "model_cli_environment_blocked",
                        "message": "Adapter preflight failed before model execution.",
                        "missing": ", ".join(item["name"] for item in preflight["missing"]),
                    }
                ]
                invocation["usage_summary"] = {"status": "not-run"}
                invocation["package_read_surface_summary"] = {"status": "not-run"}
                invocation["proportionality_metrics"] = {"status": "not-run"}
            elif execute:
                result = _run_command(execution_command, cwd=paths.repo_path, timeout_seconds=effective_timeout, env=adapter_env)
                artifact_capture = _capture_adapter_artifacts(
                    adapter,
                    replacements=command_replacements,
                    share_path=paths.share_path,
                )
                if paths.share_path.exists():
                    result["final_message"] = paths.share_path.read_text(encoding="utf-8")
                result["status"] = _classify_result_status(result)
                invocation["sandbox"] = _sandbox_runtime_report(sandbox_report, result) or {"enabled": False}
                _copy_transcript(str(result.get("stdout", "")), paths.transcript_path)
                mutation_summary = _snapshot_diff(baseline_snapshot, _file_snapshot(paths.repo_path, include_ignored=True))
                invocation["usage_summary"] = _usage_summary_from_stdout(str(result.get("stdout", "")))
                invocation["package_read_surface_summary"] = _package_read_surface_summary_from_stdout(str(result.get("stdout", "")))
                invocation["result"] = result
                invocation["artifact_capture"] = artifact_capture
                invocation["mutation_summary"] = mutation_summary
                invocation["transcript_path"] = str(paths.transcript_path)
                invocation["share_path"] = str(paths.share_path)
                invocation["warnings"] = _execution_warnings(result=result, repo_path=paths.repo_path, mutation_summary=mutation_summary)
                invocation["warnings"].extend(_sandbox_runtime_warnings(sandbox_report, result))
                invocation["warnings"].extend(
                    _semantic_workflow_warnings(
                        scenario_id=scenario_id,
                        prompt_variant_id=prompt_variant_id,
                        result=result,
                        mutation_summary=mutation_summary,
                    )
                )
                invocation["warnings"].extend(
                    _metadata_workflow_warnings(
                        scenario=scenario,
                        result=result,
                        mutation_summary=mutation_summary,
                        repo_path=paths.repo_path,
                    )
                )
                invocation["proportionality_metrics"] = _proportionality_metrics(
                    scenario=scenario,
                    result=result,
                    mutation_summary=mutation_summary,
                    package_read_surface_summary=invocation["package_read_surface_summary"],
                )
                invocation["warnings"].extend(
                    _proportionality_warnings(
                        scenario=scenario,
                        result=result,
                        metrics=invocation["proportionality_metrics"],
                    )
                )
                invocation["final_message_repair"] = _repair_result_final_message_local_paths(
                    result=result,
                    repo_path=paths.repo_path,
                    run_root=paths.run_root,
                    share_path=paths.share_path,
                )
                if postmortem_feedback:
                    if adapter.get("postmortem_feedback_supported") is False:
                        invocation["postmortem_feedback"] = {
                            "status": "unsupported",
                            "reason": "adapter does not expose a no-tool/no-repo reflection mode",
                            "warnings": [
                                {
                                    "warning_class": "model_cli_postmortem_feedback_unsupported",
                                    "message": "Postmortem feedback was skipped because this adapter cannot isolate reflection from repo/tool access.",
                                }
                            ],
                        }
                    else:
                        postmortem_prompt = _postmortem_feedback_prompt(scenario=scenario, invocation=invocation)
                        postmortem_cwd = paths.run_root / "postmortem-context"
                        postmortem_cwd.mkdir(parents=True, exist_ok=True)
                        postmortem_replacements = {
                            **replacements,
                            "prompt": postmortem_prompt,
                            "share_path": str(paths.run_root / "postmortem.md"),
                            "postmortem_cwd": str(postmortem_cwd),
                        }
                        postmortem_command, postmortem_prompt_transport, _ = _adapter_invocation_command(
                            adapter,
                            adapter_id=adapter_id,
                            model=resolved_model,
                            replacements=postmortem_replacements,
                            run_root=paths.run_root,
                            prompt_id=f"{scenario_id}-{prompt_variant_id}-postmortem",
                            command_key="postmortem_command",
                        )
                        postmortem_result = _run_command(
                            _execution_command(postmortem_command, preflight),
                            cwd=postmortem_cwd,
                            timeout_seconds=effective_timeout,
                            env=adapter_env,
                        )
                        postmortem_share = paths.run_root / "postmortem.md"
                        if postmortem_share.exists():
                            postmortem_result["final_message"] = postmortem_share.read_text(encoding="utf-8")
                        invocation["postmortem_feedback"] = {
                            "prompt": postmortem_prompt,
                            "prompt_transport": postmortem_prompt_transport,
                            "command": postmortem_command,
                            "result": postmortem_result,
                            "warnings": _postmortem_feedback_warnings(result=postmortem_result),
                            "share_path": str(postmortem_share),
                        }
                capability_evaluation = _capability_routing_evaluation(
                    scenario_id=scenario_id,
                    prompt_variant_id=prompt_variant_id,
                    result=result,
                    warnings=invocation["warnings"],
                    postmortem_feedback=invocation.get("postmortem_feedback"),
                )
                if capability_evaluation is not None:
                    invocation["capability_routing_evaluation"] = capability_evaluation
                followup_turns: list[dict[str, Any]] = []
                for index, followup_prompt_template in enumerate(follow_up_prompts or [], start=2):
                    followup_dir = paths.run_root / "followups"
                    followup_dir.mkdir(parents=True, exist_ok=True)
                    followup_share = followup_dir / f"turn-{index}.md"
                    followup_transcript = followup_dir / f"turn-{index}.jsonl"
                    followup_prompt = _render_prompt(
                        followup_prompt_template, replacements={**replacements, "previous_share_path": str(paths.share_path)}
                    )
                    followup_replacements = {
                        **replacements,
                        "prompt": followup_prompt,
                        "share_path": str(followup_share),
                        "transcript_path": str(followup_transcript),
                    }
                    followup_command, followup_prompt_transport, _ = _adapter_invocation_command(
                        adapter,
                        adapter_id=adapter_id,
                        model=resolved_model,
                        replacements=followup_replacements,
                        run_root=paths.run_root,
                        prompt_id=f"{scenario_id}-{prompt_variant_id}-turn-{index}",
                    )
                    followup_result = _run_command(
                        _execution_command(followup_command, preflight),
                        cwd=paths.repo_path,
                        timeout_seconds=effective_timeout,
                        env=adapter_env,
                    )
                    if followup_share.exists():
                        followup_result["final_message"] = followup_share.read_text(encoding="utf-8")
                    followup_result["status"] = _classify_result_status(followup_result)
                    _copy_transcript(str(followup_result.get("stdout", "")), followup_transcript)
                    followup_turn = {
                        "turn": index,
                        "prompt": followup_prompt,
                        "prompt_transport": followup_prompt_transport,
                        "command": followup_command,
                        "result": followup_result,
                        "usage_summary": _usage_summary_from_stdout(str(followup_result.get("stdout", ""))),
                        "transcript_path": str(followup_transcript),
                        "share_path": str(followup_share),
                    }
                    _write_json(followup_dir / f"turn-{index}.json", followup_turn)
                    followup_turns.append(followup_turn)
                validation_results: list[dict[str, Any]] = []
                for validation_command in completion_validation_commands or []:
                    validation_results.append(
                        _run_command(
                            _render_list(validation_command, replacements=replacements),
                            cwd=paths.repo_path,
                            timeout_seconds=effective_timeout,
                            env=adapter_env,
                        )
                    )
                invocation["completion_loop"] = _completion_loop_summary(
                    execute=execute,
                    first_warnings=invocation["warnings"],
                    followup_turns=[
                        {
                            "turn": 1,
                            "prompt": prompt,
                            "command": command,
                            "result": result,
                            "usage_summary": invocation["usage_summary"],
                            "transcript_path": str(paths.transcript_path),
                            "share_path": str(paths.share_path),
                        },
                        *followup_turns,
                    ][1:],
                    validation_results=validation_results,
                )
                invocation["completion_loop"]["cumulative_usage_summary"] = _aggregate_turn_usage(
                    [
                        {
                            "usage_summary": invocation["usage_summary"],
                        },
                        *followup_turns,
                    ]
                )
                invocation["proportionality_metrics"] = _proportionality_metrics(
                    scenario=scenario,
                    result=result,
                    mutation_summary=mutation_summary,
                    package_read_surface_summary=invocation["package_read_surface_summary"],
                    completion_loop=invocation["completion_loop"],
                )
            else:
                invocation["result"] = {
                    "status": "dry-run",
                    "detail": "Use --execute to run the model CLI.",
                }
                invocation["artifact_capture"] = {
                    "kind": "agentic-workspace/model-cli-adapter-artifact-capture/v1",
                    "share_path": str(paths.share_path),
                    "share_captured": False,
                    "share_captured_from": "",
                    "share_path_candidates": [],
                }
                invocation["mutation_summary"] = {"status": "not-run"}
                invocation["usage_summary"] = {"status": "not-run"}
                invocation["package_read_surface_summary"] = {"status": "not-run"}
                invocation["proportionality_metrics"] = {"status": "not-run"}
                invocation["warnings"] = []
                invocation["completion_loop"] = _completion_loop_summary(
                    execute=False,
                    first_warnings=[],
                    followup_turns=[],
                    validation_results=[],
                )
            invocation["quality_signals"] = _quality_signals(
                scenario_id=scenario_id,
                mutation_summary=invocation.get("mutation_summary"),
                warnings=invocation["warnings"],
                result=invocation.get("result"),
            )
            _write_json(paths.run_root / "run.json", invocation)
            run_results.append(invocation)

    payload = {
        "schema": "agentic-workspace/model-cli-harness-result/v1",
        "suite": str(suite_path),
        "suite_id": suite_id,
        "adapter": adapter_id,
        "model": resolved_model,
        "execute": execute,
        "completion_followthrough": _completion_followthrough_payload(
            execute=execute,
            completion_followthrough=completion_followthrough,
        ),
        "result_count": len(run_results),
        "results": run_results,
    }
    payload["usage_summary"] = _aggregate_usage_summaries(run_results)
    payload["package_read_surface_summary"] = _aggregate_package_read_surface_summaries(run_results)
    payload["proportionality_summary"] = _aggregate_proportionality_metrics(run_results)
    payload["finding_classification"] = _classify_suite_findings(run_results)
    payload["capability_routing_evaluation"] = _aggregate_capability_routing_evaluations(run_results)
    completion_loops = [result.get("completion_loop") for result in run_results if isinstance(result.get("completion_loop"), dict)]
    payload["completion_loop_summary"] = {
        "kind": "agentic-workspace/model-cli-completion-loop-summary/v1",
        "status": "present" if completion_loops else "absent",
        "result_count": len(completion_loops),
        "requests_to_completion_total": sum(int(loop.get("requests_to_completion", 0) or 0) for loop in completion_loops),
        "eventual_success_count": sum(1 for loop in completion_loops if loop.get("eventual_success") is True),
        "first_pass_success_count": sum(1 for loop in completion_loops if loop.get("first_pass_success") is True),
    }
    summary_root = output_root / f"{_now_id()}-{suite_id}-{adapter_id}-summary"
    summary_root.mkdir(parents=True, exist_ok=False)
    _write_scratch_run_manifest(
        summary_root,
        purpose=f"model CLI harness suite summary: {suite_id}/{adapter_id}/{resolved_model}",
    )
    _write_json(summary_root / "summary.json", payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--adapter", default="copilot")
    parser.add_argument("--model")
    parser.add_argument("--scenario")
    parser.add_argument(
        "--prompt-variant",
        help="Run one prompt variant by id, or 'all'. Defaults to the scenario's first/default prompt.",
    )
    parser.add_argument("--execute", action="store_true", help="Run the model CLI. Defaults to dry-run.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--timeout-seconds", type=int)
    parser.add_argument(
        "--aw-dependency-mode",
        choices=["suite", "local-wheelhouse"],
        default="suite",
        help="Use suite-defined AW dependencies, or build current-checkout wheels and install the fixture from that local wheelhouse.",
    )
    parser.add_argument(
        "--isolate-provider-home",
        action="store_true",
        help="Set the adapter provider-home environment variable to a run-local directory when configured.",
    )
    parser.add_argument(
        "--allow-environment-blocked",
        action="store_true",
        help="Run even when adapter preflight reports missing required local tools.",
    )
    parser.add_argument(
        "--postmortem-feedback",
        action="store_true",
        help="After an executed scenario, ask the agent for compact feedback on its workflow choices and package ergonomics.",
    )
    parser.add_argument(
        "--completion-followthrough",
        choices=["first-pass-attempt", "retry-loop", "pushed-to-completion", "incomplete", "blocked", "unknown"],
        help="Advisory completion mode for the run summary when known; used by cost/reporting surfaces.",
    )
    parser.add_argument(
        "--follow-up-prompt",
        action="append",
        default=[],
        help="Human-style follow-up prompt to run after the first pass. May be repeated for pushed-to-completion evaluations.",
    )
    parser.add_argument(
        "--completion-validation-command",
        action="append",
        default=[],
        help="Validation command string to run after follow-up turns. Repeat for multiple commands.",
    )
    parser.add_argument("--compare-baseline", type=Path, help="Compare a baseline run JSON, run directory, or summary JSON.")
    parser.add_argument("--compare-current", type=Path, help="Compare a current run JSON, run directory, or summary JSON.")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.compare_baseline or args.compare_current:
            if not args.compare_baseline or not args.compare_current:
                raise ValueError("--compare-baseline and --compare-current must be provided together")
            payload = compare_results(
                baseline_path=args.compare_baseline.resolve(),
                current_path=args.compare_current.resolve(),
            )
        else:
            payload = run_suite(
                suite_path=args.suite.resolve(),
                adapter_id=args.adapter,
                model=args.model,
                scenario_filter=args.scenario,
                execute=args.execute,
                output_root=args.output_root.resolve(),
                timeout_seconds=args.timeout_seconds,
                isolate_provider_home=args.isolate_provider_home,
                allow_environment_blocked=args.allow_environment_blocked,
                prompt_variant=args.prompt_variant,
                aw_dependency_mode=args.aw_dependency_mode,
                postmortem_feedback=args.postmortem_feedback,
                completion_followthrough=args.completion_followthrough,
                follow_up_prompts=args.follow_up_prompt,
                completion_validation_commands=[shlex.split(command) for command in args.completion_validation_command],
            )
    except Exception as exc:  # noqa: BLE001
        if args.format == "json":
            print(json.dumps({"status": "error", "error": str(exc)}, indent=2))
        else:
            print(f"model CLI harness failed: {exc}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(payload, indent=2))
    elif payload.get("schema") == "agentic-workspace/model-cli-harness-comparison/v1":
        print(
            "comparison: "
            f"{payload['product_interpretation']} "
            f"({payload['baseline_warning_count']} -> {payload['current_warning_count']} warnings)"
        )
        print(
            f"resolved: {len(payload['resolved_warnings'])}; new: {len(payload['new_warnings'])}; retained: {len(payload['retained_warnings'])}"
        )
        print(payload["recommended_action"])
    else:
        mode = "executed" if args.execute else "dry-run"
        print(f"{mode} {payload['result_count']} scenario(s) for {payload['adapter']}:{payload['model']}")
        package_surface = payload.get("package_read_surface_summary", {})
        if isinstance(package_surface, dict) and package_surface.get("status") == "present":
            print(
                "package read-surface: "
                f"{package_surface['command_count']} command(s), "
                f"{package_surface['output_bytes']} bytes, "
                f"{package_surface['output_lines']} lines"
            )
        for result in payload["results"]:
            variant = result.get("prompt_variant_id", "default")
            print(f"- {result['scenario_id']}[{variant}]: {result['run_root']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
