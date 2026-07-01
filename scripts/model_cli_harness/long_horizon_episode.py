"""Run long-horizon model CLI episodes with phases and evaluator review."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

import run_model_cli_harness as harness

EPISODE_KIND = "agentic-workspace/long-horizon-episode/v1"
EVALUATION_KIND = "agentic-workspace/long-horizon-evaluation/v1"
EVALUATOR_TEXT_LIMIT = 12_000
EVALUATOR_PATH_LIST_LIMIT = 40
EVALUATOR_NOISY_PATH_PREFIXES = (
    ".venv/",
    "venv/",
    ".tox/",
    ".pytest_cache/",
    ".mypy_cache/",
    "__pycache__/",
)
DEFAULT_EPISODE = harness.REPO_ROOT / "tools" / "model-cli-harness" / "episodes" / "intent-proof-packaging-specifier.json"
DEFAULT_OUTPUT_ROOT = harness.DEFAULT_OUTPUT_ROOT / "long-horizon"
AW_MODE_FIXTURE = harness.REPO_ROOT / "tools" / "model-cli-harness" / "fixtures" / "aw-minimal-host-repo"
MISTAKE_CLASSES = {
    "wrong_intent",
    "premature_implementation",
    "unnecessary_planning",
    "missing_planning",
    "wrong_owner_edit",
    "generated_surface_direct_edit",
    "manual_managed_state_edit",
    "existing_helper_missed",
    "duplicate_helper",
    "bad_abstraction",
    "weak_proof",
    "proof_overclaim",
    "completion_overclaim",
    "memory_ignored",
    "stale_memory_trusted",
    "adr_candidate_missed",
    "handoff_unusable",
    "restart_failed",
    "stale_planning_state_trusted",
}
EVALUATION_CONTRACT_FIELDS = {
    "issue_refs",
    "failure_path_summary",
    "agent_facing_claim_boundary",
    "required_reconciliation",
    "blocked_full_completion_when",
    "evaluator_focus",
    "handoff_contract",
}


def _string_list(value: Any, *, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be a list of strings")
    return value


def _list_of_commands(value: Any, *, field: str) -> list[list[str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    commands: list[list[str]] = []
    for index, command in enumerate(value):
        if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
            raise ValueError(f"{field}.{index} must be a string list command")
        commands.append(command)
    return commands


def _validate_evaluation_contract(value: Any, *, field: str) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    unknown_fields = sorted(set(value) - EVALUATION_CONTRACT_FIELDS)
    if unknown_fields:
        raise ValueError(f"{field} has unknown fields: {', '.join(unknown_fields)}")
    for list_field in ("issue_refs", "required_reconciliation", "evaluator_focus"):
        _string_list(value.get(list_field), field=f"{field}.{list_field}")
    for string_field in ("failure_path_summary", "agent_facing_claim_boundary"):
        if string_field in value and not isinstance(value[string_field], str):
            raise ValueError(f"{field}.{string_field} must be a string")
    blocked_rules = value.get("blocked_full_completion_when")
    if blocked_rules is not None:
        if not isinstance(blocked_rules, list):
            raise ValueError(f"{field}.blocked_full_completion_when must be a list")
        for index, rule in enumerate(blocked_rules):
            rule_field = f"{field}.blocked_full_completion_when.{index}"
            if not isinstance(rule, dict):
                raise ValueError(f"{rule_field} must be an object")
            unknown_rule_fields = sorted(set(rule) - {"mistake_class", "reason"})
            if unknown_rule_fields:
                raise ValueError(f"{rule_field} has unknown fields: {', '.join(unknown_rule_fields)}")
            mistake_class = rule.get("mistake_class")
            if not isinstance(mistake_class, str) or not mistake_class.strip():
                raise ValueError(f"{rule_field}.mistake_class is required")
            if mistake_class not in MISTAKE_CLASSES:
                raise ValueError(f"{rule_field}.mistake_class is unknown: {mistake_class}")
            if "reason" in rule and not isinstance(rule["reason"], str):
                raise ValueError(f"{rule_field}.reason must be a string")
    handoff_contract = value.get("handoff_contract")
    if handoff_contract is not None:
        if not isinstance(handoff_contract, dict):
            raise ValueError(f"{field}.handoff_contract must be an object")
        unknown_handoff_fields = sorted(set(handoff_contract) - {"required_record", "avoid"})
        if unknown_handoff_fields:
            raise ValueError(f"{field}.handoff_contract has unknown fields: {', '.join(unknown_handoff_fields)}")
        _string_list(handoff_contract.get("required_record"), field=f"{field}.handoff_contract.required_record")
        if "avoid" in handoff_contract and not isinstance(handoff_contract["avoid"], str):
            raise ValueError(f"{field}.handoff_contract.avoid must be a string")


def load_episode(path: Path) -> dict[str, Any]:
    episode = harness._load_json(path)
    validate_episode(episode)
    return episode


def validate_episode(episode: dict[str, Any]) -> None:
    if episode.get("kind") != EPISODE_KIND:
        raise ValueError(f"episode kind must be {EPISODE_KIND}")
    for field in ("id", "title", "task_prompt"):
        if not isinstance(episode.get(field), str) or not episode[field].strip():
            raise ValueError(f"episode.{field} is required")
    modes = episode.get("modes")
    if not isinstance(modes, list) or not modes:
        raise ValueError("episode.modes must be a non-empty list")
    mode_ids: set[str] = set()
    for index, mode in enumerate(modes):
        if not isinstance(mode, dict):
            raise ValueError(f"episode.modes.{index} must be an object")
        mode_id = mode.get("id")
        if not isinstance(mode_id, str) or not mode_id.strip():
            raise ValueError(f"episode.modes.{index}.id is required")
        if mode_id in mode_ids:
            raise ValueError(f"duplicate episode mode id: {mode_id}")
        mode_ids.add(mode_id)
        if not isinstance(mode.get("fixture"), str) and not isinstance(mode.get("repo_url"), str):
            raise ValueError(f"episode.modes.{mode_id} needs fixture or repo_url")
        _phase_overrides(mode, field=f"episode.modes.{mode_id}.phase_overrides")
    phases = episode.get("phases")
    if not isinstance(phases, list) or not phases:
        raise ValueError("episode.phases must be a non-empty list")
    for index, phase in enumerate(phases):
        if not isinstance(phase, dict):
            raise ValueError(f"episode.phases.{index} must be an object")
        for field in ("id", "prompt"):
            if not isinstance(phase.get(field), str) or not phase[field].strip():
                raise ValueError(f"episode.phases.{index}.{field} is required")
        _list_of_commands(phase.get("validation_commands"), field=f"episode.phases.{index}.validation_commands")
    _list_of_commands(episode.get("setup_commands"), field="episode.setup_commands")
    _list_of_commands(episode.get("visible_validation_commands"), field="episode.visible_validation_commands")
    for field in ("known_traps", "expected_mistake_classes"):
        values = _string_list(episode.get(field), field=f"episode.{field}")
        if field == "expected_mistake_classes":
            unknown = sorted(set(values) - MISTAKE_CLASSES)
            if unknown:
                raise ValueError(f"unknown mistake classes: {', '.join(unknown)}")
    rubric = episode.get("rubric")
    if not isinstance(rubric, dict) or not rubric:
        raise ValueError("episode.rubric must be a non-empty object")
    _validate_evaluation_contract(episode.get("evaluation_contract"), field="episode.evaluation_contract")


def validate_evaluation_result(result: dict[str, Any]) -> None:
    if result.get("kind") != EVALUATION_KIND:
        raise ValueError(f"evaluation kind must be {EVALUATION_KIND}")
    for field in ("scenario", "mode", "result", "mistake_classes", "aw_effect", "evidence"):
        if field not in result:
            raise ValueError(f"evaluation.{field} is required")
    outcome = result["result"]
    if not isinstance(outcome, dict):
        raise ValueError("evaluation.result must be an object")
    for field in (
        "intent_satisfied",
        "scope_respected",
        "proof_sufficient",
        "proof_matches_intent",
        "restartable_from_repo_state",
        "completion_claim_honest",
    ):
        if field not in outcome:
            raise ValueError(f"evaluation.result.{field} is required")
    mistake_classes = _string_list(result.get("mistake_classes"), field="evaluation.mistake_classes")
    unknown = sorted(set(mistake_classes) - MISTAKE_CLASSES)
    if unknown:
        raise ValueError(f"unknown evaluation mistake classes: {', '.join(unknown)}")
    aw_effect = result["aw_effect"]
    if not isinstance(aw_effect, dict):
        raise ValueError("evaluation.aw_effect must be an object")
    for field in ("helped", "hurt_or_overhead", "missed_affordance"):
        _string_list(aw_effect.get(field), field=f"evaluation.aw_effect.{field}")
    evidence = result["evidence"]
    if not isinstance(evidence, list):
        raise ValueError("evaluation.evidence must be a list")
    for index, item in enumerate(evidence):
        if not isinstance(item, dict) or not isinstance(item.get("kind"), str) or not isinstance(item.get("ref"), str):
            raise ValueError(f"evaluation.evidence.{index} needs kind and ref")


def _episode_paths(*, episode: dict[str, Any], mode_id: str, output_root: Path) -> harness.HarnessPaths:
    episode_id = str(episode.get("id", "episode"))
    readable = f"{episode_id}-{mode_id}"
    digest = hashlib.sha1(readable.encode("utf-8")).hexdigest()[:10]
    run_root = output_root / f"{harness._now_id()}-lh-{_path_slug(episode_id, 20)}-{_path_slug(mode_id, 12)}-{digest}"
    return harness.HarnessPaths(
        run_root=run_root,
        fixture_root=run_root / "fixture",
        repo_path=run_root / "repo",
        transcript_path=run_root / "transcript.jsonl",
        share_path=run_root / "session.md",
    )


def _path_slug(value: str, max_length: int) -> str:
    rendered = "".join(character if character.isalnum() else "-" for character in value.lower())
    rendered = "-".join(part for part in rendered.split("-") if part)
    return (rendered or "episode")[:max_length]


def _bootstrap_aw_mode(
    repo_path: Path,
    *,
    dependency_specs: list[str] | None = None,
    source_checkout_path: str | None = None,
) -> None:
    source_workspace = AW_MODE_FIXTURE / ".agentic-workspace"
    target_workspace = repo_path / ".agentic-workspace"
    if not target_workspace.exists():
        shutil.copytree(source_workspace, target_workspace)
    source_agents = (AW_MODE_FIXTURE / "AGENTS.md").read_text(encoding="utf-8").strip()
    target_agents = repo_path / harness.startup_instructions_file(repo_path)
    if target_agents.exists():
        existing_agents = target_agents.read_text(encoding="utf-8")
        if "<!-- agentic-workspace:workflow:start -->" not in existing_agents:
            target_agents.write_text(existing_agents.rstrip() + "\n\n" + source_agents + "\n", encoding="utf-8")
    else:
        target_agents.write_text(source_agents + "\n", encoding="utf-8")
    harness._prepare_source_checkout_invocation(
        repo_path,
        dependency_specs=dependency_specs,
        source_checkout_path=source_checkout_path,
    )


def _phase_overrides(mode: dict[str, Any], *, field: str) -> dict[str, dict[str, Any]]:
    raw_overrides = mode.get("phase_overrides", {})
    if raw_overrides is None:
        return {}
    if not isinstance(raw_overrides, dict):
        raise ValueError(f"{field} must be an object")
    overrides: dict[str, dict[str, Any]] = {}
    for phase_id, override in raw_overrides.items():
        if not isinstance(phase_id, str) or not phase_id.strip():
            raise ValueError(f"{field} keys must be phase ids")
        if not isinstance(override, dict):
            raise ValueError(f"{field}.{phase_id} must be an object")
        overrides[phase_id] = override
    return overrides


def _prepare_mode_repo(
    *,
    suite_path: Path,
    mode: dict[str, Any],
    paths: harness.HarnessPaths,
    execute: bool,
    dependency_specs: list[str] | None = None,
    adapter: dict[str, Any] | None = None,
    local_aw_wheelhouse: Path | None = None,
    source_checkout_path: str | None = None,
) -> dict[str, Any]:
    def effective_dependency_specs(repo_path: Path) -> list[str] | None:
        if local_aw_wheelhouse is None or adapter is None:
            return dependency_specs
        return harness._fixture_local_wheel_dependencies(
            repo_path=repo_path,
            source_wheelhouse=local_aw_wheelhouse,
            adapter=adapter,
        )

    def git_longpaths_enabled() -> bool:
        result = harness._run_command(["git", "config", "--get", "core.longpaths"], cwd=paths.run_root, timeout_seconds=30)
        if result.get("returncode") != 0:
            return False
        return str(result.get("stdout") or "").strip().lower() == "true"

    def preflight_windows_clone_path(*, repo_url: str) -> None:
        if os.name != "nt":
            return
        target = str(paths.repo_path.resolve())
        if len(target) < 180 or git_longpaths_enabled():
            return
        raise RuntimeError(
            "git clone path-length preflight failed for external long-horizon repo "
            f"{repo_url}: target path is {len(target)} characters. "
            "Set `git config --global core.longpaths true` or use a shorter --output-root before running the Docker episode."
        )

    paths.run_root.mkdir(parents=True, exist_ok=False)
    setup_before: dict[str, dict[str, Any]] | None = None
    fixture = mode.get("fixture")
    if isinstance(fixture, str):
        fixture_path = (suite_path.parent / ".." / "fixtures" / fixture).resolve()
        if not fixture_path.exists():
            fixture_path = (harness.REPO_ROOT / fixture).resolve()
        if not fixture_path.exists():
            raise FileNotFoundError(f"fixture not found: {fixture}")
        shutil.copytree(fixture_path, paths.repo_path)
        prepared_dependency_specs = effective_dependency_specs(paths.repo_path)
        if mode.get("aw_enabled"):
            setup_before = harness._file_snapshot(paths.repo_path, include_ignored=True)
            _bootstrap_aw_mode(
                paths.repo_path,
                dependency_specs=prepared_dependency_specs,
                source_checkout_path=source_checkout_path,
            )
        else:
            harness._prepare_source_checkout_invocation(
                paths.repo_path,
                dependency_specs=prepared_dependency_specs,
                source_checkout_path=source_checkout_path,
            )
        return _setup_mutation_summary(setup_before=setup_before, repo_path=paths.repo_path)
    repo_url = mode.get("repo_url")
    base_commit = mode.get("base_commit")
    if not isinstance(repo_url, str) or not isinstance(base_commit, str):
        raise ValueError(f"mode {mode.get('id', '<unknown>')} needs fixture or repo_url/base_commit")
    if not execute:
        paths.repo_path.mkdir(parents=True)
        (paths.repo_path / "PINNED-REPO.txt").write_text(f"{repo_url}\n{base_commit}\n", encoding="utf-8")
        prepared_dependency_specs = effective_dependency_specs(paths.repo_path)
        if mode.get("aw_enabled"):
            setup_before = harness._file_snapshot(paths.repo_path, include_ignored=True)
            _bootstrap_aw_mode(
                paths.repo_path,
                dependency_specs=prepared_dependency_specs,
                source_checkout_path=source_checkout_path,
            )
        else:
            harness._prepare_source_checkout_invocation(
                paths.repo_path,
                dependency_specs=prepared_dependency_specs,
                source_checkout_path=source_checkout_path,
            )
        return _setup_mutation_summary(setup_before=setup_before, repo_path=paths.repo_path)
    preflight_windows_clone_path(repo_url=repo_url)
    result = harness._run_command(["git", "clone", repo_url, str(paths.repo_path)], cwd=paths.run_root, timeout_seconds=900)
    if result["returncode"] != 0:
        raise RuntimeError(f"git clone failed for {repo_url}: {result['stderr']}")
    checkout = harness._run_command(["git", "checkout", base_commit], cwd=paths.repo_path, timeout_seconds=120)
    if checkout["returncode"] != 0:
        raise RuntimeError(f"git checkout failed for {base_commit}: {checkout['stderr']}")
    prepared_dependency_specs = effective_dependency_specs(paths.repo_path)
    if mode.get("aw_enabled"):
        setup_before = harness._file_snapshot(paths.repo_path, include_ignored=True)
        _bootstrap_aw_mode(
            paths.repo_path,
            dependency_specs=prepared_dependency_specs,
            source_checkout_path=source_checkout_path,
        )
    else:
        harness._prepare_source_checkout_invocation(
            paths.repo_path,
            dependency_specs=prepared_dependency_specs,
            source_checkout_path=source_checkout_path,
        )
    return _setup_mutation_summary(setup_before=setup_before, repo_path=paths.repo_path)


def _setup_mutation_summary(*, setup_before: dict[str, dict[str, Any]] | None, repo_path: Path) -> dict[str, Any]:
    if setup_before is None:
        return {"status": "not-applicable"}
    return harness._snapshot_diff(
        setup_before,
        harness._file_snapshot(repo_path, include_ignored=True),
        harness_setup_patterns=harness.HARNESS_SETUP_MUTATION_PATHS,
    )


def _adapter_command(
    *,
    suite: dict[str, Any],
    adapter_id: str,
    model: str | None,
    replacements: dict[str, str],
) -> tuple[list[str], str, dict[str, Any], dict[str, Any], dict[str, str]]:
    adapter = suite.get("adapters", {}).get(adapter_id)
    if not isinstance(adapter, dict):
        raise ValueError(f"adapter '{adapter_id}' is not defined")
    resolved_model = model or str(adapter.get("default_model") or "default")
    command, prompt_transport, command_replacements = harness._adapter_invocation_command(
        adapter,
        adapter_id=adapter_id,
        model=resolved_model,
        replacements={**replacements, "model": resolved_model},
        run_root=Path(replacements["run_root"]),
        prompt_id=f"{replacements.get('mode_id', 'mode')}-{replacements.get('phase_id', 'phase')}",
    )
    return command, resolved_model, adapter, prompt_transport, command_replacements


def _adapter_fixture_source_path(*, suite: dict[str, Any], adapter_id: str) -> str | None:
    adapter = suite.get("adapters", {}).get(adapter_id)
    if not isinstance(adapter, dict):
        return None
    source_path = adapter.get("fixture_source_path")
    return source_path if isinstance(source_path, str) and source_path.strip() else None


def _adapter_fixture_dependencies(*, suite: dict[str, Any], adapter_id: str) -> list[str]:
    adapter = suite.get("adapters", {}).get(adapter_id)
    if not isinstance(adapter, dict):
        return ["agentic-workspace"]
    return harness._adapter_fixture_dependencies(adapter)


def _run_validation_commands(
    *,
    commands: list[list[str]],
    replacements: dict[str, str],
    cwd: Path,
    execute: bool,
    timeout_seconds: int,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for command in commands:
        rendered = harness._render_list(command, replacements=replacements)
        if execute:
            result = harness._run_command(rendered, cwd=cwd, timeout_seconds=timeout_seconds)
            results.append(result)
        else:
            results.append({"status": "dry-run", "command": rendered})
    return results


def _phase_prompt(*, episode: dict[str, Any], mode: dict[str, Any], phase: dict[str, Any], prior_context: list[str]) -> tuple[str, bool]:
    prompt_parts = [
        str(episode["task_prompt"]).strip(),
        f"Mode: {mode['id']}.",
        str(phase["prompt"]).strip(),
    ]
    include_prior = bool(prior_context) and not bool(phase.get("hide_transcript_for_resume"))
    if include_prior:
        prompt_parts.append("Prior phase context:\n" + "\n\n".join(prior_context))
    elif prior_context:
        prompt_parts.append("Resume from repository state only. Do not assume prior chat history.")
    return "\n\n".join(prompt_parts) + "\n", include_prior


def _effective_phase(*, phase: dict[str, Any], mode: dict[str, Any]) -> dict[str, Any]:
    override = _phase_overrides(mode, field=f"mode.{mode.get('id', '<unknown>')}.phase_overrides").get(str(phase["id"]), {})
    return {**phase, **override}


def _compact_text_for_evaluator(value: Any, *, limit: int = EVALUATOR_TEXT_LIMIT) -> dict[str, Any]:
    text = str(value or "")
    if len(text) <= limit:
        return {"text": text, "char_count": len(text), "truncated": False}
    half = max(1, limit // 2)
    return {
        "text": text[:half] + "\n[...truncated for evaluator prompt...]\n" + text[-half:],
        "char_count": len(text),
        "truncated": True,
    }


def _compact_command_result_for_evaluator(result: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key in ("status", "returncode", "timed_out"):
        if key in result:
            compact[key] = result[key]
    for key in ("final_message", "stdout", "stderr"):
        if key in result:
            compact[key] = _compact_text_for_evaluator(result.get(key))
    return compact


def _compact_validation_results_for_evaluator(results: Any) -> list[dict[str, Any]]:
    if not isinstance(results, list):
        return []
    compact_results: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        compact_item = {
            key: item[key]
            for key in ("command", "original_command", "cwd", "returncode", "status", "timed_out")
            if key in item
        }
        for key in ("stdout", "stderr"):
            if key in item:
                compact_item[key] = _compact_text_for_evaluator(item.get(key), limit=4_000)
        compact_results.append(compact_item)
    return compact_results


def _is_noisy_evaluator_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in EVALUATOR_NOISY_PATH_PREFIXES)


def _compact_path_list_for_evaluator(values: list[Any]) -> Any:
    paths = [str(item) for item in values]
    noisy_paths = [path for path in paths if _is_noisy_evaluator_path(path)]
    signal_paths = [path for path in paths if not _is_noisy_evaluator_path(path)]
    if len(paths) <= EVALUATOR_PATH_LIST_LIMIT and not noisy_paths:
        return paths
    selected = signal_paths[:EVALUATOR_PATH_LIST_LIMIT]
    return {
        "items": selected,
        "item_count": len(paths),
        "omitted_count": max(0, len(paths) - len(selected)),
        "omitted_noisy_count": len(noisy_paths),
        "sample_noisy": noisy_paths[:5],
        "truncated": len(paths) > len(selected),
    }


def _compact_mutation_summary_for_evaluator(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    compact: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, list):
            compact[key] = _compact_path_list_for_evaluator(item)
        else:
            compact[key] = item
    return compact


def _compact_phase_for_evaluator(phase: dict[str, Any]) -> dict[str, Any]:
    compact = {
        key: phase[key]
        for key in (
            "phase_id",
            "adapter_id",
            "model",
            "prompt_transport",
            "prior_transcript_included",
            "hide_transcript_for_resume",
            "preflight",
            "sandbox",
            "artifact_capture",
            "sandbox_failure",
            "continuation_contribution",
            "continuation_contribution_detail",
            "checkpoint",
        )
        if key in phase
    }
    compact["prompt"] = _compact_text_for_evaluator(phase.get("prompt"), limit=4_000)
    compact["command"] = phase.get("command", [])
    compact["execution_command"] = phase.get("execution_command", [])
    result = phase.get("result")
    compact["result"] = _compact_command_result_for_evaluator(result if isinstance(result, dict) else {})
    compact["mutation_summary"] = _compact_mutation_summary_for_evaluator(phase.get("mutation_summary"))
    compact["validation_results"] = _compact_validation_results_for_evaluator(phase.get("validation_results"))
    return compact


def _compact_mode_result_for_evaluator(mode_result: dict[str, Any]) -> dict[str, Any]:
    compact = {
        key: mode_result[key]
        for key in (
            "mode_id",
            "aw_enabled",
            "repo_path",
            "run_root",
            "setup_results",
        )
        if key in mode_result
    }
    compact["setup_mutation_summary"] = _compact_mutation_summary_for_evaluator(mode_result.get("setup_mutation_summary"))
    phases = mode_result.get("phases")
    compact["phases"] = [_compact_phase_for_evaluator(phase) for phase in phases if isinstance(phase, dict)] if isinstance(phases, list) else []
    return compact


def _evaluation_response_contract(*, episode: dict[str, Any], mode_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": EVALUATION_KIND,
        "scenario": str(episode.get("id", "")),
        "mode": str(mode_result.get("mode_id", "")),
        "result": {
            "intent_satisfied": "yes|partial|no",
            "scope_respected": True,
            "proof_sufficient": False,
            "proof_matches_intent": False,
            "restartable_from_repo_state": False,
            "completion_claim_honest": True,
        },
        "mistake_classes": [],
        "aw_effect": {
            "helped": [],
            "hurt_or_overhead": [],
            "missed_affordance": [],
        },
        "evidence": [
            {
                "kind": "file|command|transcript|summary",
                "ref": "repo-relative path, command, or artifact name",
                "why": "short reason this supports the score",
            }
        ],
        "human_review_required": False,
        "recommended_followup": {
            "type": "issue|none",
            "summary": "short follow-up or none",
        },
    }


def _evaluation_prompt(*, episode: dict[str, Any], mode_result: dict[str, Any]) -> str:
    hidden_oracle = episode.get("hidden_oracle")
    response_contract = _evaluation_response_contract(episode=episode, mode_result=mode_result)
    evidence_bundle = {
        "kind": "agentic-workspace/long-horizon-evidence-bundle/v1",
        "episode": {
            "id": episode["id"],
            "title": episode["title"],
            "rubric": episode.get("rubric", {}),
            "known_traps": episode.get("known_traps", []),
            "expected_mistake_classes": episode.get("expected_mistake_classes", []),
            "evaluation_contract": episode.get("evaluation_contract", {}),
        },
        "mode_result": _compact_mode_result_for_evaluator(mode_result),
        "hidden_oracle_excluded": hidden_oracle is not None,
        "compaction": {
            "kind": "agentic-workspace/long-horizon-evaluator-compaction/v1",
            "rule": "Evaluator prompts include compact phase evidence, not raw transcripts or full command stdout.",
            "text_limit": EVALUATOR_TEXT_LIMIT,
        },
    }
    return (
        f"Review this long-horizon episode evidence and return only one JSON object matching {EVALUATION_KIND}.\n"
        "The response must include every field in this exact top-level contract; use the supplied scenario and mode values:\n"
        + json.dumps(response_contract, indent=2, sort_keys=True)
        + "\n\nEvidence bundle:\n"
        + json.dumps(evidence_bundle, indent=2, sort_keys=True)
    )


def _contract_assessment(*, episode: dict[str, Any], evaluation_payload: dict[str, Any]) -> dict[str, Any]:
    contract = episode.get("evaluation_contract")
    if not isinstance(contract, dict) or not contract:
        return {"status": "absent"}
    if not isinstance(evaluation_payload, dict) or evaluation_payload.get("kind") != EVALUATION_KIND:
        return {
            "status": "pending-primary-score",
            "contract": contract,
            "claim_level": "unknown",
            "blocking_rules": [],
        }
    mistakes = set(_string_list(evaluation_payload.get("mistake_classes"), field="evaluation.mistake_classes"))
    blocking_rules: list[dict[str, Any]] = []
    for rule in contract.get("blocked_full_completion_when", []):
        if not isinstance(rule, dict):
            continue
        mistake_class = rule.get("mistake_class")
        if isinstance(mistake_class, str) and mistake_class in mistakes:
            blocking_rules.append(rule)
    full_completion_blocked = bool(blocking_rules)
    return {
        "status": "full-completion-blocked" if full_completion_blocked else "primary-score-allows-claim",
        "contract": contract,
        "claim_level": "partial-progress" if full_completion_blocked else "primary-evaluation-claim",
        "blocking_rules": blocking_rules,
        "required_reconciliation": contract.get("required_reconciliation", []) if full_completion_blocked else [],
        "agent_facing_claim_boundary": contract.get("agent_facing_claim_boundary", "") if full_completion_blocked else "",
    }


def _post_score_reference_payload(*, episode: dict[str, Any], evaluation_status: str) -> dict[str, Any]:
    hidden_oracle = episode.get("hidden_oracle")
    if not isinstance(hidden_oracle, dict):
        return {"status": "absent"}
    if evaluation_status != "valid":
        return {
            "status": "pending-primary-score",
            "primary_evaluation_status": evaluation_status,
            "reference_available": True,
            "rule": "The hidden/reference oracle is excluded from the primary evaluator prompt and exposed only after primary scoring.",
        }
    return {
        "status": "available-after-primary-score",
        "primary_evaluation_status": evaluation_status,
        "reference": hidden_oracle,
        "rule": "The hidden/reference oracle is excluded from the primary evaluator prompt and exposed only after primary scoring.",
    }


def _sandbox_failure_summary(
    *,
    phase_id: str,
    sandbox_report: dict[str, Any] | None,
    result: dict[str, Any],
    artifact_capture: dict[str, Any],
    checkpoint: dict[str, str],
) -> dict[str, Any] | None:
    if not sandbox_report or not sandbox_report.get("enabled"):
        return None
    runtime_status = str(sandbox_report.get("runtime_status") or result.get("status") or "")
    returncode = result.get("returncode")
    if runtime_status in {"completed", "dry-run"} and (returncode in {0, None}):
        return None
    stderr = str(result.get("stderr") or "")
    runtime_error = str(sandbox_report.get("runtime_error") or "").strip()
    timeout_text = f"{runtime_status}\n{stderr}\n{runtime_error}".lower()
    timed_out = bool(result.get("timed_out")) or "context deadline" in timeout_text or "deadline exceeded" in timeout_text
    failure_class = "sandbox-timeout" if timed_out else "sandbox-runtime-failed"
    share_path = checkpoint.get("share_path", "")
    transcript_path = checkpoint.get("transcript_path", "")
    share_artifact_exists = bool(result.get("final_message")) or bool(artifact_capture.get("share_captured"))
    if not share_artifact_exists and share_path:
        share_artifact_exists = Path(share_path).is_file()
    transcript_exists = bool(transcript_path) and Path(transcript_path).is_file()
    return {
        "kind": "agentic-workspace/long-horizon-sandbox-failure/v1",
        "status": "present",
        "failure_class": failure_class,
        "boundary": "sandbox-executor-timeout" if timed_out else "sandbox-adapter-runtime",
        "phase_id": phase_id,
        "sandbox": sandbox_report.get("identity", ""),
        "sandbox_name": sandbox_report.get("sandbox_name", ""),
        "runtime_status": runtime_status,
        "runtime_returncode": returncode,
        "timed_out": timed_out,
        "runtime_error": runtime_error or (stderr.strip().splitlines()[0][:500] if stderr.strip() else ""),
        "share_artifact_exists": share_artifact_exists,
        "transcript_exists": transcript_exists,
        "agent_performance_finding": False,
        "rule": "Sandbox runtime failures are harness/executor evidence until a model transcript or share artifact proves agent behavior.",
    }


def _parse_evaluation(text: str, *, scenario: str = "", mode: str = "") -> dict[str, Any]:
    payload = harness._json_document(text.strip())
    if payload is None:
        match = None
        for candidate in text.splitlines():
            candidate = candidate.strip()
            if candidate.startswith("{") and candidate.endswith("}"):
                match = candidate
        if match:
            payload = harness._json_document(match)
    if payload is None:
        raise ValueError("evaluator did not return a JSON object")
    repairs: list[str] = []
    if isinstance(payload, dict) and payload.get("kind") == EVALUATION_KIND:
        if "scenario" not in payload and scenario:
            payload["scenario"] = scenario
            repairs.append("filled missing scenario from episode context")
        if "mode" not in payload and mode:
            payload["mode"] = mode
            repairs.append("filled missing mode from mode context")
        if repairs:
            payload["harness_repairs"] = repairs
    validate_evaluation_result(payload)
    return payload


def _comparison_summary(mode_results: list[dict[str, Any]], *, episode: dict[str, Any] | None = None) -> dict[str, Any]:
    mistake_classes_by_mode: dict[str, list[str]] = {}
    aw_effect_by_mode: dict[str, dict[str, list[str]]] = {}
    post_score_reference_by_mode: dict[str, dict[str, Any]] = {}
    contract_assessment_by_mode: dict[str, dict[str, Any]] = {}
    invalid_evaluations_by_mode: dict[str, dict[str, Any]] = {}
    sandbox_runtime_failures_by_mode: dict[str, list[dict[str, Any]]] = {}
    human_review_required = False
    followups: list[dict[str, Any]] = []
    for result in mode_results:
        mode_id = result["mode_id"]
        sandbox_failures = [
            phase.get("sandbox_failure")
            for phase in result.get("phases", [])
            if isinstance(phase, dict)
            and isinstance(phase.get("sandbox_failure"), dict)
            and phase["sandbox_failure"].get("status") == "present"
        ]
        evaluation_result = result.get("evaluation", {})
        if isinstance(evaluation_result, dict) and isinstance(evaluation_result.get("sandbox_failure"), dict):
            evaluator_sandbox_failure = evaluation_result["sandbox_failure"]
            if evaluator_sandbox_failure.get("status") == "present":
                sandbox_failures.append(evaluator_sandbox_failure)
        if sandbox_failures:
            sandbox_runtime_failures_by_mode[mode_id] = sandbox_failures
            human_review_required = True
            for failure in sandbox_failures:
                followups.append(
                    {
                        "mode": mode_id,
                        "type": "rerun-executor",
                        "summary": "Rerun the Docker sandbox phase before scoring agent behavior.",
                        "phase_id": failure.get("phase_id", ""),
                        "failure_class": failure.get("failure_class", ""),
                        "boundary": failure.get("boundary", ""),
                        "sandbox": failure.get("sandbox", ""),
                        "sandbox_name": failure.get("sandbox_name", ""),
                        "share_artifact_exists": bool(failure.get("share_artifact_exists")),
                        "transcript_exists": bool(failure.get("transcript_exists")),
                        "aw_improvement_scope": "separate-from-agent-performance-finding",
                    }
                )
        if isinstance(evaluation_result, dict) and isinstance(evaluation_result.get("post_score_reference"), dict):
            post_score_reference_by_mode[mode_id] = evaluation_result["post_score_reference"]
        if isinstance(evaluation_result, dict) and isinstance(evaluation_result.get("contract_assessment"), dict):
            contract_assessment_by_mode[mode_id] = evaluation_result["contract_assessment"]
        evaluation_status = str(evaluation_result.get("status") or "") if isinstance(evaluation_result, dict) else ""
        evaluation = evaluation_result.get("payload") if isinstance(evaluation_result, dict) else None
        if evaluation_status == "invalid":
            schema_errors = []
            if isinstance(evaluation, dict) and isinstance(evaluation.get("error"), str):
                schema_errors.append(evaluation["error"])
            invalid_evaluations_by_mode[mode_id] = {
                "status": "invalid",
                "mode": mode_id,
                "schema_errors": schema_errors,
                "post_score_reference": post_score_reference_by_mode.get(mode_id, {}),
            }
            human_review_required = True
            followups.append(
                {
                    "mode": mode_id,
                    "type": "evaluation-harness",
                    "summary": "Primary evaluator payload was invalid; rerun or fix evaluator schema handling before treating this mode as scored.",
                    "schema_errors": schema_errors,
                    "primary_evaluation_status": evaluation_status,
                }
            )
        if not isinstance(evaluation, dict):
            continue
        mistake_classes_by_mode[mode_id] = list(evaluation.get("mistake_classes", []))
        aw_effect = evaluation.get("aw_effect", {})
        if isinstance(aw_effect, dict):
            aw_effect_by_mode[mode_id] = {
                "helped": list(aw_effect.get("helped", [])),
                "hurt_or_overhead": list(aw_effect.get("hurt_or_overhead", [])),
                "missed_affordance": list(aw_effect.get("missed_affordance", [])),
            }
        human_review_required = human_review_required or bool(evaluation.get("human_review_required"))
        followup = evaluation.get("recommended_followup")
        if isinstance(followup, dict):
            followups.append({"mode": mode_id, **followup})
    all_classes = sorted({item for values in mistake_classes_by_mode.values() for item in values})
    blocking_modes = [
        mode_id
        for mode_id, assessment in contract_assessment_by_mode.items()
        if assessment.get("status") == "full-completion-blocked"
    ]
    if mode_results and len(invalid_evaluations_by_mode) == len(mode_results):
        claim_gate_status = "invalid-primary-evaluation"
    elif invalid_evaluations_by_mode:
        claim_gate_status = "primary-evaluation-with-invalid-modes"
    elif blocking_modes:
        claim_gate_status = "full-completion-blocked"
    else:
        claim_gate_status = "primary-evaluation"
    return {
        "kind": "agentic-workspace/long-horizon-comparison/v1",
        "status": "present" if mode_results else "absent",
        "mode_count": len(mode_results),
        "mistake_classes": all_classes,
        "mistake_classes_by_mode": mistake_classes_by_mode,
        "aw_effect_by_mode": aw_effect_by_mode,
        "human_review_required": human_review_required,
        "recommended_followups": followups,
        "invalid_evaluations_by_mode": invalid_evaluations_by_mode,
        "sandbox_runtime_failures_by_mode": sandbox_runtime_failures_by_mode,
        "continuation_comparison": _continuation_comparison(mode_results),
        "post_score_reference_by_mode": post_score_reference_by_mode,
        "contract_assessment_by_mode": contract_assessment_by_mode,
        "claim_gate": {
            "status": claim_gate_status,
            "blocking_modes": blocking_modes,
            "invalid_modes": sorted(invalid_evaluations_by_mode),
            "sandbox_failure_modes": sorted(sandbox_runtime_failures_by_mode),
            "contract_present": bool(isinstance(episode, dict) and episode.get("evaluation_contract")),
            "rule": (
                "Episode evaluation contracts downgrade full-completion claims when configured mistake classes appear; "
                "visible validation success remains separate from semantic proof, restartability, and managed-state proof."
            ),
        },
        "rule": "Comparison is review evidence, not a deterministic leaderboard.",
    }


def _continuation_comparison(mode_results: list[dict[str, Any]]) -> dict[str, Any]:
    modes: list[dict[str, Any]] = []
    kinds: set[str] = set()
    continuation_contribution_by_mode: dict[str, str] = {}
    for result in mode_results:
        phases = result.get("phases", [])
        if not isinstance(phases, list):
            phases = []
        adapters = [str(phase.get("adapter_id", "")) for phase in phases if isinstance(phase, dict)]
        models = [str(phase.get("model", "")) for phase in phases if isinstance(phase, dict)]
        contributions = [str(phase.get("continuation_contribution", "unknown")) for phase in phases if isinstance(phase, dict)]
        if len(adapters) <= 1:
            kind = "single-phase"
        elif len(set(adapters)) == 1 and len(set(models)) == 1:
            kind = "same-agent-continuation"
        else:
            kind = "agent-switch-continuation"
        kinds.add(kind)
        continuation_contribution_by_mode[str(result.get("mode_id", ""))] = contributions[-1] if contributions else "unknown"
        modes.append(
            {
                "mode_id": result.get("mode_id", ""),
                "aw_enabled": bool(result.get("aw_enabled", False)),
                "phase_count": len(adapters),
                "phase_adapter_ids": adapters,
                "phase_models": models,
                "phase_contributions": contributions,
                "continuation_kind": kind,
            }
        )
    has_same_agent = "same-agent-continuation" in kinds
    has_agent_switch = "agent-switch-continuation" in kinds
    return {
        "status": "present" if has_same_agent and has_agent_switch else "partial" if modes else "absent",
        "has_same_agent_continuation": has_same_agent,
        "has_agent_switch_continuation": has_agent_switch,
        "continuation_contribution_by_mode": continuation_contribution_by_mode,
        "substantive_continuation_count": sum(
            1
            for contribution in continuation_contribution_by_mode.values()
            if contribution in {"changed-source", "changed-tests", "changed-non-source"}
        ),
        "modes": modes,
    }


def _path_contribution_kind(paths: list[str]) -> str:
    if any(path.startswith(("src/", "lib/", "packages/")) and not path.endswith((".md", ".txt")) for path in paths):
        return "changed-source"
    if any(
        path.startswith(("test/", "tests/", "testing/")) or path.endswith(("_test.py", "test.py")) or "/test_" in path for path in paths
    ):
        return "changed-tests"
    if paths:
        return "changed-non-source"
    return "no-op"


def _phase_contribution(mutation_summary: dict[str, Any]) -> dict[str, Any]:
    paths = sorted(
        set(mutation_summary.get("created", [])) | set(mutation_summary.get("modified", [])) | set(mutation_summary.get("deleted", []))
    )
    kind = _path_contribution_kind([str(path) for path in paths])
    if kind == "no-op" and mutation_summary.get("raw_status") == "changed":
        kind = "ignored-or-setup-only"
    return {
        "kind": kind,
        "source_change_count": len(paths),
        "raw_change_count": int(mutation_summary.get("raw_created_count", 0) or 0)
        + int(mutation_summary.get("raw_modified_count", 0) or 0)
        + int(mutation_summary.get("raw_deleted_count", 0) or 0),
        "paths": paths[:20],
    }


def run_episode(
    *,
    episode_path: Path,
    suite_path: Path = harness.DEFAULT_SUITE,
    execute: bool = False,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    mode_filter: str | None = None,
    evaluator: bool = True,
    timeout_seconds: int = 900,
    adapter_override: str | None = None,
    model_override: str | None = None,
    evaluator_adapter_override: str | None = None,
    evaluator_model_override: str | None = None,
    aw_dependency_mode: str = "suite",
) -> dict[str, Any]:
    episode = load_episode(episode_path)
    suite = harness._load_json(suite_path)
    modes = [mode for mode in episode["modes"] if mode_filter is None or mode["id"] == mode_filter]
    if not modes:
        raise ValueError(f"mode '{mode_filter}' is not defined")
    local_aw_wheelhouse = harness._build_local_aw_wheelhouse(output_root) if aw_dependency_mode == "local-wheelhouse" else None
    mode_results: list[dict[str, Any]] = []
    for mode in modes:
        paths = _episode_paths(episode=episode, mode_id=mode["id"], output_root=output_root)
        setup_adapter_id = adapter_override or str(episode.get("default_adapter") or "copilot")
        setup_adapter = suite.get("adapters", {}).get(setup_adapter_id)
        if aw_dependency_mode == "local-wheelhouse" and not isinstance(setup_adapter, dict):
            raise ValueError(f"adapter '{setup_adapter_id}' is not defined")
        setup_mutation_summary = _prepare_mode_repo(
            suite_path=suite_path,
            mode=mode,
            paths=paths,
            execute=execute,
            dependency_specs=_adapter_fixture_dependencies(suite=suite, adapter_id=setup_adapter_id),
            adapter=setup_adapter if isinstance(setup_adapter, dict) else None,
            local_aw_wheelhouse=local_aw_wheelhouse,
            source_checkout_path=_adapter_fixture_source_path(suite=suite, adapter_id=setup_adapter_id),
        )
        harness._write_scratch_run_manifest(
            paths.run_root,
            purpose=f"long-horizon episode run: {episode['id']}/{mode['id']}",
        )
        replacements = {
            "repo": str(paths.repo_path),
            "run_root": str(paths.run_root),
            "python": harness.sys.executable,
            "source_root": str(harness.REPO_ROOT),
            "sandbox_name": harness._safe_sandbox_name(
                adapter_id=adapter_override or str(episode.get("default_adapter") or "copilot"),
                run_root=paths.run_root,
            ),
            "program_files": os.environ.get("ProgramFiles", ""),
            "local_app_data": os.environ.get("LOCALAPPDATA", ""),
            "mode_id": str(mode["id"]),
            "episode_id": str(episode["id"]),
        }
        setup_results = _run_validation_commands(
            commands=_list_of_commands(episode.get("setup_commands"), field="episode.setup_commands"),
            replacements=replacements,
            cwd=paths.repo_path,
            execute=execute,
            timeout_seconds=timeout_seconds,
        )
        prior_context: list[str] = []
        phase_results: list[dict[str, Any]] = []
        previous_snapshot = harness._file_snapshot(paths.repo_path, include_ignored=True)
        for phase in episode["phases"]:
            phase = _effective_phase(phase=phase, mode=mode)
            phase_prompt, prior_included = _phase_prompt(episode=episode, mode=mode, phase=phase, prior_context=prior_context)
            phase_share = paths.run_root / f"{phase['id']}.md"
            phase_transcript = paths.run_root / f"{phase['id']}.transcript.jsonl"
            phase_replacements = {
                **replacements,
                "phase_id": str(phase["id"]),
                "share_path": str(phase_share),
                "transcript_path": str(phase_transcript),
                "prompt": phase_prompt,
            }
            phase_adapter_id = adapter_override or str(phase.get("adapter") or episode.get("default_adapter") or "copilot")
            if model_override:
                phase_model = model_override
            elif adapter_override:
                phase_model = None
            else:
                phase_model = phase.get("model") if isinstance(phase.get("model"), str) else None
            command, resolved_model, adapter, prompt_transport, command_replacements = _adapter_command(
                suite=suite,
                adapter_id=phase_adapter_id,
                model=phase_model,
                replacements=phase_replacements,
            )
            env = harness._adapter_environment(adapter, replacements=command_replacements, isolate_provider_home=False)
            preflight = harness._adapter_preflight(adapter, command=command, replacements=command_replacements)
            execution_command = harness._execution_command(command, preflight)
            sandbox_report = harness._adapter_sandbox_report(
                adapter,
                adapter_id=phase_adapter_id,
                model=resolved_model,
                repo_path=paths.repo_path,
                preflight=preflight,
                command=command,
            )
            env = harness._prepend_env_path(env, preflight["path_prepend"])
            result: dict[str, Any]
            if execute:
                result = harness._run_command(execution_command, cwd=paths.repo_path, timeout_seconds=timeout_seconds, env=env)
                artifact_capture = harness._capture_adapter_artifacts(
                    adapter,
                    replacements=command_replacements,
                    share_path=phase_share,
                )
                result["status"] = harness._classify_result_status(result)
                if phase_share.exists():
                    result["final_message"] = phase_share.read_text(encoding="utf-8")
                harness._copy_transcript(str(result.get("stdout", "")), phase_transcript)
                sandbox_report = harness._sandbox_runtime_report(sandbox_report, result)
            else:
                result = {"status": "dry-run", "command": command}
                artifact_capture = {
                    "kind": "agentic-workspace/model-cli-adapter-artifact-capture/v1",
                    "share_path": str(phase_share),
                    "share_captured": False,
                    "share_captured_from": "",
                    "share_path_candidates": [],
                }
            current_snapshot = harness._file_snapshot(paths.repo_path, include_ignored=True)
            mutation_summary = harness._snapshot_diff(previous_snapshot, current_snapshot)
            previous_snapshot = current_snapshot
            contribution = _phase_contribution(mutation_summary)
            validation_commands = _list_of_commands(
                phase.get("validation_commands", episode.get("visible_validation_commands")),
                field=f"phase.{phase['id']}.validation_commands",
            )
            validation_results = _run_validation_commands(
                commands=validation_commands,
                replacements=phase_replacements,
                cwd=paths.repo_path,
                execute=execute,
                timeout_seconds=timeout_seconds,
            )
            final_message = str(result.get("final_message") or result.get("stdout") or "")
            if final_message.strip():
                prior_context.append(f"{phase['id']} final message:\n{final_message.strip()}")
            checkpoint = {
                "transcript_path": str(phase_transcript),
                "share_path": str(phase_share),
                "repo_path": str(paths.repo_path),
            }
            sandbox_failure = _sandbox_failure_summary(
                phase_id=str(phase["id"]),
                sandbox_report=sandbox_report,
                result=result,
                artifact_capture=artifact_capture,
                checkpoint=checkpoint,
            )
            phase_results.append(
                {
                    "phase_id": phase["id"],
                    "adapter_id": phase_adapter_id,
                    "model": resolved_model,
                    "prompt": phase_prompt,
                    "prompt_transport": prompt_transport,
                    "prior_transcript_included": prior_included,
                    "hide_transcript_for_resume": bool(phase.get("hide_transcript_for_resume")),
                    "command": command,
                    "execution_command": execution_command if execution_command != command else [],
                    "preflight": preflight,
                    "sandbox": sandbox_report or {"enabled": False},
                    "artifact_capture": artifact_capture,
                    "sandbox_failure": sandbox_failure or {"status": "absent"},
                    "result": result,
                    "mutation_summary": mutation_summary,
                    "continuation_contribution": contribution["kind"],
                    "continuation_contribution_detail": contribution,
                    "validation_results": validation_results,
                    "checkpoint": checkpoint,
                }
            )
        mode_result: dict[str, Any] = {
            "mode_id": mode["id"],
            "aw_enabled": bool(mode.get("aw_enabled", False)),
            "repo_path": str(paths.repo_path),
            "run_root": str(paths.run_root),
            "setup_mutation_summary": setup_mutation_summary,
            "setup_results": setup_results,
            "phases": phase_results,
        }
        if evaluator and isinstance(episode.get("evaluator"), dict):
            evaluator_config = episode["evaluator"]
            evaluator_prompt = _evaluation_prompt(episode=episode, mode_result=mode_result)
            evaluator_share = paths.run_root / "evaluator.md"
            evaluator_replacements = {
                **replacements,
                "phase_id": "evaluator",
                "share_path": str(evaluator_share),
                "prompt": evaluator_prompt,
            }
            evaluator_adapter_id = evaluator_adapter_override or str(
                evaluator_config.get("adapter")
                or episode.get("default_evaluator_adapter")
                or episode.get("default_adapter")
                or "copilot"
            )
            if evaluator_model_override:
                evaluator_model = evaluator_model_override
            elif evaluator_adapter_override:
                evaluator_model = None
            else:
                evaluator_model = evaluator_config.get("model") if isinstance(evaluator_config.get("model"), str) else None
            command, resolved_model, adapter, prompt_transport, command_replacements = _adapter_command(
                suite=suite,
                adapter_id=evaluator_adapter_id,
                model=evaluator_model,
                replacements=evaluator_replacements,
            )
            env = harness._adapter_environment(adapter, replacements=command_replacements, isolate_provider_home=False)
            preflight = harness._adapter_preflight(adapter, command=command, replacements=command_replacements)
            execution_command = harness._execution_command(command, preflight)
            sandbox_report = harness._adapter_sandbox_report(
                adapter,
                adapter_id=evaluator_adapter_id,
                model=resolved_model,
                repo_path=paths.repo_path,
                preflight=preflight,
                command=command,
            )
            env = harness._prepend_env_path(env, preflight["path_prepend"])
            if execute:
                evaluator_result = harness._run_command(execution_command, cwd=paths.repo_path, timeout_seconds=timeout_seconds, env=env)
                artifact_capture = harness._capture_adapter_artifacts(
                    adapter,
                    replacements=command_replacements,
                    share_path=evaluator_share,
                )
                if evaluator_share.exists():
                    evaluator_result["final_message"] = evaluator_share.read_text(encoding="utf-8")
                text = str(evaluator_result.get("final_message") or evaluator_result.get("stdout") or "")
                try:
                    evaluation_payload = _parse_evaluation(text, scenario=str(episode["id"]), mode=str(mode["id"]))
                    evaluation_status = "valid"
                except ValueError as exc:
                    evaluation_payload = {"error": str(exc)}
                    evaluation_status = "invalid"
                sandbox_report = harness._sandbox_runtime_report(sandbox_report, evaluator_result)
            else:
                evaluator_result = {"status": "dry-run", "command": command}
                artifact_capture = {
                    "kind": "agentic-workspace/model-cli-adapter-artifact-capture/v1",
                    "share_path": str(evaluator_share),
                    "share_captured": False,
                    "share_captured_from": "",
                    "share_path_candidates": [],
                }
                evaluation_payload = {"status": "not-run"}
                evaluation_status = "not-run"
            contract_assessment = _contract_assessment(episode=episode, evaluation_payload=evaluation_payload)
            evaluator_checkpoint = {
                "transcript_path": "",
                "share_path": str(evaluator_share),
                "repo_path": str(paths.repo_path),
            }
            sandbox_failure = _sandbox_failure_summary(
                phase_id="evaluator",
                sandbox_report=sandbox_report,
                result=evaluator_result,
                artifact_capture=artifact_capture,
                checkpoint=evaluator_checkpoint,
            )
            mode_result["evaluation"] = {
                "status": evaluation_status,
                "adapter_id": evaluator_adapter_id,
                "model": resolved_model,
                "prompt": evaluator_prompt,
                "prompt_transport": prompt_transport,
                "command": command,
                "execution_command": execution_command if execution_command != command else [],
                "preflight": preflight,
                "sandbox": sandbox_report or {"enabled": False},
                "sandbox_failure": sandbox_failure or {"status": "absent"},
                "artifact_capture": artifact_capture,
                "result": evaluator_result,
                "payload": evaluation_payload,
                "contract_assessment": contract_assessment,
                "hidden_oracle_excluded": episode.get("hidden_oracle") is not None,
                "post_score_reference": _post_score_reference_payload(episode=episode, evaluation_status=evaluation_status),
            }
        mode_results.append(mode_result)
    payload = {
        "kind": "agentic-workspace/long-horizon-run/v1",
        "episode": str(episode_path),
        "episode_id": episode["id"],
        "execute": execute,
        "mode_count": len(mode_results),
        "modes": mode_results,
        "comparison": _comparison_summary(mode_results, episode=episode),
    }
    output_root.mkdir(parents=True, exist_ok=True)
    harness._write_json(output_root / f"{episode['id']}-summary.json", payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode", type=Path, default=DEFAULT_EPISODE)
    parser.add_argument("--suite", type=Path, default=harness.DEFAULT_SUITE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--mode", help="Run only one episode mode.")
    parser.add_argument("--adapter", help="Override the adapter used for all episode phases.")
    parser.add_argument("--model", help="Override the model used for all episode phases.")
    parser.add_argument("--evaluator-adapter", help="Override the evaluator adapter.")
    parser.add_argument("--evaluator-model", help="Override the evaluator model.")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--no-evaluator", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument(
        "--aw-dependency-mode",
        choices=["suite", "local-wheelhouse"],
        default="suite",
        help="Use suite-defined AW dependencies, or build current-checkout wheels and install fixtures from that local wheelhouse.",
    )
    parser.add_argument("--format", choices=("json", "text"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run_episode(
        episode_path=args.episode,
        suite_path=args.suite,
        execute=args.execute,
        output_root=args.output_root,
        mode_filter=args.mode,
        evaluator=not args.no_evaluator,
        timeout_seconds=args.timeout_seconds,
        adapter_override=args.adapter,
        model_override=args.model,
        evaluator_adapter_override=args.evaluator_adapter,
        evaluator_model_override=args.evaluator_model,
        aw_dependency_mode=args.aw_dependency_mode,
    )
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"{payload['episode_id']}: {payload['mode_count']} mode(s), execute={payload['execute']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
