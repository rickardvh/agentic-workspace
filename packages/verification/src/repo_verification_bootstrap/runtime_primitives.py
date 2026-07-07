from __future__ import annotations

import ast
import fnmatch
import tomllib
from datetime import date
from pathlib import Path
from typing import Any

VERIFICATION_MANIFEST_PATH = Path(".agentic-workspace/verification/manifest.toml")
PROOF_DECISION_PATH = Path(".agentic-workspace/verification/proof-decision.json")
PROOF_STRATEGY_PATH = Path(".agentic-workspace/verification/proof-strategy.toml")
SCHEMA_VERSION = "agentic-workspace/verification-manifest/v1"
EVIDENCE_STRATEGY_KIND = "agentic-workspace/verification-evidence-strategy/v1"
PROOF_GOVERNANCE_KIND = "agentic-workspace/verification-proof-governance/v1"
PROOF_DECISION_KIND = "agentic-workspace/verification-proof-decision/v1"
CORE_EVIDENCE_CONCEPTS = {
    "scenario_coverage": "Scenario or workflow coverage evidence.",
    "contract": "Contract, conformance, or interface evidence.",
    "conformance": "Conformance evidence against a declared protocol or spec.",
    "regression_prevention": "Evidence that a previous failure mode remains covered.",
    "characterization": "Characterization evidence for current behavior.",
    "manual_review": "Named manual review evidence.",
    "migration": "Migration or storage-transition evidence.",
    "export_integration": "Export, import, or integration evidence.",
    "security_review": "Security, access-control, or audit review evidence.",
    "compliance_uncertainty": "Explicit preservation of compliance or certification uncertainty.",
}

ASSURANCE_FIRST_LANE_CANDIDATES = (
    {
        "id": "access_audit",
        "title": "Access, authorization, and audit",
        "tokens": ("auth", "authz", "access", "permission", "role", "audit", "security"),
        "suggested_requirement": "access_audit_review",
        "suggested_protocol": "access_audit_verification",
    },
    {
        "id": "migrations_history",
        "title": "Migrations, storage, and history",
        "tokens": ("migration", "migrations", "schema", "storage", "database", "history"),
        "suggested_requirement": "migration_history_review",
        "suggested_protocol": "migration_history_verification",
    },
    {
        "id": "api_error_privacy",
        "title": "API, error, log, and privacy boundaries",
        "tokens": ("api", "error", "errors", "log", "logs", "privacy", "redaction"),
        "suggested_requirement": "api_error_privacy_review",
        "suggested_protocol": "api_error_privacy_verification",
    },
    {
        "id": "domain_legal_boundary",
        "title": "Domain and legal boundaries",
        "tokens": ("domain", "legal", "policy", "policies", "terms", "contract"),
        "suggested_requirement": "domain_legal_boundary_review",
        "suggested_protocol": "domain_legal_boundary_verification",
    },
    {
        "id": "compliance_uncertainty",
        "title": "Compliance uncertainty",
        "tokens": ("compliance", "regulatory", "certification", "certified", "soc2", "hipaa", "gdpr"),
        "suggested_requirement": "compliance_uncertainty_review",
        "suggested_protocol": "compliance_uncertainty_verification",
    },
    {
        "id": "integration_export_ai",
        "title": "Integration, export, and AI readiness",
        "tokens": ("integration", "integrations", "export", "import", "ai", "llm", "model"),
        "suggested_requirement": "integration_export_ai_review",
        "suggested_protocol": "integration_export_ai_verification",
    },
)

SOURCE_HINTS = [
    (Path("docs/maintainer/testing-strategy.md"), "candidate-host-strategy-source"),
    (Path("docs/maintainer/test-knowledge-inventory.md"), "candidate-test-knowledge-inventory"),
    (Path("docs/maintainer/aw-contract-test-replacement-inventory.md"), "candidate-host-strategy-source"),
    (Path(".agentic-workspace/docs/proof-surfaces-contract.md"), "candidate-host-strategy-source"),
    (Path("docs/host-repo-learning.md"), "candidate-host-strategy-source"),
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


def _read_json_if_present(path: Path) -> tuple[bool, Any, str]:
    text = _read_text_if_present(path)
    if not text:
        return False, None, ""
    import json

    try:
        return True, json.loads(text), ""
    except json.JSONDecodeError as exc:
        return True, None, str(exc)


GROUP_DECISION_QUESTIONS = [
    "Does this group represent one behavior class or separate regression records?",
    "Which member labels or historical facts must remain visible if this evidence is rewritten?",
    "What replacement evidence would make it safe to merge, move, convert, or prune this group?",
    "Which host-owned source should the agent read before deciding?",
]

ITEM_DECISION_QUESTIONS = [
    "What behavior claim does this evidence item currently preserve?",
    "Is this executable proof, historical regression knowledge, or both?",
    "Which owner should carry this evidence if the test is moved or retired?",
    "What replacement evidence must exist before changing this item?",
]

FILE_REVIEW_QUESTIONS = [
    "Which inventory row or host-owned source should the agent read for this file?",
    "Which behavior classes in this file are worth preserving as executable proof?",
    "Which historical regression facts should move to a non-executable record?",
    "What smaller proof surface should own stable behavior after migration?",
]

PROOF_GOVERNANCE_DECISIONS = [
    "add",
    "merge",
    "convert-to-conformance",
    "record-manual-evidence",
    "prune",
    "no-new-proof-needed",
    "needs-human-strategy-choice",
]

PROOF_INTENT_OPTIONS = [
    "behavior-unchanged",
    "target-parity",
    "workflow-routing",
    "migration-residue",
    "cli-compatibility",
    "temporary-characterization",
    "unknown",
]

EVIDENCE_DURABILITY_OPTIONS = [
    "permanent",
    "temporary",
    "replaceable",
    "unknown",
]

PROOF_GOVERNANCE_QUESTIONS = [
    "What host-repo testing or proof strategy applies to this surface?",
    "What trust question is being answered?",
    "What is the narrowest evidence that answers it under that strategy?",
    "Which owner should hold the evidence?",
    "Is this proof permanent, temporary, or replaceable by a host-preferred proof surface?",
    "What would make it safe to prune later?",
]

PROOF_DECISION_REQUIRED_FIELDS = [
    "selected_decision",
    "trust_question",
    "host_strategy_source",
    "proof_owner",
    "proof_intent",
    "evidence_durability",
    "narrowest_evidence",
    "prune_or_replacement_condition",
    "confidence",
    "residual_risk",
]

ORDINARY_TEST_GROWTH_OPTIONS = {
    "allowed",
    "requires-proof-decision",
    "discouraged",
    "unknown",
}


def _candidate_strategy_sources(*, target_root: Path) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for relative_path, source_role in SOURCE_HINTS:
        absolute_path = target_root / relative_path
        if not absolute_path.is_file():
            continue
        sources.append(
            {
                "path": relative_path.as_posix(),
                "source_role": source_role,
                "authority": "uninterpreted-source",
            }
        )
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


def _proof_governance_payload(
    *,
    candidate_sources: list[dict[str, Any]],
    changed_paths: list[str],
    test_functions: list[dict[str, Any]],
    group_entries: list[dict[str, Any]],
    task_text: str | None,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    observed_facts: list[dict[str, Any]] = []
    if task_text:
        observed_facts.append(
            {
                "source": "task_text",
                "fact": "task text supplied",
                "confidence": "medium",
            }
        )
    if changed_paths:
        observed_facts.append(
            {
                "source": "changed_paths",
                "fact": "changed paths supplied",
                "paths": changed_paths,
                "confidence": "medium",
            }
        )
    if test_functions:
        observed_facts.append(
            {
                "source": "test_ast",
                "fact": "changed Python test functions collected by AST",
                "paths": _dedupe([str(function["path"]) for function in test_functions]),
                "count": len(test_functions),
                "confidence": "medium",
            }
        )
    if group_entries:
        observed_facts.append(
            {
                "source": "test_ast",
                "fact": "same-file test name-prefix groups detected",
                "count": len(group_entries),
                "confidence": "low",
            }
        )
    if manifest.get("configured"):
        observed_facts.append(
            {
                "source": "verification_manifest",
                "fact": "verification manifest is configured",
                "paths": [str(manifest.get("path", VERIFICATION_MANIFEST_PATH.as_posix()))],
                "confidence": "medium",
            }
        )
    status = "attention" if observed_facts or candidate_sources else "unavailable"
    return {
        "kind": PROOF_GOVERNANCE_KIND,
        "status": status,
        "decision_authority": "agent",
        "available_decisions": PROOF_GOVERNANCE_DECISIONS,
        "proof_intent_options": PROOF_INTENT_OPTIONS,
        "proof_owner_options": [
            "root-orchestration",
            "package-local-behavior",
            "conformance-contract",
            "verification-evidence",
            "memory-lesson",
            "docs-manual-review",
            "unknown",
        ],
        "evidence_durability_options": EVIDENCE_DURABILITY_OPTIONS,
        "candidate_context": {
            "changed_path_count": len(changed_paths),
            "ordinary_test_function_count": len(test_functions),
            "group_count": len(group_entries),
            "candidate_strategy_source_count": len(candidate_sources),
            "verification_manifest_configured": bool(manifest.get("configured")),
            "task_text_present": bool(task_text),
        },
        "observed_facts": observed_facts,
        "pre_test_decision_questions": PROOF_GOVERNANCE_QUESTIONS,
        "agent_decision_template": {
            "selected_decision": "unset-agent-owned",
            "trust_question": "unset-agent-owned",
            "proof_intent": "unset-agent-owned",
            "narrowest_evidence": "unset-agent-owned",
            "evidence_owner": "unset-agent-owned",
            "durability": "unset-agent-owned",
            "safe_to_prune_when": "unset-agent-owned",
        },
        "limits": [
            "No decision is assigned by Verification.",
            "No host strategy is inferred from prose.",
            "No new proof requirement is created.",
            "No pruning, merging, or conversion is authorized.",
        ],
    }


def _proof_decision_lifecycle(*, decision: dict[str, Any], changed_paths: list[str]) -> dict[str, Any]:
    durability = str(decision.get("evidence_durability", "")).strip()
    retention_until = str(decision.get("retention_until", "")).strip()
    replacement_owner = str(decision.get("replacement_owner", "")).strip()
    review_trigger = str(decision.get("review_trigger", "")).strip()
    stale_when = [str(item).strip() for item in _list_payload(decision.get("stale_when")) if str(item).strip()]
    stale_matches: list[str] = []
    for path in _normalize_changed_paths(changed_paths):
        for pattern in stale_when:
            if fnmatch.fnmatch(path, pattern):
                stale_matches.append(f"changed path matched {pattern}")
    invalid_fields: list[str] = []
    expired = False
    if retention_until:
        try:
            expired = date.fromisoformat(retention_until) < date.today()
        except ValueError:
            invalid_fields.append("retention_until")
    state = "unknown"
    if durability == "permanent":
        state = "permanent"
    elif durability in {"temporary", "replaceable"}:
        if invalid_fields:
            state = "invalid"
        elif expired:
            state = "expired"
        elif stale_matches:
            state = "stale"
        else:
            state = "current"
    return {
        "state": state,
        "retention_until": retention_until,
        "stale_when": stale_when,
        "stale_because": _dedupe(stale_matches),
        "replacement_owner": replacement_owner,
        "review_trigger": review_trigger,
        "review_needed": state in {"expired", "stale", "invalid"},
        "invalid_fields": invalid_fields,
        "limits": [
            "Lifecycle state is derived only from explicit proof-decision fields.",
            "Verification does not decide whether temporary evidence remains sufficient.",
        ],
    }


def _proof_decision_payload(*, target_root: Path, changed_paths: list[str]) -> dict[str, Any]:
    decision_path = target_root / PROOF_DECISION_PATH
    exists, payload, parse_error = _read_json_if_present(decision_path)
    base = {
        "kind": PROOF_DECISION_KIND,
        "path": PROOF_DECISION_PATH.as_posix(),
        "authority": "agent-authored",
        "decision_authority": "agent",
        "limits": [
            "Verification validates the record shape but does not create the decision.",
            "No missing field is inferred from prose, paths, names, or AW conventions.",
        ],
    }
    if not exists:
        return {
            **base,
            "status": "missing",
            "missing_fields": PROOF_DECISION_REQUIRED_FIELDS,
            "invalid_fields": [],
            "decision": {},
            "lifecycle": {},
        }
    if parse_error:
        return {
            **base,
            "status": "invalid",
            "parse_error": parse_error,
            "missing_fields": [],
            "invalid_fields": ["json"],
            "decision": {},
            "lifecycle": {},
        }
    if not isinstance(payload, dict):
        return {
            **base,
            "status": "invalid",
            "missing_fields": [],
            "invalid_fields": ["root"],
            "decision": {},
            "lifecycle": {},
        }
    decision = payload.get("proof_decision", payload)
    if not isinstance(decision, dict):
        return {
            **base,
            "status": "invalid",
            "missing_fields": [],
            "invalid_fields": ["proof_decision"],
            "decision": {},
            "lifecycle": {},
        }
    missing_fields = [field for field in PROOF_DECISION_REQUIRED_FIELDS if not str(decision.get(field, "")).strip()]
    invalid_fields: list[str] = []
    selected_decision = str(decision.get("selected_decision", "")).strip()
    if selected_decision and selected_decision not in PROOF_GOVERNANCE_DECISIONS:
        invalid_fields.append("selected_decision")
    proof_owner = str(decision.get("proof_owner", "")).strip()
    if proof_owner and proof_owner not in {
        "root-orchestration",
        "package-local-behavior",
        "conformance-contract",
        "verification-evidence",
        "memory-lesson",
        "docs-manual-review",
        "unknown",
    }:
        invalid_fields.append("proof_owner")
    proof_intent = str(decision.get("proof_intent", "")).strip()
    if proof_intent and proof_intent not in PROOF_INTENT_OPTIONS:
        invalid_fields.append("proof_intent")
    durability = str(decision.get("evidence_durability", "")).strip()
    if durability and durability not in EVIDENCE_DURABILITY_OPTIONS:
        invalid_fields.append("evidence_durability")
    confidence = str(decision.get("confidence", "")).strip()
    if confidence and confidence not in {"high", "medium", "low"}:
        invalid_fields.append("confidence")
    lifecycle = _proof_decision_lifecycle(decision=decision, changed_paths=changed_paths)
    invalid_fields.extend(field for field in lifecycle["invalid_fields"] if field not in invalid_fields)
    status = "present"
    if invalid_fields:
        status = "invalid"
    elif missing_fields:
        status = "incomplete"
    return {
        **base,
        "status": status,
        "missing_fields": missing_fields,
        "invalid_fields": invalid_fields,
        "decision": {field: decision.get(field, "") for field in PROOF_DECISION_REQUIRED_FIELDS},
        "lifecycle": lifecycle,
    }


def _is_python_test_path(path: str) -> bool:
    candidate = Path(path)
    return candidate.suffix == ".py" and candidate.name.startswith("test_")


def _regression_sprawl_payload(
    *,
    target_root: Path,
    changed_paths: list[str],
    test_functions: list[dict[str, Any]],
    group_entries: list[dict[str, Any]],
    proof_decision: dict[str, Any],
) -> dict[str, Any]:
    normalized_changed = _normalize_changed_paths(changed_paths)
    changed_test_paths = [path for path in normalized_changed if _is_python_test_path(path)]
    deleted_or_missing_test_paths = [
        path for path in changed_test_paths if not ((Path(path) if Path(path).is_absolute() else target_root / Path(path)).exists())
    ]
    generated_output_assertions = [
        {
            "id": f"{function['path']}::{function['name']}",
            "path": function["path"],
            "matched_fragments": [
                fragment
                for fragment in function.get("assertion_fragments", [])
                if any(token in str(fragment).lower() for token in ("stdout", "stderr", "output", "contains"))
            ],
        }
        for function in test_functions
    ]
    generated_output_assertions = [item for item in generated_output_assertions if item["matched_fragments"]]
    proof_status = str(proof_decision.get("status", "missing"))
    decision_gap = proof_status in {"missing", "incomplete", "invalid"}
    has_sprawl_context = bool(
        changed_test_paths or deleted_or_missing_test_paths or test_functions or group_entries or generated_output_assertions
    )
    return {
        "kind": "agentic-workspace/verification-regression-sprawl/v1",
        "status": "attention" if has_sprawl_context else "unavailable",
        "authority": "diagnostic-facts",
        "test_files_touched": changed_test_paths,
        "deleted_or_missing_test_files": deleted_or_missing_test_paths,
        "ordinary_test_function_count": len(test_functions),
        "likely_fixture_variant_group_count": len(group_entries),
        "generated_output_assertion_count": len(generated_output_assertions),
        "generated_output_assertions": generated_output_assertions,
        "proof_decision_status": proof_status,
        "missing_or_incomplete_proof_decision": decision_gap if has_sprawl_context else False,
        "review_questions": [
            "Is this evidence preserving a durable behavior class or an incident-specific regression record?",
            "Can repeated fixtures become a scenario matrix without losing labels or historical facts?",
            "Should generated output assertions move to a named contract or remain local executable proof?",
            "What proof-decision record explains any ordinary test growth or deletion?",
        ],
        "limits": [
            "No test is classified as redundant.",
            "No deletion, merge, or conformance conversion is recommended by this diagnostic.",
            "Generated-output assertion detection is a shallow AST substring signal.",
        ],
    }


def _structured_strategy_hints_payload(*, target_root: Path) -> dict[str, Any]:
    strategy_path = target_root / PROOF_STRATEGY_PATH
    base = {
        "path": PROOF_STRATEGY_PATH.as_posix(),
        "authority": "host-structured-config",
        "limits": [
            "Only structured enum fields are interpreted.",
            "Free-text host strategy prose remains uninterpreted.",
        ],
    }
    if not strategy_path.is_file():
        return {
            **base,
            "status": "absent",
            "hints": {},
            "invalid_fields": [],
        }
    try:
        with strategy_path.open("rb") as handle:
            payload = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        return {
            **base,
            "status": "invalid",
            "parse_error": str(exc),
            "hints": {},
            "invalid_fields": ["toml"],
        }
    raw_hints = payload.get("proof_strategy", payload)
    if not isinstance(raw_hints, dict):
        return {
            **base,
            "status": "invalid",
            "hints": {},
            "invalid_fields": ["proof_strategy"],
        }
    hints = {
        "strategy_source": str(raw_hints.get("strategy_source", "")).strip(),
        "ordinary_test_growth": str(raw_hints.get("ordinary_test_growth", "")).strip() or "unknown",
        "preferred_owner_vocab": [str(item).strip() for item in _list_payload(raw_hints.get("preferred_owner_vocab")) if str(item).strip()],
        "proof_intent_vocab": [str(item).strip() for item in _list_payload(raw_hints.get("proof_intent_vocab")) if str(item).strip()],
    }
    invalid_fields: list[str] = []
    if hints["ordinary_test_growth"] not in ORDINARY_TEST_GROWTH_OPTIONS:
        invalid_fields.append("ordinary_test_growth")
    invalid_owner_values = [
        item
        for item in hints["preferred_owner_vocab"]
        if item
        not in {
            "root-orchestration",
            "package-local-behavior",
            "conformance-contract",
            "verification-evidence",
            "memory-lesson",
            "docs-manual-review",
            "unknown",
        }
    ]
    if invalid_owner_values:
        invalid_fields.append("preferred_owner_vocab")
    invalid_intents = [item for item in hints["proof_intent_vocab"] if item not in PROOF_INTENT_OPTIONS]
    if invalid_intents:
        invalid_fields.append("proof_intent_vocab")
    return {
        **base,
        "status": "invalid" if invalid_fields else "present",
        "hints": hints,
        "invalid_fields": invalid_fields,
    }


def _structured_strategy_state(structured_hints: dict[str, Any]) -> tuple[str, str]:
    if structured_hints.get("status") != "present":
        return "not-declared", "unclear"
    hints = structured_hints.get("hints")
    hints = hints if isinstance(hints, dict) else {}
    strategy_source = str(hints.get("strategy_source", "")).strip()
    has_meaningful_strategy_field = bool(
        str(hints.get("ordinary_test_growth", "")).strip() not in {"", "unknown"}
        or _list_payload(hints.get("preferred_owner_vocab"))
        or _list_payload(hints.get("proof_intent_vocab"))
    )
    if strategy_source and has_meaningful_strategy_field:
        return "declared", "medium"
    return "partially-declared", "low"


def _evidence_strategy_payload(
    *,
    target_root: Path,
    changed_paths: list[str],
    task_text: str | None,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    candidate_sources = _candidate_strategy_sources(target_root=target_root)
    structured_hints = _structured_strategy_hints_payload(target_root=target_root)
    test_functions = [
        function
        for changed_path in changed_paths
        for function in _test_functions_from_path(target_root=target_root, changed_path=changed_path)
    ]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for function in test_functions:
        grouped.setdefault((str(function["path"]), _test_group_key(str(function["name"]))), []).append(function)

    observed_signals: list[dict[str, Any]] = []
    if changed_paths:
        observed_signals.append(
            {
                "source": "changed_paths",
                "signal": "changed paths supplied",
                "paths": changed_paths,
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
        member_names = [str(member["name"]) for member in members]
        for member in members:
            group_size_by_function[f"{path}::{member['name']}"] = len(members)
        group_entries.append(
            {
                "id": key.replace("_", "-"),
                "paths": [path],
                "members": member_names,
                "group_role": "fixture-variant",
                "recommended_disposition": "needs-human-strategy-choice",
                "confidence": "low",
                "explanation": (
                    "Tests share a path and name prefix. Verification surfaces this as a review question; "
                    "the agent must decide whether the host strategy supports merging."
                ),
                "decision_questions": GROUP_DECISION_QUESTIONS,
            }
        )

    evidence_items: list[dict[str, Any]] = []
    for function in test_functions:
        path = str(function["path"])
        item_id = f"{path}::{function['name']}"
        group_size = group_size_by_function.get(item_id, 1)
        signals = ["changed Python test function"]
        if group_size > 1:
            signals.append("shares name prefix with sibling tests")
        if function.get("helper_calls"):
            signals.append("uses helper calls")
        evidence_items.append(
            {
                "id": item_id,
                "path": path,
                "item_type": "test-function",
                "proof_owner": "unknown",
                "evidence_role": "fixture-variant" if group_size > 1 else "unknown",
                "strategy_fit": "strategy-unclear",
                "recommended_disposition": "needs-human-strategy-choice",
                "confidence": "low",
                "explanation": (
                    "Verification reports structural evidence facts only. The agent must interpret host strategy and decide disposition."
                ),
                "observed_signals": signals,
                "decision_questions": ITEM_DECISION_QUESTIONS,
                "required_replacement_evidence": [],
                "unsafe_to_prune_because": [],
            }
        )

    file_summaries: list[dict[str, Any]] = []
    functions_by_path: dict[str, list[dict[str, Any]]] = {}
    for function in test_functions:
        functions_by_path.setdefault(str(function["path"]), []).append(function)
    grouped_member_ids = set(group_size_by_function)
    for path, functions in sorted(functions_by_path.items()):
        file_summaries.append(
            {
                "path": path,
                "test_function_count": len(functions),
                "grouped_test_function_count": sum(1 for function in functions if f"{path}::{function['name']}" in grouped_member_ids),
                "helper_call_count": sum(len(function.get("helper_calls", [])) for function in functions),
                "assertion_count": sum(int(function.get("assertion_count", 0)) for function in functions),
                "review_questions": FILE_REVIEW_QUESTIONS,
            }
        )

    structured_declared_state, structured_strategy_confidence = _structured_strategy_state(structured_hints)
    if structured_declared_state == "declared":
        declared_state = structured_declared_state
        strategy_confidence = structured_strategy_confidence
    elif structured_declared_state == "partially-declared":
        declared_state = structured_declared_state
        strategy_confidence = structured_strategy_confidence
    elif candidate_sources:
        declared_state = "partially-declared"
        strategy_confidence = "low"
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
                    "observed AST grouping",
                ],
                "confidence": "low",
            }
        )
    proof_governance = _proof_governance_payload(
        candidate_sources=candidate_sources,
        changed_paths=changed_paths,
        test_functions=test_functions,
        group_entries=group_entries,
        task_text=task_text,
        manifest=manifest,
    )
    proof_decision = _proof_decision_payload(target_root=target_root, changed_paths=changed_paths)
    regression_sprawl = _regression_sprawl_payload(
        target_root=target_root,
        changed_paths=changed_paths,
        test_functions=test_functions,
        group_entries=group_entries,
        proof_decision=proof_decision,
    )
    return {
        "kind": EVIDENCE_STRATEGY_KIND,
        "status": "attention" if candidate_sources or observed_signals else "unavailable",
        "strategy_basis": {
            "declared_strategy_state": declared_state,
            "declared_strategy_sources": [],
            "structured_strategy_hints": structured_hints,
            "candidate_strategy_sources": candidate_sources,
            "matched_strategy_signals": [],
            "observed_signal_state": "observed" if observed_signals else "absent",
            "observed_signals": observed_signals,
            "agent_inference_state": "inferred" if agent_inferences else "not-inferred",
            "agent_inferences": agent_inferences,
            "strategy_confidence": strategy_confidence,
            "strategy_summary": (
                "Verification found candidate host-owned strategy sources but did not interpret their prose. "
                "The agent must read them and decide how the evidence fits."
                if candidate_sources
                else "No candidate host strategy source was found; the agent must decide how to interpret the evidence."
            ),
            "decision_questions": [
                "Which host-owned strategy source, if any, should govern this evidence?",
                "Do grouped tests represent one behavior class or separate regression records?",
                "What replacement evidence would be required before merging, moving, converting, or pruning evidence?",
            ],
        },
        "evidence_items": evidence_items,
        "groups": group_entries,
        "inventory_review": {
            "candidate_inventory_sources": [
                source for source in candidate_sources if source["source_role"] == "candidate-test-knowledge-inventory"
            ],
            "test_file_summaries": file_summaries,
            "limits": [
                "Counts are AST diagnostics, not proof of coverage.",
                "File summaries do not authorize deletion or merge decisions.",
            ],
        },
        "proof_governance": proof_governance,
        "proof_decision": proof_decision,
        "regression_sprawl": regression_sprawl,
        "summary": {
            "candidate_count": len(evidence_items),
            "high_confidence_merge_count": sum(1 for group in group_entries if group["confidence"] == "high"),
            "high_confidence_prune_count": 0,
            "needs_human_strategy_choice_count": sum(
                1 for item in evidence_items if item["recommended_disposition"] == "needs-human-strategy-choice"
            ),
            "ordinary_tests_touched": len(test_functions),
            "hotspot_files_touched": [],
            "candidate_threshold_note": (
                "Verification does not assign high-confidence merge or prune candidates from prose or name matching; "
                "the agent must make the strategy decision."
                if group_entries
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


def _load_evidence_concepts(*, payload: dict[str, Any]) -> dict[str, Any]:
    raw_concepts = _table(payload, "evidence_concepts", surface=VERIFICATION_MANIFEST_PATH.as_posix())
    declared: dict[str, dict[str, Any]] = {}
    invalid: list[dict[str, str]] = []
    for concept_id, raw_concept in sorted(raw_concepts.items()):
        surface = f"{VERIFICATION_MANIFEST_PATH.as_posix()} evidence_concepts.{concept_id}"
        if not isinstance(raw_concept, dict):
            raise VerificationUsageError(f"{surface} must be a table.")
        unknown = sorted(set(raw_concept) - {"title", "meaning", "owner", "claim_effect", "render_as"})
        if unknown:
            raise VerificationUsageError(f"{surface} contains unsupported field(s): {', '.join(unknown)}.")
        concept_key = str(concept_id).strip()
        if not concept_key.startswith("host:"):
            invalid.append(
                {
                    "id": concept_key,
                    "reason": "host-declared evidence concepts must use the host:<term> namespace",
                    "source": surface,
                }
            )
            continue
        declared[concept_key] = {
            "id": concept_key,
            "kind": "host-declared",
            "title": _required_string(payload=raw_concept, key="title", surface=surface),
            "meaning": _required_string(payload=raw_concept, key="meaning", surface=surface),
            "owner": _optional_string(payload=raw_concept, key="owner", surface=surface) or "host-repo",
            "claim_effect": _optional_string(payload=raw_concept, key="claim_effect", surface=surface) or "reviewable-evidence",
            "render_as": _optional_string(payload=raw_concept, key="render_as", surface=surface) or concept_key,
            "source": surface,
        }
    return {
        "kind": "agentic-workspace/verification-evidence-concepts/v1",
        "core": [
            {"id": concept_id, "kind": "core", "meaning": meaning, "source": "AW core vocabulary"}
            for concept_id, meaning in sorted(CORE_EVIDENCE_CONCEPTS.items())
        ],
        "declared_host": list(declared.values()),
        "declared_host_by_id": declared,
        "invalid_declarations": invalid,
    }


def _evidence_concept_usage(*, labels: list[str], concepts: dict[str, Any]) -> dict[str, Any]:
    declared = concepts.get("declared_host_by_id", {}) if isinstance(concepts, dict) else {}
    declared = declared if isinstance(declared, dict) else {}
    used: list[dict[str, Any]] = []
    degraded: list[dict[str, str]] = []
    for label in labels:
        normalized = str(label).strip()
        if not normalized:
            continue
        if normalized in CORE_EVIDENCE_CONCEPTS:
            used.append(
                {
                    "id": normalized,
                    "kind": "core",
                    "meaning": CORE_EVIDENCE_CONCEPTS[normalized],
                    "source": "AW core vocabulary",
                }
            )
        elif normalized.startswith("host:") and normalized in declared:
            used.append(dict(declared[normalized]))
        elif normalized.startswith("host:"):
            degraded.append(
                {
                    "id": normalized,
                    "state": "undeclared-host-concept",
                    "reason": "Declare this host evidence concept under [evidence_concepts] before relying on it for proof or closeout output.",
                }
            )
        else:
            degraded.append(
                {
                    "id": normalized,
                    "state": "legacy-unclassified-label",
                    "reason": "Use a core concept or a declared host:<term> concept for machine-readable proof semantics.",
                }
            )
    return {
        "used": used,
        "degraded": degraded,
        "status": "attention" if degraded else "declared" if used else "none",
    }


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
            "evidence_concepts": _load_evidence_concepts(payload={}),
        }
    schema_version = payload.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        raise VerificationUsageError(f'{VERIFICATION_MANIFEST_PATH.as_posix()} schema_version must be "{SCHEMA_VERSION}".')
    unknown_top = sorted(
        set(payload) - {"schema_version", "protocols", "scenarios", "evidence_bundles", "proof_routes", "known_gaps", "evidence_concepts"}
    )
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

    evidence_concepts = _load_evidence_concepts(payload=payload)
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
        "evidence_concepts": evidence_concepts,
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
) -> tuple[bool, list[str], list[dict[str, Any]]]:
    applies_because: list[str] = []
    match_signals: list[dict[str, Any]] = []
    for path in _normalize_changed_paths(changed_paths):
        for pattern in _list_payload(protocol.get("applies_to_paths")):
            pattern_text = str(pattern).strip()
            if pattern_text and fnmatch.fnmatch(path, pattern_text):
                reason = f"changed path matched {pattern_text}"
                applies_because.append(reason)
                match_signals.append(
                    {
                        "signal_type": "changed_path",
                        "authority": "structured-input",
                        "priority": "structured",
                        "value": path,
                        "matched": pattern_text,
                        "reason": reason,
                    }
                )
        for pattern in _list_payload(protocol.get("stale_when")):
            pattern_text = str(pattern).strip()
            if pattern_text and fnmatch.fnmatch(path, pattern_text):
                reason = f"changed path may stale protocol via {pattern_text}"
                applies_because.append(reason)
                match_signals.append(
                    {
                        "signal_type": "stale_path",
                        "authority": "structured-input",
                        "priority": "structured",
                        "value": path,
                        "matched": pattern_text,
                        "reason": reason,
                    }
                )
    normalized_task = (task_text or "").lower()
    for marker in _list_payload(protocol.get("applies_to_task_markers")):
        marker_text = str(marker).strip()
        if marker_text and marker_text.lower() in normalized_task:
            reason = f"task marker matched {marker_text}"
            applies_because.append(reason)
            match_signals.append(
                {
                    "signal_type": "task_marker",
                    "authority": "host-declared-verification-manifest",
                    "priority": "advisory",
                    "value": marker_text,
                    "matched": marker_text,
                    "reason": reason,
                    "agent_decision_required": True,
                }
            )
    planning_refs = set(_planning_refs(active_planning_record))
    for ref in _list_payload(protocol.get("planning_refs")):
        ref_text = str(ref).strip()
        if ref_text and ref_text in planning_refs:
            reason = f"planning ref matched {ref_text}"
            applies_because.append(reason)
            match_signals.append(
                {
                    "signal_type": "planning_ref",
                    "authority": "structured-planning-state",
                    "priority": "structured",
                    "value": ref_text,
                    "matched": ref_text,
                    "reason": reason,
                }
            )
    for ref in _list_payload(protocol.get("protocol_refs")):
        ref_text = str(ref).strip()
        if ref_text and ref_text in planning_refs:
            reason = f"active planning protocol ref matched {ref_text}"
            applies_because.append(reason)
            match_signals.append(
                {
                    "signal_type": "protocol_ref",
                    "authority": "structured-planning-state",
                    "priority": "structured",
                    "value": ref_text,
                    "matched": ref_text,
                    "reason": reason,
                }
            )
    active_requirements = []
    if isinstance(assurance_requirements, dict):
        active_requirements = [item for item in _list_payload(assurance_requirements.get("active")) if isinstance(item, dict)]
    for requirement in active_requirements:
        requirement_id = str(requirement.get("id", "")).strip()
        proof_profile = str(requirement.get("proof_profile") or "").strip()
        required_evidence = {str(item).strip() for item in _list_payload(requirement.get("required_evidence")) if str(item).strip()}
        protocol_evidence = {str(item).strip() for item in _list_payload(protocol.get("expected_evidence")) if str(item).strip()}
        if requirement_id and requirement_id in {str(item).strip() for item in _list_payload(protocol.get("assurance_requirement_refs"))}:
            reason = f"assurance requirement matched {requirement_id}"
            applies_because.append(reason)
            match_signals.append(
                {
                    "signal_type": "assurance_requirement",
                    "authority": "host-declared-assurance-config",
                    "priority": "structured",
                    "value": requirement_id,
                    "matched": requirement_id,
                    "reason": reason,
                }
            )
        if proof_profile and proof_profile in {str(item).strip() for item in _list_payload(protocol.get("proof_profiles"))}:
            reason = f"assurance proof profile matched {proof_profile}"
            applies_because.append(reason)
            match_signals.append(
                {
                    "signal_type": "proof_profile",
                    "authority": "host-declared-assurance-config",
                    "priority": "structured",
                    "value": proof_profile,
                    "matched": proof_profile,
                    "reason": reason,
                }
            )
        for label in sorted(required_evidence & protocol_evidence):
            reason = f"required evidence label matched {label}"
            applies_because.append(reason)
            match_signals.append(
                {
                    "signal_type": "required_evidence",
                    "authority": "host-declared-assurance-config",
                    "priority": "structured",
                    "value": label,
                    "matched": label,
                    "reason": reason,
                }
            )
    return (bool(applies_because), _dedupe(applies_because), match_signals)


def _token_matches(text: str, tokens: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [token for token in tokens if token in lowered]


def _assurance_first_signal(
    *,
    task_text: str | None,
    assurance_requirements: dict[str, Any] | None,
    protocols: list[dict[str, Any]],
) -> dict[str, Any]:
    signals: list[dict[str, Any]] = []
    if isinstance(assurance_requirements, dict) and int(assurance_requirements.get("active_count", 0) or 0) > 0:
        signals.append(
            {
                "source": "assurance_requirements",
                "authority": "host-declared-assurance-config",
                "reason": "active assurance requirements are present",
            }
        )
    task_matches = _token_matches(
        str(task_text or ""),
        ("assurance", "high assurance", "verification", "compliance", "security", "audit"),
    )
    if task_matches:
        signals.append(
            {
                "source": "task_text",
                "authority": "explicit-user-task",
                "matches": task_matches,
                "reason": "task text asks for assurance or verification-focused jumpstart",
            }
        )
    for protocol in protocols:
        text = " ".join(
            str(value or "")
            for value in (
                protocol.get("id"),
                protocol.get("title"),
                protocol.get("purpose"),
                " ".join(str(item) for item in _list_payload(protocol.get("expected_evidence"))),
                " ".join(str(item) for item in _list_payload(protocol.get("review_aids"))),
            )
        )
        matches = _token_matches(text, ("assurance", "security", "audit", "compliance", "privacy", "verification"))
        if matches:
            signals.append(
                {
                    "source": f"protocol:{protocol.get('id')}",
                    "authority": "host-declared-verification-manifest",
                    "matches": matches,
                    "reason": "configured protocol names assurance-sensitive verification concerns",
                }
            )
    return {
        "status": "present" if signals else "absent",
        "signals": signals,
        "signal_count": len(signals),
        "rule": "Assurance-first jumpstart activates only from explicit task text or host-owned assurance/verification evidence.",
    }


def _host_file_evidence_by_lane(
    *, target_root: Path, lanes: tuple[dict[str, Any], ...], per_lane_limit: int = 4, scan_limit: int = 1500
) -> dict[str, list[dict[str, Any]]]:
    evidence_by_lane: dict[str, list[dict[str, Any]]] = {str(lane["id"]): [] for lane in lanes}
    ignored_dir_names = {
        ".git",
        ".hg",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "node_modules",
        ".agentic-workspace",
    }
    stack = [target_root]
    scanned = 0
    while stack and scanned < scan_limit:
        current = stack.pop()
        try:
            children = sorted(current.iterdir(), key=lambda item: item.name)
        except OSError:
            continue
        for child in children:
            if child.is_dir():
                if child.name not in ignored_dir_names:
                    stack.append(child)
                continue
            if not child.is_file():
                continue
            scanned += 1
            relative = _repo_relative_path(child, target_root)
            for lane in lanes:
                lane_id = str(lane["id"])
                if len(evidence_by_lane[lane_id]) >= per_lane_limit:
                    continue
                matches = _token_matches(relative, tuple(str(token) for token in lane.get("tokens", ())))
                if not matches:
                    continue
                evidence_by_lane[lane_id].append(
                    {
                        "source": "host_path",
                        "path": relative,
                        "matches": matches,
                        "authority": "host-owned-file-path",
                    }
                )
    return evidence_by_lane


def _protocol_evidence_for_lane(*, protocols: list[dict[str, Any]], lane: dict[str, Any], limit: int = 4) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    tokens = tuple(str(token) for token in lane.get("tokens", ()))
    for protocol in protocols:
        fields = {
            "id": str(protocol.get("id") or ""),
            "title": str(protocol.get("title") or ""),
            "purpose": str(protocol.get("purpose") or ""),
            "applies_to_paths": " ".join(str(item) for item in _list_payload(protocol.get("applies_to_paths"))),
            "expected_evidence": " ".join(str(item) for item in _list_payload(protocol.get("expected_evidence"))),
            "steps": " ".join(str(item) for item in _list_payload(protocol.get("steps"))),
            "authority_refs": " ".join(str(item) for item in _list_payload(protocol.get("authority_refs"))),
        }
        for field, text in fields.items():
            matches = _token_matches(text, tokens)
            if not matches:
                continue
            evidence.append(
                {
                    "source": "verification_manifest",
                    "protocol_id": protocol.get("id"),
                    "field": field,
                    "matches": matches,
                    "authority": "host-declared-verification-manifest",
                }
            )
            break
        if len(evidence) >= limit:
            break
    return evidence


def _broad_protocol_gap(*, protocols: list[dict[str, Any]], candidate_lanes: list[dict[str, Any]]) -> dict[str, Any]:
    active_lane_ids = {str(lane.get("id")) for lane in candidate_lanes}
    broad_protocols: list[dict[str, Any]] = []
    for protocol in protocols:
        text = " ".join(
            [
                str(protocol.get("id") or ""),
                str(protocol.get("title") or ""),
                str(protocol.get("purpose") or ""),
                " ".join(str(item) for item in _list_payload(protocol.get("expected_evidence"))),
                " ".join(str(item) for item in _list_payload(protocol.get("steps"))),
            ]
        )
        lane_matches = [
            str(lane.get("id"))
            for lane in ASSURANCE_FIRST_LANE_CANDIDATES
            if _token_matches(text, tuple(str(token) for token in lane.get("tokens", ())))
        ]
        applies_to_paths = [str(item).strip() for item in _list_payload(protocol.get("applies_to_paths")) if str(item).strip()]
        catch_all = any(pattern in {"*", "**", "**/*"} for pattern in applies_to_paths)
        if catch_all or len(set(lane_matches) & active_lane_ids) >= 2:
            broad_protocols.append(
                {
                    "protocol_id": protocol.get("id"),
                    "reason": "catch-all path activation" if catch_all else "protocol text spans multiple candidate assurance lanes",
                    "matched_lane_ids": sorted(set(lane_matches) & active_lane_ids),
                    "applies_to_paths": applies_to_paths,
                    "status": "possible_modeling_gap",
                }
            )
    return {
        "status": "possible_gap" if broad_protocols else "not_detected",
        "protocols": broad_protocols,
        "rule": "Broad protocol coverage is advisory modeling-gap evidence, not a failing error.",
    }


def _assurance_first_jumpstart_payload(
    *,
    target_root: Path,
    task_text: str | None,
    assurance_requirements: dict[str, Any] | None,
    protocols: list[dict[str, Any]],
) -> dict[str, Any]:
    signal = _assurance_first_signal(task_text=task_text, assurance_requirements=assurance_requirements, protocols=protocols)
    if signal["status"] != "present":
        return {
            "kind": "agentic-workspace/assurance-first-jumpstart/v1",
            "status": "not_applicable",
            "assurance_signal": signal,
            "candidate_lanes": [],
            "omitted_lanes": [],
            "rule": "No assurance-first signal was detected; low-evidence repos stay on the current low-cost path.",
        }
    candidate_lanes: list[dict[str, Any]] = []
    omitted_lanes: list[dict[str, Any]] = []
    host_evidence_by_lane = _host_file_evidence_by_lane(target_root=target_root, lanes=ASSURANCE_FIRST_LANE_CANDIDATES)
    for lane in ASSURANCE_FIRST_LANE_CANDIDATES:
        evidence = [
            *_protocol_evidence_for_lane(protocols=protocols, lane=lane),
            *host_evidence_by_lane.get(str(lane["id"]), []),
        ]
        if evidence:
            candidate_lanes.append(
                {
                    "id": lane["id"],
                    "title": lane["title"],
                    "status": "candidate",
                    "evidence": evidence,
                    "suggested_assurance_requirement": lane["suggested_requirement"],
                    "suggested_verification_protocol": lane["suggested_protocol"],
                    "claim_boundary": "Advisory jumpstart suggestion only; seed durable routes only after agent/human review.",
                }
            )
        else:
            omitted_lanes.append(
                {
                    "id": lane["id"],
                    "title": lane["title"],
                    "reason": "no host-owned evidence found for this lane",
                }
            )
    broad_gap = _broad_protocol_gap(protocols=protocols, candidate_lanes=candidate_lanes)
    return {
        "kind": "agentic-workspace/assurance-first-jumpstart/v1",
        "status": "candidate_lanes_present" if candidate_lanes else "assurance_signal_without_lane_evidence",
        "assurance_signal": signal,
        "candidate_lanes": candidate_lanes,
        "candidate_lane_count": len(candidate_lanes),
        "omitted_lanes": omitted_lanes,
        "broad_protocol_gap": broad_gap,
        "rule": (
            "Suggest narrower assurance lanes only when an assurance-first signal and host-owned lane evidence are both present. "
            "Suggestions are advisory and must cite host evidence."
        ),
    }


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
    evidence_concepts = manifest["evidence_concepts"]
    evidence_by_protocol: dict[str, list[dict[str, Any]]] = {}
    for bundle in evidence_bundles:
        evidence_by_protocol.setdefault(str(bundle.get("protocol_id", "")), []).append(bundle)

    active_protocols: list[dict[str, Any]] = []
    match_records: list[dict[str, Any]] = []
    evidence_status: list[dict[str, Any]] = []
    normalized_paths = _normalize_changed_paths(changed_paths)
    for protocol in configured_protocols:
        matched, applies_because, match_signals = _match_protocol(
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
                "match_signals": match_signals,
                "structured_signal_count": sum(1 for item in match_signals if item.get("priority") == "structured"),
                "advisory_marker_count": sum(1 for item in match_signals if item.get("signal_type") == "task_marker"),
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
        expected_evidence_concepts = _evidence_concept_usage(labels=expected_evidence, concepts=evidence_concepts)
        missing_evidence = [item for item in expected_evidence if item not in evidence_present]
        stale_expected_evidence = [item for item in missing_evidence if item in stale_evidence]
        if matched:
            active_protocols.append(
                {
                    **protocol,
                    "applies_because": applies_because,
                    "match_signals": match_signals,
                    "evidence_bundle_ids": [b["id"] for b in bundles],
                    "expected_evidence_concepts": expected_evidence_concepts,
                    "authority_boundary": {
                        "kind": "agentic-workspace/authority-boundary/v1",
                        "surface": "verification.protocol",
                        "authority_class": "advisory-support",
                        "observed_by_aw": [
                            f"configured verification protocol {protocol['id']}",
                            *applies_because,
                        ],
                        "match_authority": {
                            "structured_signal_count": sum(1 for item in match_signals if item.get("priority") == "structured"),
                            "advisory_marker_count": sum(1 for item in match_signals if item.get("signal_type") == "task_marker"),
                            "rule": (
                                "Path, planning, proof-profile, requirement, and evidence-label signals are structured evidence. "
                                "Task markers are host-declared manifest hints and remain advisory."
                            ),
                        },
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
                    "expected_evidence_concepts": expected_evidence_concepts,
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
    assurance_first_jumpstart = _assurance_first_jumpstart_payload(
        target_root=target_root,
        task_text=task_text,
        assurance_requirements=assurance_requirements,
        protocols=configured_protocols,
    )
    degraded_concepts = [
        item
        for status in evidence_status
        if isinstance(status, dict)
        for item in _list_payload(
            status.get("expected_evidence_concepts", {}).get("degraded")
            if isinstance(status.get("expected_evidence_concepts"), dict)
            else []
        )
    ]
    concept_attention = any(item.get("state") == "undeclared-host-concept" for item in degraded_concepts) or bool(
        _list_payload(evidence_concepts.get("invalid_declarations"))
    )
    return {
        "kind": "agentic-workspace/verification/v1",
        "status": "attention"
        if any(item.get("state") in {"missing-evidence", "stale-evidence"} for item in evidence_status) or concept_attention
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
        "evidence_concepts": {
            **evidence_concepts,
            "used_degraded": degraded_concepts,
            "status": "attention"
            if concept_attention
            else "declared"
            if _list_payload(evidence_concepts.get("declared_host"))
            else "core-only",
            "rule": (
                "Core concepts are AW vocabulary; host concepts must be declared as host:<term>. "
                "Undeclared host concepts degrade proof guidance instead of weakening structured schemas."
            ),
        },
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
        "assurance_first_jumpstart": assurance_first_jumpstart,
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
