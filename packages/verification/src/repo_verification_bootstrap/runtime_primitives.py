from __future__ import annotations

import ast
import fnmatch
import tomllib
from datetime import date
from pathlib import Path
from typing import Any

VERIFICATION_MANIFEST_PATH = Path(".agentic-workspace/verification/manifest.toml")
SCHEMA_VERSION = "agentic-workspace/verification-manifest/v1"
EVIDENCE_STRATEGY_KIND = "agentic-workspace/verification-evidence-strategy/v1"

DECLARED_STRATEGY_SOURCE_PATHS = [
    Path("docs/maintainer/testing-strategy.md"),
    Path("docs/maintainer/aw-contract-test-replacement-inventory.md"),
    Path(".agentic-workspace/docs/proof-surfaces-contract.md"),
    Path("docs/host-repo-learning.md"),
]

STRATEGY_SIGNAL_MARKERS = [
    ("prefer behavior contracts over one-off regressions", ["behavior contracts", "one-off regressions"]),
    ("merge repeated mode/section/branch-shape checks", ["Merge", "Repeated mode", "section", "branch-shape"]),
    ("convert stable generated command output only with named conformance owner", ["Contract-Owned Cases", "conformance"]),
    ("prune only with equivalent coverage recorded", ["Prune only", "equivalent coverage"]),
    ("root tests prove product orchestration", ["Root workspace tests prove", "product orchestration"]),
    ("package-local tests prove module-owned behavior", ["Package-local tests prove", "module-owned behavior"]),
    ("filenames and markers are hints, not authority", ["suggest discovery questions", "not authority"]),
]

FIXTURE_VARIANT_TOKENS = {
    "active",
    "alias",
    "aliases",
    "before",
    "current",
    "external",
    "json",
    "later",
    "missing",
    "mode",
    "modes",
    "path",
    "posix",
    "raw",
    "section",
    "selector",
    "text",
    "verbose",
    "windows",
    "without",
}


class VerificationUsageError(ValueError):
    """Raised when a repo verification manifest is invalid."""


def _dedupe(values: list[str]) -> list[str]:
    ordered: list[str] = []
    for value in values:
        if value and value not in ordered:
            ordered.append(value)
    return ordered


def _list_payload(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _repo_relative_path(path: Path, target_root: Path) -> str:
    try:
        return path.relative_to(target_root).as_posix()
    except ValueError:
        return path.as_posix()


def _normalize_changed_paths(paths: list[str] | None) -> list[str]:
    normalized: list[str] = []
    for path_text in paths or []:
        stripped = str(path_text).strip()
        if not stripped:
            continue
        path = Path(stripped)
        try:
            stripped = path.resolve().as_posix() if path.is_absolute() else path.as_posix()
        except OSError:
            stripped = path.as_posix()
        while stripped.startswith("./"):
            stripped = stripped[2:]
        stripped = stripped.rstrip("/")
        if stripped and stripped not in normalized:
            normalized.append(stripped)
    return normalized


def _read_text_if_present(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _declared_strategy_sources(*, target_root: Path) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for relative_path in DECLARED_STRATEGY_SOURCE_PATHS:
        text = _read_text_if_present(target_root / relative_path)
        if not text:
            continue
        signals = [
            signal
            for signal, required_markers in STRATEGY_SIGNAL_MARKERS
            if all(marker.lower() in text.lower() for marker in required_markers)
        ]
        if signals:
            sources.append({"path": relative_path.as_posix(), "signals": signals})
    return sources


def _test_functions_from_path(*, target_root: Path, changed_path: str) -> list[dict[str, Any]]:
    relative_path = Path(changed_path)
    if relative_path.suffix != ".py" or not relative_path.name.startswith("test_"):
        return []
    absolute_path = relative_path if relative_path.is_absolute() else target_root / relative_path
    text = _read_text_if_present(absolute_path)
    if not text:
        return []
    try:
        module = ast.parse(text)
    except SyntaxError:
        return []
    functions: list[dict[str, Any]] = []
    for node in module.body:
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
            continue
        assertions: list[str] = []
        helper_calls: list[str] = []
        decorator_names: list[str] = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                decorator = decorator.func
            if isinstance(decorator, ast.Attribute):
                decorator_names.append(decorator.attr)
            elif isinstance(decorator, ast.Name):
                decorator_names.append(decorator.id)
        for child in ast.walk(node):
            if isinstance(child, ast.Assert):
                assertions.append(ast.unparse(child.test) if hasattr(ast, "unparse") else "assert")
            elif isinstance(child, ast.Call):
                call = child.func
                if isinstance(call, ast.Name) and call.id.startswith("_"):
                    helper_calls.append(call.id)
                elif isinstance(call, ast.Attribute) and call.attr.startswith("_"):
                    helper_calls.append(call.attr)
        functions.append(
            {
                "name": node.name,
                "path": Path(changed_path).as_posix(),
                "line": node.lineno,
                "decorators": _dedupe(decorator_names),
                "helper_calls": _dedupe(helper_calls)[:8],
                "assertion_fragments": _dedupe(assertions)[:5],
                "assertion_count": len(assertions),
            }
        )
    return functions


def _test_group_key(name: str) -> str:
    stem = name.removeprefix("test_")
    parts = stem.split("_")
    while parts and parts[-1] in FIXTURE_VARIANT_TOKENS:
        parts.pop()
    if len(parts) < 3:
        return stem
    return "_".join(parts[: min(len(parts), 7)])


def _proof_owner_for_path(path: str) -> str:
    if path.startswith("packages/") and "/tests/" in path:
        return "package-local-behavior"
    if "generated_command" in path or "conformance" in path:
        return "conformance-contract"
    if path.startswith("docs/") or path.startswith(".agentic-workspace/docs/"):
        return "docs-manual-review"
    if path.startswith("tests/"):
        return "root-orchestration"
    return "unknown"


def _evidence_role_for_test(function: dict[str, Any]) -> str:
    name = str(function.get("name", "")).lower()
    path = str(function.get("path", "")).lower()
    if any(token in name for token in ("reject", "error", "invalid", "fail", "usage")):
        return "error-path"
    if any(token in name for token in ("edge", "stale", "missing", "gap", "empty")):
        return "edge-case"
    if "generated_command" in path or "generated_package" in name or "conformance" in name:
        return "generated-output-assertion"
    if any(token in name for token in ("adapter", "cli", "stdout", "stderr", "exit")):
        return "transport-adapter-compatibility"
    if "migration" in name or "residue" in name:
        return "migration-residue"
    if "characterization" in name:
        return "temporary-characterization"
    return "behavior-class-coverage"


def _strategy_disposition(*, role: str, proof_owner: str, group_size: int, declared_sources: list[dict[str, Any]]) -> str:
    declared_text = " ".join(signal for source in declared_sources for signal in source.get("signals", []))
    if group_size > 1 and "merge repeated" in declared_text:
        return "merge"
    if role == "generated-output-assertion" and proof_owner == "conformance-contract" and "conformance" in declared_text:
        return "convert-to-conformance"
    if role == "temporary-characterization":
        return "record-verification-evidence"
    if not declared_sources:
        return "needs-human-strategy-choice"
    return "keep"


def _evidence_strategy_payload(
    *,
    target_root: Path,
    changed_paths: list[str],
    task_text: str | None,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    declared_sources = _declared_strategy_sources(target_root=target_root)
    test_functions = [
        function
        for changed_path in changed_paths
        for function in _test_functions_from_path(target_root=target_root, changed_path=changed_path)
    ]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for function in test_functions:
        grouped.setdefault((str(function["path"]), _test_group_key(str(function["name"]))), []).append(function)

    observed_signals: list[dict[str, Any]] = []
    hotspot_paths = [
        path
        for path in changed_paths
        if path
        in {
            "tests/test_model_cli_harness.py",
            "tests/test_workspace_report_cli.py",
            "tests/test_workspace_start_preflight_cli.py",
            "tests/test_generated_command_package_proof_runner.py",
            "tests/test_workspace_proof_cli.py",
            "tests/test_workspace_implement_cli.py",
            "packages/planning/tests/test_summary.py",
            "packages/planning/tests/test_archive.py",
        }
    ]
    if hotspot_paths:
        observed_signals.append(
            {
                "source": "changed_paths",
                "signal": "hotspot test file touched",
                "paths": hotspot_paths,
                "confidence": "medium",
            }
        )
    if test_functions:
        observed_signals.append(
            {
                "source": "test_ast",
                "signal": "changed Python test functions collected by AST",
                "paths": _dedupe([str(function["path"]) for function in test_functions]),
                "confidence": "medium",
            }
        )
    if manifest.get("configured"):
        observed_signals.append(
            {
                "source": "verification_manifest",
                "signal": "verification manifest is configured",
                "paths": [str(manifest.get("path", VERIFICATION_MANIFEST_PATH.as_posix()))],
                "confidence": "medium",
            }
        )

    group_entries: list[dict[str, Any]] = []
    group_size_by_function: dict[str, int] = {}
    for (path, key), members in sorted(grouped.items()):
        if len(members) < 2:
            continue
        confidence = "high" if declared_sources else "medium"
        member_names = [str(member["name"]) for member in members]
        for member in members:
            group_size_by_function[f"{path}::{member['name']}"] = len(members)
        group_entries.append(
            {
                "id": key.replace("_", "-"),
                "paths": [path],
                "members": member_names,
                "group_role": "fixture-variant",
                "recommended_disposition": "merge",
                "confidence": confidence,
                "explanation": (
                    "Tests share a path and name prefix, and the declared strategy supports merging repeated checks; "
                    "inspect setup/assertion shape before merging."
                    if declared_sources
                    else "Tests share a path and name prefix; inspect setup/assertion shape before merging."
                ),
            }
        )

    evidence_items: list[dict[str, Any]] = []
    for function in test_functions:
        path = str(function["path"])
        item_id = f"{path}::{function['name']}"
        proof_owner = _proof_owner_for_path(path)
        role = _evidence_role_for_test(function)
        group_size = group_size_by_function.get(item_id, 1)
        disposition = _strategy_disposition(
            role="fixture-variant" if group_size > 1 else role,
            proof_owner=proof_owner,
            group_size=group_size,
            declared_sources=declared_sources,
        )
        signals = ["changed Python test function", f"proof owner inferred from path: {proof_owner}"]
        if group_size > 1:
            signals.append("shares name prefix with sibling tests")
        if function.get("helper_calls"):
            signals.append("uses helper calls")
        evidence_items.append(
            {
                "id": item_id,
                "path": path,
                "item_type": "test-function",
                "proof_owner": proof_owner,
                "evidence_role": "fixture-variant" if group_size > 1 else role,
                "strategy_fit": "fits-declared-strategy" if declared_sources else "strategy-unclear",
                "recommended_disposition": disposition,
                "confidence": "medium" if declared_sources else "low",
                "explanation": (
                    "Classification is based on repo-declared strategy signals, changed path ownership, and cheap AST facts; "
                    "it is diagnostic and not proof-equivalence."
                ),
                "observed_signals": signals,
                "required_replacement_evidence": ["retain behavior-class coverage"] if disposition in {"merge", "prune"} else [],
                "unsafe_to_prune_because": [] if disposition != "prune" else ["first-slice report does not prove semantic equivalence"],
            }
        )

    if declared_sources:
        declared_state = "declared"
        strategy_confidence = "high"
    elif observed_signals:
        declared_state = "not-declared"
        strategy_confidence = "low"
    else:
        declared_state = "not-declared"
        strategy_confidence = "unclear"
    agent_inferences = []
    if group_entries:
        agent_inferences.append(
            {
                "inference": "changed tests include likely fixture variants under shared behavior classes",
                "based_on": [
                    "shared test path",
                    "shared test name prefix",
                    "declared merge policy" if declared_sources else "observed AST grouping",
                ],
                "confidence": "medium" if declared_sources else "low",
            }
        )
    return {
        "kind": EVIDENCE_STRATEGY_KIND,
        "status": "ready" if declared_sources else "unclear" if observed_signals else "unavailable",
        "strategy_basis": {
            "declared_strategy_state": declared_state,
            "declared_strategy_sources": declared_sources,
            "observed_signal_state": "observed" if observed_signals else "absent",
            "observed_signals": observed_signals,
            "agent_inference_state": "inferred" if agent_inferences else "not-inferred",
            "agent_inferences": agent_inferences,
            "strategy_confidence": strategy_confidence,
            "strategy_summary": (
                "This repo declares behavior-contract coverage, scenario-matrix consolidation for repeated checks, "
                "contract-owned conformance for suitable generated behavior, and explicit replacement evidence before pruning."
                if declared_sources
                else "No declared host testing strategy was found; treat classifications as discovery prompts, not policy."
            ),
        },
        "evidence_items": evidence_items,
        "groups": group_entries,
        "summary": {
            "candidate_count": len(evidence_items),
            "high_confidence_merge_count": sum(1 for group in group_entries if group["confidence"] == "high"),
            "high_confidence_prune_count": 0,
            "needs_human_strategy_choice_count": sum(
                1 for item in evidence_items if item["recommended_disposition"] == "needs-human-strategy-choice"
            ),
            "ordinary_tests_touched": len(test_functions),
            "hotspot_files_touched": hotspot_paths,
            "candidate_threshold_note": (
                "Fewer than 10 high-confidence merge candidates were found with the first-slice exact-prefix heuristic; "
                "broader reductions need human review or stronger equivalence signals."
                if declared_sources and sum(1 for group in group_entries if group["confidence"] == "high") < 10
                else ""
            ),
        },
        "limits": [
            "No automatic deletion.",
            "No proof-equivalence guarantee.",
            "No universal testing strategy inferred.",
        ],
    }


def _required_string(*, payload: dict[str, Any], key: str, surface: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise VerificationUsageError(f"{surface} {key} must be a non-empty string.")
    return value.strip()


def _optional_string(*, payload: dict[str, Any], key: str, surface: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise VerificationUsageError(f"{surface} {key} must be a non-empty string when present.")
    return value.strip()


def _string_list(*, payload: dict[str, Any], key: str, surface: str) -> list[str]:
    value = payload.get(key, [])
    if value is None:
        return []
    if isinstance(value, str):
        raise VerificationUsageError(f"{surface} {key} must be a list of strings, not a scalar string.")
    if not isinstance(value, list):
        raise VerificationUsageError(f"{surface} {key} must be a list of strings.")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise VerificationUsageError(f"{surface} {key}[{index}] must be a non-empty string.")
        result.append(item.strip())
    return result


def _table(payload: dict[str, Any], key: str, *, surface: str) -> dict[str, Any]:
    value = payload.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise VerificationUsageError(f"{surface} [{key}] section must be a table.")
    return value


def _manifest_raw(*, target_root: Path) -> tuple[Path, dict[str, Any] | None]:
    manifest_path = target_root / VERIFICATION_MANIFEST_PATH
    if not manifest_path.exists():
        return manifest_path, None
    try:
        with manifest_path.open("rb") as handle:
            payload = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise VerificationUsageError(f"{VERIFICATION_MANIFEST_PATH.as_posix()} is invalid TOML: {exc}") from exc
    return manifest_path, payload


def _planning_refs(active_planning_record: dict[str, Any] | None) -> list[str]:
    if not isinstance(active_planning_record, dict):
        return []
    adaptive = active_planning_record.get("adaptive_assurance", {})
    adaptive = adaptive if isinstance(adaptive, dict) else {}
    refs: list[str] = []
    for raw in (
        active_planning_record.get("id"),
        active_planning_record.get("title"),
        active_planning_record.get("surface"),
        active_planning_record.get("next_action"),
    ):
        if str(raw).strip():
            refs.append(str(raw).strip())
    refs.extend(str(item).strip() for item in _list_payload(active_planning_record.get("minimal_refs")) if str(item).strip())
    refs.extend(str(item).strip() for item in _list_payload(active_planning_record.get("traceability_refs")) if str(item).strip())
    refs.extend(str(item).strip() for item in _list_payload(adaptive.get("requirement_refs")) if str(item).strip())
    refs.extend(str(item).strip() for item in _list_payload(adaptive.get("proof_profiles")) if str(item).strip())
    refs.extend(str(item).strip() for item in _list_payload(active_planning_record.get("assurance_requirement_refs")) if str(item).strip())
    refs.extend(str(item).strip() for item in _list_payload(active_planning_record.get("verification_protocol_refs")) if str(item).strip())
    refs.extend(str(item).strip() for item in _list_payload(active_planning_record.get("verification_refs")) if str(item).strip())
    return _dedupe(refs)


def _load_manifest(*, target_root: Path) -> dict[str, Any]:
    manifest_path, payload = _manifest_raw(target_root=target_root)
    if payload is None:
        return {
            "configured": False,
            "path": VERIFICATION_MANIFEST_PATH.as_posix(),
            "protocols": [],
            "scenarios": [],
            "evidence_bundles": [],
            "proof_routes": [],
            "known_gaps": [],
        }
    schema_version = payload.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        raise VerificationUsageError(f'{VERIFICATION_MANIFEST_PATH.as_posix()} schema_version must be "{SCHEMA_VERSION}".')
    unknown_top = sorted(set(payload) - {"schema_version", "protocols", "scenarios", "evidence_bundles", "proof_routes", "known_gaps"})
    if unknown_top:
        raise VerificationUsageError(
            f"{VERIFICATION_MANIFEST_PATH.as_posix()} contains unsupported top-level field(s): {', '.join(unknown_top)}."
        )

    scenarios_by_id: dict[str, dict[str, Any]] = {}
    raw_scenarios = _table(payload, "scenarios", surface=VERIFICATION_MANIFEST_PATH.as_posix())
    for scenario_id, raw_scenario in sorted(raw_scenarios.items()):
        surface = f"{VERIFICATION_MANIFEST_PATH.as_posix()} scenarios.{scenario_id}"
        if not isinstance(raw_scenario, dict):
            raise VerificationUsageError(f"{surface} must be a table.")
        unknown = sorted(
            set(raw_scenario)
            - {
                "protocol_id",
                "title",
                "steps",
                "expected_observations",
                "pass_evidence_labels",
                "fail_evidence_labels",
                "automation_hint",
                "manual_boundary",
            }
        )
        if unknown:
            raise VerificationUsageError(f"{surface} contains unsupported field(s): {', '.join(unknown)}.")
        scenario = {
            "id": str(scenario_id).strip(),
            "protocol_id": _required_string(payload=raw_scenario, key="protocol_id", surface=surface),
            "title": _required_string(payload=raw_scenario, key="title", surface=surface),
            "steps": _string_list(payload=raw_scenario, key="steps", surface=surface),
            "expected_observations": _string_list(payload=raw_scenario, key="expected_observations", surface=surface),
            "pass_evidence_labels": _string_list(payload=raw_scenario, key="pass_evidence_labels", surface=surface),
            "fail_evidence_labels": _string_list(payload=raw_scenario, key="fail_evidence_labels", surface=surface),
            "automation_hint": _optional_string(payload=raw_scenario, key="automation_hint", surface=surface),
            "manual_boundary": _optional_string(payload=raw_scenario, key="manual_boundary", surface=surface),
        }
        if not scenario["id"]:
            raise VerificationUsageError(f"{surface} id must be non-empty.")
        scenarios_by_id[scenario["id"]] = scenario

    protocols: list[dict[str, Any]] = []
    raw_protocols = _table(payload, "protocols", surface=VERIFICATION_MANIFEST_PATH.as_posix())
    activation_fields = {
        "applies_to_paths",
        "applies_to_task_markers",
        "assurance_requirement_refs",
        "proof_profiles",
        "planning_refs",
        "protocol_refs",
    }
    for protocol_id, raw_protocol in sorted(raw_protocols.items()):
        surface = f"{VERIFICATION_MANIFEST_PATH.as_posix()} protocols.{protocol_id}"
        if not isinstance(raw_protocol, dict):
            raise VerificationUsageError(f"{surface} must be a table.")
        unknown = sorted(
            set(raw_protocol)
            - {
                "title",
                "purpose",
                *activation_fields,
                "scenario_refs",
                "steps",
                "expected_evidence",
                "review_owner",
                "ownerless_reason",
                "authority_refs",
                "stale_when",
                "retention",
                "non_goals",
                "commands",
                "review_aids",
            }
        )
        if unknown:
            raise VerificationUsageError(f"{surface} contains unsupported field(s): {', '.join(unknown)}.")
        activation_values = {key: _string_list(payload=raw_protocol, key=key, surface=surface) for key in activation_fields}
        if not any(activation_values.values()):
            raise VerificationUsageError(f"{surface} requires at least one activation signal: {', '.join(sorted(activation_fields))}.")
        review_owner = _optional_string(payload=raw_protocol, key="review_owner", surface=surface)
        ownerless_reason = _optional_string(payload=raw_protocol, key="ownerless_reason", surface=surface)
        if not (review_owner or ownerless_reason):
            raise VerificationUsageError(f"{surface} requires review_owner or ownerless_reason.")
        scenario_refs = _string_list(payload=raw_protocol, key="scenario_refs", surface=surface)
        missing_scenarios = sorted(ref for ref in scenario_refs if ref not in scenarios_by_id)
        if missing_scenarios:
            raise VerificationUsageError(f"{surface} references unknown scenario(s): {', '.join(missing_scenarios)}.")
        protocol = {
            "id": str(protocol_id).strip(),
            "title": _required_string(payload=raw_protocol, key="title", surface=surface),
            "purpose": _required_string(payload=raw_protocol, key="purpose", surface=surface),
            **activation_values,
            "scenario_refs": scenario_refs,
            "steps": _string_list(payload=raw_protocol, key="steps", surface=surface),
            "expected_evidence": _string_list(payload=raw_protocol, key="expected_evidence", surface=surface),
            "review_owner": review_owner,
            "ownerless_reason": ownerless_reason,
            "authority_refs": _string_list(payload=raw_protocol, key="authority_refs", surface=surface),
            "stale_when": _string_list(payload=raw_protocol, key="stale_when", surface=surface),
            "retention": _optional_string(payload=raw_protocol, key="retention", surface=surface),
            "non_goals": _string_list(payload=raw_protocol, key="non_goals", surface=surface),
            "commands": _string_list(payload=raw_protocol, key="commands", surface=surface),
            "review_aids": _string_list(payload=raw_protocol, key="review_aids", surface=surface),
        }
        if not protocol["id"]:
            raise VerificationUsageError(f"{surface} id must be non-empty.")
        protocols.append(protocol)

    protocols_by_id = {str(protocol["id"]): protocol for protocol in protocols}
    protocol_ids = set(protocols_by_id)
    evidence_bundles: list[dict[str, Any]] = []
    raw_bundles = _table(payload, "evidence_bundles", surface=VERIFICATION_MANIFEST_PATH.as_posix())
    for bundle_id, raw_bundle in sorted(raw_bundles.items()):
        surface = f"{VERIFICATION_MANIFEST_PATH.as_posix()} evidence_bundles.{bundle_id}"
        if not isinstance(raw_bundle, dict):
            raise VerificationUsageError(f"{surface} must be a table.")
        unknown = sorted(
            set(raw_bundle)
            - {
                "protocol_id",
                "scenario_id",
                "task_refs",
                "issue_refs",
                "pr_refs",
                "changed_paths",
                "executor",
                "executed_at",
                "outcome",
                "evidence_items",
                "transcript_refs",
                "transcript_summaries",
                "residual_risk",
                "claim_boundaries",
                "reviewer",
                "retention_until",
                "stale_when",
                "redaction",
                "source_tool",
                "source_model",
                "post_score_reference",
            }
        )
        if unknown:
            raise VerificationUsageError(f"{surface} contains unsupported field(s): {', '.join(unknown)}.")
        protocol_id = _required_string(payload=raw_bundle, key="protocol_id", surface=surface)
        if protocol_id not in protocol_ids:
            raise VerificationUsageError(f"{surface} references unknown protocol_id {protocol_id}.")
        scenario_id = _optional_string(payload=raw_bundle, key="scenario_id", surface=surface)
        if scenario_id and scenario_id not in scenarios_by_id:
            raise VerificationUsageError(f"{surface} references unknown scenario_id {scenario_id}.")
        transcript_refs = _string_list(payload=raw_bundle, key="transcript_refs", surface=surface)
        transcript_summaries = _string_list(payload=raw_bundle, key="transcript_summaries", surface=surface)
        retention_until = _optional_string(payload=raw_bundle, key="retention_until", surface=surface)
        redaction = _optional_string(payload=raw_bundle, key="redaction", surface=surface)
        protocol_retention = _optional_string(
            payload=protocols_by_id[protocol_id],
            key="retention",
            surface=f"{VERIFICATION_MANIFEST_PATH.as_posix()} protocols.{protocol_id}",
        )
        if transcript_refs:
            missing_bounds: list[str] = []
            if not transcript_summaries:
                missing_bounds.append("transcript_summaries")
            if not (retention_until or protocol_retention):
                missing_bounds.append("retention_until or protocol retention")
            if not redaction:
                missing_bounds.append("redaction")
            if missing_bounds:
                raise VerificationUsageError(
                    f"{surface} transcript_refs requires bounded transcript metadata: {', '.join(missing_bounds)}."
                )
        evidence_bundles.append(
            {
                "id": str(bundle_id).strip(),
                "protocol_id": protocol_id,
                "scenario_id": scenario_id,
                "task_refs": _string_list(payload=raw_bundle, key="task_refs", surface=surface),
                "issue_refs": _string_list(payload=raw_bundle, key="issue_refs", surface=surface),
                "pr_refs": _string_list(payload=raw_bundle, key="pr_refs", surface=surface),
                "changed_paths": _string_list(payload=raw_bundle, key="changed_paths", surface=surface),
                "executor": _optional_string(payload=raw_bundle, key="executor", surface=surface),
                "executed_at": _optional_string(payload=raw_bundle, key="executed_at", surface=surface),
                "outcome": _optional_string(payload=raw_bundle, key="outcome", surface=surface) or "recorded",
                "evidence_items": _string_list(payload=raw_bundle, key="evidence_items", surface=surface),
                "transcript_refs": transcript_refs,
                "transcript_summaries": transcript_summaries,
                "residual_risk": _optional_string(payload=raw_bundle, key="residual_risk", surface=surface),
                "claim_boundaries": _string_list(payload=raw_bundle, key="claim_boundaries", surface=surface),
                "reviewer": _optional_string(payload=raw_bundle, key="reviewer", surface=surface),
                "retention_until": retention_until,
                "stale_when": _string_list(payload=raw_bundle, key="stale_when", surface=surface),
                "redaction": redaction,
                "source_tool": _optional_string(payload=raw_bundle, key="source_tool", surface=surface),
                "source_model": _optional_string(payload=raw_bundle, key="source_model", surface=surface),
                "post_score_reference": _optional_string(payload=raw_bundle, key="post_score_reference", surface=surface),
            }
        )

    proof_routes = _load_proof_routes(payload=payload, protocol_ids=protocol_ids, scenarios_by_id=scenarios_by_id)
    known_gaps = _load_known_gaps(payload=payload, protocol_ids=protocol_ids, scenarios_by_id=scenarios_by_id)
    return {
        "configured": True,
        "path": _repo_relative_path(manifest_path, target_root),
        "protocols": protocols,
        "scenarios": list(scenarios_by_id.values()),
        "evidence_bundles": evidence_bundles,
        "proof_routes": proof_routes,
        "known_gaps": known_gaps,
    }


def _load_proof_routes(
    *, payload: dict[str, Any], protocol_ids: set[str], scenarios_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    proof_routes: list[dict[str, Any]] = []
    raw_proof_routes = _table(payload, "proof_routes", surface=VERIFICATION_MANIFEST_PATH.as_posix())
    for route_id, raw_route in sorted(raw_proof_routes.items()):
        surface = f"{VERIFICATION_MANIFEST_PATH.as_posix()} proof_routes.{route_id}"
        if not isinstance(raw_route, dict):
            raise VerificationUsageError(f"{surface} must be a table.")
        unknown = sorted(
            set(raw_route)
            - {
                "protocol_refs",
                "scenario_refs",
                "assurance_requirement_refs",
                "proof_profiles",
                "commands",
                "review_aids",
                "proof_lane_hint",
                "reason",
            }
        )
        if unknown:
            raise VerificationUsageError(f"{surface} contains unsupported field(s): {', '.join(unknown)}.")
        protocol_refs = _string_list(payload=raw_route, key="protocol_refs", surface=surface)
        scenario_refs = _string_list(payload=raw_route, key="scenario_refs", surface=surface)
        missing_protocols = sorted(ref for ref in protocol_refs if ref not in protocol_ids)
        if missing_protocols:
            raise VerificationUsageError(f"{surface} references unknown protocol(s): {', '.join(missing_protocols)}.")
        missing_scenarios = sorted(ref for ref in scenario_refs if ref not in scenarios_by_id)
        if missing_scenarios:
            raise VerificationUsageError(f"{surface} references unknown scenario(s): {', '.join(missing_scenarios)}.")
        if not (protocol_refs or scenario_refs):
            raise VerificationUsageError(f"{surface} requires protocol_refs or scenario_refs.")
        commands = _string_list(payload=raw_route, key="commands", surface=surface)
        review_aids = _string_list(payload=raw_route, key="review_aids", surface=surface)
        if not (commands or review_aids):
            raise VerificationUsageError(f"{surface} requires commands or review_aids.")
        proof_routes.append(
            {
                "id": str(route_id).strip(),
                "protocol_refs": protocol_refs,
                "scenario_refs": scenario_refs,
                "assurance_requirement_refs": _string_list(payload=raw_route, key="assurance_requirement_refs", surface=surface),
                "proof_profiles": _string_list(payload=raw_route, key="proof_profiles", surface=surface),
                "commands": commands,
                "review_aids": review_aids,
                "proof_lane_hint": _optional_string(payload=raw_route, key="proof_lane_hint", surface=surface),
                "reason": _optional_string(payload=raw_route, key="reason", surface=surface),
            }
        )
    return proof_routes


def _load_known_gaps(
    *, payload: dict[str, Any], protocol_ids: set[str], scenarios_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    known_gaps: list[dict[str, Any]] = []
    raw_known_gaps = _table(payload, "known_gaps", surface=VERIFICATION_MANIFEST_PATH.as_posix())
    for gap_id, raw_gap in sorted(raw_known_gaps.items()):
        surface = f"{VERIFICATION_MANIFEST_PATH.as_posix()} known_gaps.{gap_id}"
        if not isinstance(raw_gap, dict):
            raise VerificationUsageError(f"{surface} must be a table.")
        unknown = sorted(
            set(raw_gap)
            - {
                "protocol_id",
                "scenario_id",
                "reason",
                "owner",
                "status",
                "evidence_labels",
                "blocked_claims",
                "residual_risk",
                "reopen_trigger",
                "created_from",
            }
        )
        if unknown:
            raise VerificationUsageError(f"{surface} contains unsupported field(s): {', '.join(unknown)}.")
        protocol_id = _required_string(payload=raw_gap, key="protocol_id", surface=surface)
        if protocol_id not in protocol_ids:
            raise VerificationUsageError(f"{surface} references unknown protocol_id {protocol_id}.")
        scenario_id = _optional_string(payload=raw_gap, key="scenario_id", surface=surface)
        if scenario_id and scenario_id not in scenarios_by_id:
            raise VerificationUsageError(f"{surface} references unknown scenario_id {scenario_id}.")
        known_gaps.append(
            {
                "id": str(gap_id).strip(),
                "protocol_id": protocol_id,
                "scenario_id": scenario_id,
                "reason": _required_string(payload=raw_gap, key="reason", surface=surface),
                "owner": _optional_string(payload=raw_gap, key="owner", surface=surface),
                "status": _optional_string(payload=raw_gap, key="status", surface=surface) or "open",
                "evidence_labels": _string_list(payload=raw_gap, key="evidence_labels", surface=surface),
                "blocked_claims": _string_list(payload=raw_gap, key="blocked_claims", surface=surface),
                "residual_risk": _optional_string(payload=raw_gap, key="residual_risk", surface=surface),
                "reopen_trigger": _optional_string(payload=raw_gap, key="reopen_trigger", surface=surface),
                "created_from": _optional_string(payload=raw_gap, key="created_from", surface=surface),
            }
        )
    return known_gaps


def _bundle_state(bundle: dict[str, Any], *, changed_paths: list[str]) -> dict[str, Any]:
    state = "present"
    retention_until = str(bundle.get("retention_until") or "").strip()
    if retention_until:
        try:
            if date.fromisoformat(retention_until) < date.today():
                state = "expired"
        except ValueError:
            state = "invalid-retention-date"
    stale_matches: list[str] = []
    for path in _normalize_changed_paths(changed_paths):
        for pattern in _list_payload(bundle.get("stale_when")):
            pattern_text = str(pattern).strip()
            if pattern_text and fnmatch.fnmatch(path, pattern_text):
                stale_matches.append(f"changed path matched {pattern_text}")
    if stale_matches and state == "present":
        state = "stale"
    return {
        "bundle_id": bundle.get("id"),
        "protocol_id": bundle.get("protocol_id"),
        "state": state,
        "outcome": bundle.get("outcome"),
        "evidence_items": bundle.get("evidence_items", []),
        "claim_boundaries": bundle.get("claim_boundaries", []),
        "retention_until": retention_until,
        "stale_because": _dedupe(stale_matches),
        "transcript_summary_count": len(_list_payload(bundle.get("transcript_summaries"))),
        "raw_transcript_ref_count": len(_list_payload(bundle.get("transcript_refs"))),
    }


def _match_protocol(
    *,
    protocol: dict[str, Any],
    changed_paths: list[str],
    task_text: str | None,
    active_planning_record: dict[str, Any] | None,
    assurance_requirements: dict[str, Any] | None,
) -> tuple[bool, list[str]]:
    applies_because: list[str] = []
    for path in _normalize_changed_paths(changed_paths):
        for pattern in _list_payload(protocol.get("applies_to_paths")):
            pattern_text = str(pattern).strip()
            if pattern_text and fnmatch.fnmatch(path, pattern_text):
                applies_because.append(f"changed path matched {pattern_text}")
        for pattern in _list_payload(protocol.get("stale_when")):
            pattern_text = str(pattern).strip()
            if pattern_text and fnmatch.fnmatch(path, pattern_text):
                applies_because.append(f"changed path may stale protocol via {pattern_text}")
    normalized_task = (task_text or "").lower()
    for marker in _list_payload(protocol.get("applies_to_task_markers")):
        marker_text = str(marker).strip()
        if marker_text and marker_text.lower() in normalized_task:
            applies_because.append(f"task marker matched {marker_text}")
    planning_refs = set(_planning_refs(active_planning_record))
    for ref in _list_payload(protocol.get("planning_refs")):
        ref_text = str(ref).strip()
        if ref_text and ref_text in planning_refs:
            applies_because.append(f"planning ref matched {ref_text}")
    for ref in _list_payload(protocol.get("protocol_refs")):
        ref_text = str(ref).strip()
        if ref_text and ref_text in planning_refs:
            applies_because.append(f"active planning protocol ref matched {ref_text}")
    active_requirements = []
    if isinstance(assurance_requirements, dict):
        active_requirements = [item for item in _list_payload(assurance_requirements.get("active")) if isinstance(item, dict)]
    for requirement in active_requirements:
        requirement_id = str(requirement.get("id", "")).strip()
        proof_profile = str(requirement.get("proof_profile") or "").strip()
        required_evidence = {str(item).strip() for item in _list_payload(requirement.get("required_evidence")) if str(item).strip()}
        protocol_evidence = {str(item).strip() for item in _list_payload(protocol.get("expected_evidence")) if str(item).strip()}
        if requirement_id and requirement_id in {str(item).strip() for item in _list_payload(protocol.get("assurance_requirement_refs"))}:
            applies_because.append(f"assurance requirement matched {requirement_id}")
        if proof_profile and proof_profile in {str(item).strip() for item in _list_payload(protocol.get("proof_profiles"))}:
            applies_because.append(f"assurance proof profile matched {proof_profile}")
        for label in sorted(required_evidence & protocol_evidence):
            applies_because.append(f"required evidence label matched {label}")
    return (bool(applies_because), _dedupe(applies_because))


def verification_report_payload(
    *,
    target_root: Path | None,
    changed_paths: list[str] | None = None,
    task_text: str | None = None,
    active_planning_record: dict[str, Any] | None = None,
    assurance_requirements: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if target_root is None:
        return {"kind": "agentic-workspace/verification/v1", "status": "unavailable", "configured": False}
    manifest = _load_manifest(target_root=target_root)
    configured_protocols = manifest["protocols"]
    configured_scenarios = manifest["scenarios"]
    evidence_bundles = manifest["evidence_bundles"]
    proof_routes = manifest["proof_routes"]
    known_gaps = manifest["known_gaps"]
    evidence_by_protocol: dict[str, list[dict[str, Any]]] = {}
    for bundle in evidence_bundles:
        evidence_by_protocol.setdefault(str(bundle.get("protocol_id", "")), []).append(bundle)

    active_protocols: list[dict[str, Any]] = []
    match_records: list[dict[str, Any]] = []
    evidence_status: list[dict[str, Any]] = []
    normalized_paths = _normalize_changed_paths(changed_paths)
    for protocol in configured_protocols:
        matched, applies_because = _match_protocol(
            protocol=protocol,
            changed_paths=normalized_paths,
            task_text=task_text,
            active_planning_record=active_planning_record,
            assurance_requirements=assurance_requirements,
        )
        match_records.append(
            {
                "id": protocol["id"],
                "matched": matched,
                "applies_because": applies_because,
                "non_match_reason": "" if matched else "no verification activation signal matched current work",
            }
        )
        bundles = evidence_by_protocol.get(str(protocol["id"]), [])
        bundle_state_by_id = {str(bundle.get("id")): _bundle_state(bundle, changed_paths=normalized_paths) for bundle in bundles}
        bundle_states = list(bundle_state_by_id.values())
        evidence_present = _dedupe(
            [
                str(item).strip()
                for bundle in bundles
                if bundle_state_by_id.get(str(bundle.get("id")), {}).get("state") == "present"
                for item in _list_payload(bundle.get("evidence_items"))
                if str(item).strip()
            ]
        )
        stale_evidence = _dedupe(
            [
                str(item).strip()
                for bundle in bundles
                if bundle_state_by_id.get(str(bundle.get("id")), {}).get("state") == "stale"
                for item in _list_payload(bundle.get("evidence_items"))
                if str(item).strip()
            ]
        )
        expected_evidence = [str(item).strip() for item in _list_payload(protocol.get("expected_evidence")) if str(item).strip()]
        missing_evidence = [item for item in expected_evidence if item not in evidence_present]
        stale_expected_evidence = [item for item in missing_evidence if item in stale_evidence]
        if matched:
            active_protocols.append(
                {
                    **protocol,
                    "applies_because": applies_because,
                    "evidence_bundle_ids": [b["id"] for b in bundles],
                    "authority_boundary": {
                        "kind": "agentic-workspace/authority-boundary/v1",
                        "surface": "verification.protocol",
                        "authority_class": "advisory-support",
                        "observed_by_aw": [
                            f"configured verification protocol {protocol['id']}",
                            *applies_because,
                        ],
                        "recommended_by_aw": ["run or record the configured verification evidence when agent judgment finds it relevant"],
                        "agent_owned_decisions": [
                            "whether the configured protocol is semantically relevant to the current work",
                            "whether evidence is sufficient for the intended claim boundary",
                        ],
                        "human_owned_decisions": ["acceptance or waiver of manual verification gaps"],
                        "reporting_rule": (
                            "Verification task-marker matches are configured protocol evidence; AW reports them and does not "
                            "classify user intent."
                        ),
                    },
                }
            )
            state = (
                "satisfied"
                if expected_evidence and not missing_evidence
                else "stale-evidence"
                if stale_expected_evidence
                else "missing-evidence"
                if missing_evidence
                else "matched"
            )
            evidence_status.append(
                {
                    "protocol_id": protocol["id"],
                    "state": state,
                    "applies_because": applies_because,
                    "expected_evidence": expected_evidence,
                    "evidence_present": evidence_present,
                    "stale_evidence": stale_evidence,
                    "stale_expected_evidence": stale_expected_evidence,
                    "missing_evidence": missing_evidence,
                    "evidence_bundle_ids": [str(bundle.get("id")) for bundle in bundles],
                    "bundle_states": bundle_states,
                    "residual_risk": [str(bundle.get("residual_risk")) for bundle in bundles if bundle.get("residual_risk")],
                    "claim_boundaries": _dedupe(
                        [
                            str(item).strip()
                            for bundle in bundles
                            for item in _list_payload(bundle.get("claim_boundaries"))
                            if str(item).strip()
                        ]
                    ),
                }
            )

    active_protocol_ids = {str(protocol.get("id", "")).strip() for protocol in active_protocols if isinstance(protocol, dict)}
    active_scenario_refs = {
        str(ref).strip() for protocol in active_protocols for ref in _list_payload(protocol.get("scenario_refs")) if str(ref).strip()
    }
    active_proof_routes = [
        route
        for route in proof_routes
        if active_protocol_ids.intersection({str(ref).strip() for ref in _list_payload(route.get("protocol_refs"))})
        or active_scenario_refs.intersection({str(ref).strip() for ref in _list_payload(route.get("scenario_refs"))})
    ]
    active_known_gaps = [
        gap for gap in known_gaps if str(gap.get("protocol_id", "")).strip() in active_protocol_ids and gap.get("status") != "closed"
    ]
    evidence_strategy = _evidence_strategy_payload(
        target_root=target_root,
        changed_paths=normalized_paths,
        task_text=task_text,
        manifest=manifest,
    )
    return {
        "kind": "agentic-workspace/verification/v1",
        "status": "attention"
        if any(item.get("state") in {"missing-evidence", "stale-evidence"} for item in evidence_status)
        else "matched"
        if active_protocols
        else "configured"
        if manifest["configured"]
        else "absent",
        "configured": bool(manifest["configured"]),
        "path": manifest["path"],
        "rule": "Verification owns reusable protocols and bounded evidence records; Assurance requires evidence and Closeout decides claim honesty.",
        "authority_boundary": {
            "kind": "agentic-workspace/authority-boundary/v1",
            "surface": "verification",
            "authority_class": "advisory-support" if active_protocols else "observed-facts",
            "observed_by_aw": ["verification manifest protocols/scenarios/evidence", "configured activation match facts"],
            "recommended_by_aw": ["use active protocols as proof guidance when agent judgment finds they fit the task"],
            "agent_owned_decisions": [
                "semantic fit of configured verification protocols",
                "proof sufficiency and claim-boundary judgment",
            ],
            "human_owned_decisions": ["acceptance or waiver of manual verification gaps"],
            "reporting_rule": ("Verification is configured evidence and proof guidance; AW does not decide the user's semantic intent."),
        },
        "protocol_count": len(configured_protocols),
        "scenario_count": len(configured_scenarios),
        "evidence_bundle_count": len(evidence_bundles),
        "proof_route_count": len(proof_routes),
        "known_gap_count": len(known_gaps),
        "configured_protocols": configured_protocols,
        "configured_scenarios": configured_scenarios,
        "proof_routes": proof_routes,
        "known_gaps": known_gaps,
        "evidence_bundles": evidence_bundles,
        "active_protocols": active_protocols,
        "active_proof_routes": active_proof_routes,
        "active_known_gaps": active_known_gaps,
        "active_count": len(active_protocols),
        "evidence_status": evidence_status,
        "evidence_bundle_status": [_bundle_state(bundle, changed_paths=normalized_paths) for bundle in evidence_bundles],
        "evidence_strategy": evidence_strategy,
        "match_evidence": {
            "observed_scope_source": ", ".join(
                source
                for source, present in (
                    ("changed paths", bool(normalized_paths)),
                    ("task text", bool(task_text)),
                    ("active planning", bool(active_planning_record)),
                    ("active assurance", bool(assurance_requirements and assurance_requirements.get("active_count"))),
                )
                if present
            )
            or "no active planning record, task text, changed paths, or assurance requirement",
            "match_count": len(active_protocols),
            "matching": match_records,
        },
        "transcript_policy": {
            "status": "active",
            "summary_first": True,
            "raw_transcript_refs": "optional-bounded",
            "hidden_oracle_rule": "Keep hidden/reference oracle material out of primary evaluator prompts; expose it only as post-score review metadata.",
            "memory_rule": "Promote only durable lessons or anti-rediscovery findings to Memory; do not store raw transcripts in Memory.",
        },
        "detail_command": "agentic-workspace report --target ./repo --section verification --format json",
    }
