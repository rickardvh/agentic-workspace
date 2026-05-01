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


def _selected_config_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    workspace = payload.get("workspace", {}) if isinstance(payload.get("workspace"), dict) else {}
    return {
        "exists": payload.get("exists"),
        "agent_instructions_file": workspace.get("agent_instructions_file"),
        "workflow_artifact_profile": workspace.get("workflow_artifact_profile"),
        "default_preset": workspace.get("default_preset"),
    }


def _selected_modules_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    package_footprint = payload.get("package_footprint", {}) if isinstance(payload.get("package_footprint"), dict) else {}
    component_model = payload.get("component_model", {}) if isinstance(payload.get("component_model"), dict) else {}
    compatibility = payload.get("feature_tiers_compatibility", {}) if isinstance(payload.get("feature_tiers_compatibility"), dict) else {}
    modules = payload.get("modules", [])
    module_names = [module.get("name") for module in modules if isinstance(module, dict)] if isinstance(modules, list) else []
    return {
        "package_footprint_status": package_footprint.get("status"),
        "component_model_alignment": component_model.get("alignment"),
        "feature_tiers_compatibility_status": compatibility.get("status"),
        "module_names": module_names,
    }


def _selected_start_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    context_router = payload.get("context_router", {}) if isinstance(payload.get("context_router"), dict) else {}
    proof = payload.get("proof", {}) if isinstance(payload.get("proof"), dict) else {}
    return {
        "kind": payload.get("kind"),
        "first_view": context_router.get("first_view"),
        "proof_kind": proof.get("kind"),
        "changed_paths": proof.get("changed_paths"),
    }


def _selected_summary_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    machine_first = payload.get("machine_first_planning", {}) if isinstance(payload.get("machine_first_planning"), dict) else {}
    execplans = payload.get("execplans", {}) if isinstance(payload.get("execplans"), dict) else {}
    return {
        "kind": payload.get("kind"),
        "profile": payload.get("profile"),
        "machine_first_status": machine_first.get("status"),
        "active_count": execplans.get("active_count"),
    }


def _selected_implement_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    proof = payload.get("proof", {}) if isinstance(payload.get("proof"), dict) else {}
    return {
        "kind": payload.get("kind"),
        "proof_kind": proof.get("kind"),
    }


def _selected_preflight_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    return {
        "kind": payload.get("kind"),
        "mode": payload.get("mode"),
    }


def _selected_proof_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    answer = payload.get("answer", {}) if isinstance(payload.get("answer"), dict) else {}
    return {
        "profile": payload.get("profile"),
        "surface": payload.get("surface"),
        "matched": payload.get("matched"),
        "answer_kind": answer.get("kind"),
    }


def _selected_ownership_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    return {
        "profile": payload.get("profile"),
        "surface": payload.get("surface"),
        "matched": payload.get("matched"),
    }


def _selected_skills_fields(stdout: str) -> dict[str, object]:
    payload = json.loads(stdout)
    return {
        "task": payload.get("task"),
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

        def compare_adapter(
            *,
            label: str,
            success_args: list[str],
            selected_fields,
            expected_fields: dict[str, object],
        ) -> None:
            canonical_process = _capture(
                [python, str(shim), *success_args],
                cwd=fixture_root,
                env=_conformance_env(),
            )
            if canonical_process.returncode != 0:
                errors.append(
                    f"runtime primitive failure: canonical {label} command exited {canonical_process.returncode}; "
                    f"stderr={canonical_process.stderr!r}"
                )
                return
            try:
                canonical_selected = selected_fields(canonical_process.stdout)
            except json.JSONDecodeError as exc:
                errors.append(f"runtime primitive failure: canonical {label} stdout was not JSON: {exc}")
                return
            if canonical_selected != expected_fields:
                errors.append(
                    f"runtime primitive failure: canonical {label} output shape drifted; "
                    f"expected selected fields {expected_fields!r}, got {canonical_selected!r}"
                )
                return

            adapter_process = _capture(
                [node, str(cli), *success_args],
                cwd=fixture_root,
                env=_conformance_env(runtime=runtime),
            )
            if adapter_process.returncode != canonical_process.returncode:
                errors.append(
                    f"adapter failure: {label} exit code drifted from canonical process; "
                    f"expected {canonical_process.returncode}, got {adapter_process.returncode}; stderr={adapter_process.stderr!r}"
                )
            else:
                try:
                    adapter_selected = selected_fields(adapter_process.stdout)
                except json.JSONDecodeError as exc:
                    errors.append(f"adapter failure: {label} stdout was not JSON: {exc}; stdout={adapter_process.stdout!r}")
                else:
                    if adapter_selected != canonical_selected:
                        errors.append(
                            f"adapter failure: {label} JSON selected fields drifted from canonical process; "
                            f"expected {canonical_selected!r}, got {adapter_selected!r}"
                        )
            if adapter_process.stderr.strip():
                errors.append(f"adapter failure: {label} emitted unexpected stderr: {adapter_process.stderr!r}")

            invalid_args = [*success_args, "--definitely-invalid"]
            canonical_invalid_process = _capture(
                [python, str(shim), *invalid_args],
                cwd=fixture_root,
                env=_conformance_env(),
            )
            adapter_invalid_process = _capture(
                [node, str(cli), *invalid_args],
                cwd=fixture_root,
                env=_conformance_env(runtime=runtime),
            )
            if adapter_invalid_process.returncode != canonical_invalid_process.returncode:
                errors.append(
                    f"adapter failure: {label} invalid-option exit code drifted from canonical process; "
                    f"expected {canonical_invalid_process.returncode}, got {adapter_invalid_process.returncode}"
                )
            if bool(adapter_invalid_process.stderr.strip()) != bool(canonical_invalid_process.stderr.strip()):
                errors.append(
                    f"adapter failure: {label} invalid-option stderr presence drifted from canonical process; "
                    f"canonical={canonical_invalid_process.stderr!r}, adapter={adapter_invalid_process.stderr!r}"
                )

        config_args = ["config", "--target", ".", "--format", "json"]
        canonical_config = _capture(
            [python, str(shim), *config_args],
            cwd=fixture_root,
            env=_conformance_env(),
        )
        if canonical_config.returncode != 0:
            return [f"runtime primitive failure: canonical config command exited {canonical_config.returncode}; stderr={canonical_config.stderr!r}"]
        try:
            canonical_config_fields = _selected_config_fields(canonical_config.stdout)
        except json.JSONDecodeError as exc:
            return [f"runtime primitive failure: canonical config stdout was not JSON: {exc}"]
        expected_config_fields = {
            "exists": False,
            "agent_instructions_file": "AGENTS.md",
            "workflow_artifact_profile": "repo-owned",
            "default_preset": "full",
        }
        if canonical_config_fields != expected_config_fields:
            return [
                "runtime primitive failure: canonical config output shape drifted; "
                f"expected selected fields {expected_config_fields!r}, got {canonical_config_fields!r}"
            ]

        adapter_config = _capture(
            [node, str(cli), *config_args],
            cwd=fixture_root,
            env=_conformance_env(runtime=runtime),
        )
        if adapter_config.returncode != canonical_config.returncode:
            errors.append(
                "adapter failure: config exit code drifted from canonical process; "
                f"expected {canonical_config.returncode}, got {adapter_config.returncode}; stderr={adapter_config.stderr!r}"
            )
        else:
            try:
                adapter_config_fields = _selected_config_fields(adapter_config.stdout)
            except json.JSONDecodeError as exc:
                errors.append(f"adapter failure: config stdout was not JSON: {exc}; stdout={adapter_config.stdout!r}")
            else:
                if adapter_config_fields != canonical_config_fields:
                    errors.append(
                        "adapter failure: config JSON selected fields drifted from canonical process; "
                        f"expected {canonical_config_fields!r}, got {adapter_config_fields!r}"
                    )
        if adapter_config.stderr.strip():
            errors.append(f"adapter failure: config emitted unexpected stderr: {adapter_config.stderr!r}")

        config_invalid_args = ["config", "--target", ".", "--format", "json", "--definitely-invalid"]
        canonical_config_invalid = _capture(
            [python, str(shim), *config_invalid_args],
            cwd=fixture_root,
            env=_conformance_env(),
        )
        adapter_config_invalid = _capture(
            [node, str(cli), *config_invalid_args],
            cwd=fixture_root,
            env=_conformance_env(runtime=runtime),
        )
        if adapter_config_invalid.returncode != canonical_config_invalid.returncode:
            errors.append(
                "adapter failure: config invalid-option exit code drifted from canonical process; "
                f"expected {canonical_config_invalid.returncode}, got {adapter_config_invalid.returncode}"
            )
        if bool(adapter_config_invalid.stderr.strip()) != bool(canonical_config_invalid.stderr.strip()):
            errors.append(
                "adapter failure: config invalid-option stderr presence drifted from canonical process; "
                f"canonical={canonical_config_invalid.stderr!r}, adapter={adapter_config_invalid.stderr!r}"
            )

        modules_args = ["modules", "--target", ".", "--format", "json"]
        canonical_modules = _capture(
            [python, str(shim), *modules_args],
            cwd=fixture_root,
            env=_conformance_env(),
        )
        if canonical_modules.returncode != 0:
            return [f"runtime primitive failure: canonical modules command exited {canonical_modules.returncode}; stderr={canonical_modules.stderr!r}"]
        try:
            canonical_modules_fields = _selected_modules_fields(canonical_modules.stdout)
        except json.JSONDecodeError as exc:
            return [f"runtime primitive failure: canonical modules stdout was not JSON: {exc}"]
        expected_modules_fields = {
            "package_footprint_status": "intentional-temporary",
            "component_model_alignment": "mcp-style-adapter-ready",
            "feature_tiers_compatibility_status": "deprecated-alias",
            "module_names": ["planning", "memory"],
        }
        if canonical_modules_fields != expected_modules_fields:
            return [
                "runtime primitive failure: canonical modules output shape drifted; "
                f"expected selected fields {expected_modules_fields!r}, got {canonical_modules_fields!r}"
            ]

        adapter_modules = _capture(
            [node, str(cli), *modules_args],
            cwd=fixture_root,
            env=_conformance_env(runtime=runtime),
        )
        if adapter_modules.returncode != canonical_modules.returncode:
            errors.append(
                "adapter failure: modules exit code drifted from canonical process; "
                f"expected {canonical_modules.returncode}, got {adapter_modules.returncode}; stderr={adapter_modules.stderr!r}"
            )
        else:
            try:
                adapter_modules_fields = _selected_modules_fields(adapter_modules.stdout)
            except json.JSONDecodeError as exc:
                errors.append(f"adapter failure: modules stdout was not JSON: {exc}; stdout={adapter_modules.stdout!r}")
            else:
                if adapter_modules_fields != canonical_modules_fields:
                    errors.append(
                        "adapter failure: modules JSON selected fields drifted from canonical process; "
                        f"expected {canonical_modules_fields!r}, got {adapter_modules_fields!r}"
                    )
        if adapter_modules.stderr.strip():
            errors.append(f"adapter failure: modules emitted unexpected stderr: {adapter_modules.stderr!r}")

        modules_invalid_args = ["modules", "--target", ".", "--format", "json", "--definitely-invalid"]
        canonical_modules_invalid = _capture(
            [python, str(shim), *modules_invalid_args],
            cwd=fixture_root,
            env=_conformance_env(),
        )
        adapter_modules_invalid = _capture(
            [node, str(cli), *modules_invalid_args],
            cwd=fixture_root,
            env=_conformance_env(runtime=runtime),
        )
        if adapter_modules_invalid.returncode != canonical_modules_invalid.returncode:
            errors.append(
                "adapter failure: modules invalid-option exit code drifted from canonical process; "
                f"expected {canonical_modules_invalid.returncode}, got {adapter_modules_invalid.returncode}"
            )
        if bool(adapter_modules_invalid.stderr.strip()) != bool(canonical_modules_invalid.stderr.strip()):
            errors.append(
                "adapter failure: modules invalid-option stderr presence drifted from canonical process; "
                f"canonical={canonical_modules_invalid.stderr!r}, adapter={adapter_modules_invalid.stderr!r}"
            )

        start_args = ["start", "--target", ".", "--changed", "README.md", "--format", "json"]
        canonical_start = _capture(
            [python, str(shim), *start_args],
            cwd=fixture_root,
            env=_conformance_env(),
        )
        if canonical_start.returncode != 0:
            return [f"runtime primitive failure: canonical start command exited {canonical_start.returncode}; stderr={canonical_start.stderr!r}"]
        try:
            canonical_start_fields = _selected_start_fields(canonical_start.stdout)
        except json.JSONDecodeError as exc:
            return [f"runtime primitive failure: canonical start stdout was not JSON: {exc}"]
        expected_start_fields = {
            "kind": "startup-context/v1",
            "first_view": "start",
            "proof_kind": "proof-selection/v1",
            "changed_paths": ["README.md"],
        }
        if canonical_start_fields != expected_start_fields:
            return [
                "runtime primitive failure: canonical start output shape drifted; "
                f"expected selected fields {expected_start_fields!r}, got {canonical_start_fields!r}"
            ]

        adapter_start = _capture(
            [node, str(cli), *start_args],
            cwd=fixture_root,
            env=_conformance_env(runtime=runtime),
        )
        if adapter_start.returncode != canonical_start.returncode:
            errors.append(
                "adapter failure: start exit code drifted from canonical process; "
                f"expected {canonical_start.returncode}, got {adapter_start.returncode}; stderr={adapter_start.stderr!r}"
            )
        else:
            try:
                adapter_start_fields = _selected_start_fields(adapter_start.stdout)
            except json.JSONDecodeError as exc:
                errors.append(f"adapter failure: start stdout was not JSON: {exc}; stdout={adapter_start.stdout!r}")
            else:
                if adapter_start_fields != canonical_start_fields:
                    errors.append(
                        "adapter failure: start JSON selected fields drifted from canonical process; "
                        f"expected {canonical_start_fields!r}, got {adapter_start_fields!r}"
                    )
        if adapter_start.stderr.strip():
            errors.append(f"adapter failure: start emitted unexpected stderr: {adapter_start.stderr!r}")

        start_invalid_args = ["start", "--target", ".", "--format", "json", "--definitely-invalid"]
        canonical_start_invalid = _capture(
            [python, str(shim), *start_invalid_args],
            cwd=fixture_root,
            env=_conformance_env(),
        )
        adapter_start_invalid = _capture(
            [node, str(cli), *start_invalid_args],
            cwd=fixture_root,
            env=_conformance_env(runtime=runtime),
        )
        if adapter_start_invalid.returncode != canonical_start_invalid.returncode:
            errors.append(
                "adapter failure: start invalid-option exit code drifted from canonical process; "
                f"expected {canonical_start_invalid.returncode}, got {adapter_start_invalid.returncode}"
            )
        if bool(adapter_start_invalid.stderr.strip()) != bool(canonical_start_invalid.stderr.strip()):
            errors.append(
                "adapter failure: start invalid-option stderr presence drifted from canonical process; "
                f"canonical={canonical_start_invalid.stderr!r}, adapter={adapter_start_invalid.stderr!r}"
            )

        summary_args = ["summary", "--target", ".", "--profile", "compact", "--format", "json"]
        canonical_summary = _capture(
            [python, str(shim), *summary_args],
            cwd=fixture_root,
            env=_conformance_env(),
        )
        if canonical_summary.returncode != 0:
            return [f"runtime primitive failure: canonical summary command exited {canonical_summary.returncode}; stderr={canonical_summary.stderr!r}"]
        try:
            canonical_summary_fields = _selected_summary_fields(canonical_summary.stdout)
        except json.JSONDecodeError as exc:
            return [f"runtime primitive failure: canonical summary stdout was not JSON: {exc}"]
        expected_summary_fields = {
            "kind": "planning-summary/v1",
            "profile": "compact",
            "machine_first_status": "no-active-execplan",
            "active_count": 0,
        }
        if canonical_summary_fields != expected_summary_fields:
            return [
                "runtime primitive failure: canonical summary output shape drifted; "
                f"expected selected fields {expected_summary_fields!r}, got {canonical_summary_fields!r}"
            ]

        adapter_summary = _capture(
            [node, str(cli), *summary_args],
            cwd=fixture_root,
            env=_conformance_env(runtime=runtime),
        )
        if adapter_summary.returncode != canonical_summary.returncode:
            errors.append(
                "adapter failure: summary exit code drifted from canonical process; "
                f"expected {canonical_summary.returncode}, got {adapter_summary.returncode}; stderr={adapter_summary.stderr!r}"
            )
        else:
            try:
                adapter_summary_fields = _selected_summary_fields(adapter_summary.stdout)
            except json.JSONDecodeError as exc:
                errors.append(f"adapter failure: summary stdout was not JSON: {exc}; stdout={adapter_summary.stdout!r}")
            else:
                if adapter_summary_fields != canonical_summary_fields:
                    errors.append(
                        "adapter failure: summary JSON selected fields drifted from canonical process; "
                        f"expected {canonical_summary_fields!r}, got {adapter_summary_fields!r}"
                    )
        if adapter_summary.stderr.strip():
            errors.append(f"adapter failure: summary emitted unexpected stderr: {adapter_summary.stderr!r}")

        summary_invalid_args = ["summary", "--target", ".", "--profile", "compact", "--format", "json", "--definitely-invalid"]
        canonical_summary_invalid = _capture(
            [python, str(shim), *summary_invalid_args],
            cwd=fixture_root,
            env=_conformance_env(),
        )
        adapter_summary_invalid = _capture(
            [node, str(cli), *summary_invalid_args],
            cwd=fixture_root,
            env=_conformance_env(runtime=runtime),
        )
        if adapter_summary_invalid.returncode != canonical_summary_invalid.returncode:
            errors.append(
                "adapter failure: summary invalid-option exit code drifted from canonical process; "
                f"expected {canonical_summary_invalid.returncode}, got {adapter_summary_invalid.returncode}"
            )
        if bool(adapter_summary_invalid.stderr.strip()) != bool(canonical_summary_invalid.stderr.strip()):
            errors.append(
                "adapter failure: summary invalid-option stderr presence drifted from canonical process; "
                f"canonical={canonical_summary_invalid.stderr!r}, adapter={adapter_summary_invalid.stderr!r}"
            )

        compare_adapter(
            label="implement",
            success_args=["implement", "--target", ".", "--changed", "README.md", "--task", "generated-adapter-proof", "--format", "json"],
            selected_fields=_selected_implement_fields,
            expected_fields={
                "kind": "implementer-context/v1",
                "proof_kind": "proof-selection/v1",
            },
        )
        compare_adapter(
            label="preflight",
            success_args=["preflight", "--target", ".", "--active-only", "--format", "json"],
            selected_fields=_selected_preflight_fields,
            expected_fields={
                "kind": "preflight-response/v1",
                "mode": "active-state-only",
            },
        )
        compare_adapter(
            label="proof",
            success_args=["proof", "--target", ".", "--changed", "README.md", "--format", "json"],
            selected_fields=_selected_proof_fields,
            expected_fields={
                "profile": "compact-contract-answer/v1",
                "surface": "proof",
                "matched": True,
                "answer_kind": "proof-selection/v1",
            },
        )
        compare_adapter(
            label="ownership",
            success_args=["ownership", "--target", ".", "--concern", "startup", "--format", "json"],
            selected_fields=_selected_ownership_fields,
            expected_fields={
                "profile": "compact-contract-answer/v1",
                "surface": "ownership",
                "matched": False,
            },
        )
        compare_adapter(
            label="skills",
            success_args=["skills", "--target", ".", "--task", "proof", "--format", "json"],
            selected_fields=_selected_skills_fields,
            expected_fields={
                "task": "proof",
            },
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
