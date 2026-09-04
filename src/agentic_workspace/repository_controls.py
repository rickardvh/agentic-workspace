from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .durability import atomic_write_json
from .generated_semantics import operation_contract, semantic_digest
from .modules import Module
from .operations import Operation

RULE_PATTERN = re.compile(r"<!--\s*agentic-workspace:rule\s*(\{.*?\})\s*-->", re.DOTALL)
SHARED_ANSWERS = ".agentic-workspace/config.answers.json"
LOCAL_ANSWERS = ".agentic-workspace/local/configuration.json"


def _rules(root: Path) -> list[dict[str, Any]]:
    path = root / "AGENTS.md"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    rules: list[dict[str, Any]] = []
    for match in RULE_PATTERN.finditer(text):
        value = json.loads(match.group(1))
        if not isinstance(value, dict) or not value.get("id"):
            raise ValueError("each scoped AGENTS.md rule requires an id")
        rule = dict(value)
        rule["revision"] = semantic_digest({"source": "AGENTS.md", "rule": value})
        rules.append(rule)
    return rules


def repository_rule_revision(root: Path, rule_id: str) -> str | None:
    """Return the current exact revision of one repository-owned rule."""

    rule = next((item for item in _rules(root.resolve()) if item["id"] == rule_id), None)
    return str(rule["revision"]) if rule is not None else None


def _json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def _applicable(rule: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    applies = rule.get("applies", {})
    if not isinstance(applies, Mapping):
        raise ValueError(f"rule {rule.get('id')} applies must be an object")
    terms = applies.get("task_terms", [])
    patterns = applies.get("paths", [])
    task = str(context.get("task") or "").lower()
    changed = [str(path) for path in context.get("changed_paths", [])]
    return (
        (not terms and not patterns)
        or any(str(term).lower() in task for term in terms)
        or any(Path(path).match(str(pattern)) for path in changed for pattern in patterns)
    )


def _answers(root: Path) -> dict[str, Any]:
    return {**_json(root / SHARED_ANSWERS), **_json(root / LOCAL_ANSWERS)}


def _path_exists(root: Path, relative: str) -> bool:
    candidate = Path(relative)
    if candidate.is_absolute() or not candidate.parts or any(part in {"", ".", ".."} for part in candidate.parts):
        raise ValueError(f"configuration inference path must be canonical and relative: {relative}")
    path = root.joinpath(*candidate.parts)
    return path.is_file() or path.is_dir()


def _inferred_answer(root: Path, rule_id: str, decision: Mapping[str, Any], facts: Mapping[str, Any]) -> str | None:
    candidates = decision.get("infer", [])
    if not isinstance(candidates, list) or any(not isinstance(item, Mapping) for item in candidates):
        raise ValueError(f"rule {rule_id} decision.infer must be a list of objects")
    choice_ids = {
        str(choice.get("id"))
        for choice in decision.get("choices", [])
        if isinstance(choice, Mapping) and choice.get("id")
    }
    matched: list[str] = []
    for candidate in candidates:
        answer = str(candidate.get("answer") or "")
        condition = candidate.get("when", {})
        if not answer or answer not in choice_ids or not isinstance(condition, Mapping):
            raise ValueError(f"rule {rule_id} has an invalid inferred answer")
        matches = False
        if set(condition) == {"path_exists"}:
            matches = _path_exists(root, str(condition["path_exists"]))
        elif set(condition) == {"fact_equals"} and isinstance(condition.get("fact_equals"), Mapping):
            comparison = condition["fact_equals"]
            matches = facts.get(comparison.get("key")) == comparison.get("value")
        else:
            raise ValueError(f"rule {rule_id} inference requires one strong path_exists or fact_equals condition")
        if matches:
            matched.append(answer)
    unique = sorted(set(matched))
    if len(unique) > 1:
        raise ValueError(f"rule {rule_id} has conflicting current configuration inferences")
    return unique[0] if unique else None


def _contribute(context: Mapping[str, Any]) -> dict[str, Any] | None:
    root = Path(str(context["target"])).resolve()
    applicable = sorted((rule for rule in _rules(root) if _applicable(rule, context)), key=lambda item: str(item["id"]))
    if not applicable:
        return None
    answers = _answers(root)
    facts: dict[str, Any] = {}
    resources: list[dict[str, Any]] = []
    procedures: list[dict[str, Any]] = []
    pending_decisions: list[dict[str, Any]] = []
    inferred_actions: list[dict[str, Any]] = []
    blocked_claims: list[str] = []
    conflicts: list[str] = []
    # Admission is deliberately two-phase: every inference sees the complete
    # current fact set, independent of rule identifiers or file order.
    for rule in applicable:
        rule_id = str(rule["id"])
        for key, value in dict(rule.get("facts", {})).items():
            if key in facts and facts[key] != value:
                conflicts.append(key)
            facts[key] = value
        for field, destination in (("resources", resources), ("procedures", procedures)):
            for raw in rule.get(field, []):
                item = dict(raw)
                item.setdefault("revision", rule["revision"])
                item.setdefault("locator", f"AGENTS.md#{rule_id}")
                destination.append(item)
        claims = rule.get("claims", {})
        if isinstance(claims, Mapping):
            blocked_claims.extend(str(claim) for claim in claims.get("blocked", []))

    for rule in applicable:
        rule_id = str(rule["id"])
        decision = rule.get("decision")
        answer = answers.get(rule_id)
        if isinstance(decision, Mapping) and (
            not isinstance(answer, Mapping) or answer.get("rule_revision") != rule["revision"]
        ):
            inferred = _inferred_answer(root, rule_id, decision, facts)
            scope = str(decision.get("scope") or "shared")
            if inferred:
                inferred_actions.append(
                    {
                        "operation_id": "repository.answer",
                        "arguments": {
                            "target": str(root),
                            "rule_id": rule_id,
                            "rule_revision": rule["revision"],
                            "answer": inferred,
                            "scope": scope,
                        },
                        "effects": ["repository-configuration"],
                        "authority": "repository-inference",
                        "priority": 1000 - len(inferred_actions),
                    }
                )
                continue
            choices = list(decision.get("choices", []))
            if decision.get("required", True) is False:
                choices = [*choices, {"id": "defer", "label": "Defer for now"}]
            pending_decisions.append(
                {
                    "id": rule_id,
                    "detail_revision": rule["revision"],
                    "question": str(decision.get("question") or ""),
                    "authority": str(decision.get("authority") or "maintainer"),
                    "response_operation_id": "repository.answer",
                    "effects": ["repository-configuration"],
                    "choices": choices,
                    "allow_open": decision.get("allow_open") is True,
                }
            )
        elif isinstance(answer, Mapping):
            if answer.get("disposition") == "deferred":
                resume = context.get("configuration")
                if (
                    isinstance(decision, Mapping)
                    and isinstance(resume, Mapping)
                    and resume.get("resume") in {True, rule_id}
                ):
                    choices = list(decision.get("choices", []))
                    choices.append({"id": "defer", "label": "Defer for now"})
                    pending_decisions.append(
                        {
                            "id": rule_id,
                            "detail_revision": rule["revision"],
                            "question": str(decision.get("question") or ""),
                            "authority": str(decision.get("authority") or "maintainer"),
                            "response_operation_id": "repository.answer",
                            "effects": ["repository-configuration"],
                            "choices": choices,
                            "allow_open": decision.get("allow_open") is True,
                        }
                    )
                else:
                    facts[f"configuration:{rule_id}"] = {
                        "status": "deferred",
                        "decision_revision": rule["revision"],
                    }
            else:
                facts[f"configuration:{rule_id}"] = answer.get("answer")
    blockers = []
    if conflicts:
        blockers.append(
            {
                "code": "repository-control-conflict",
                "message": "applicable repository controls disagree on hard facts",
                "owner": "repository",
                "recovery": "AGENTS.md keys: " + ", ".join(sorted(set(conflicts))),
            }
        )
    decisions = [] if inferred_actions else pending_decisions[:1]
    actions = inferred_actions[:1]
    return {
        "revision": semantic_digest(
            {"rules": [(rule["id"], rule["revision"]) for rule in applicable], "answers": answers}
        ),
        "facts": facts,
        "resources": resources,
        "procedures": procedures,
        "decisions": decisions,
        "actions": actions,
        "blockers": blockers,
        "claims": {"blocked": sorted(set(blocked_claims))},
        "terminal": not decisions and not actions and not blockers,
    }


def _answer(arguments: dict[str, Any]) -> dict[str, Any]:
    root = Path(arguments["target"]).resolve()
    current = next((rule for rule in _rules(root) if rule["id"] == arguments["rule_id"]), None)
    if current is None or current["revision"] != arguments["rule_revision"]:
        return {"status": "rejected", "effects": [], "value": {"reason": "stale-repository-rule"}}
    decision = current.get("decision", {})
    expected_scope = decision.get("scope", "shared") if isinstance(decision, Mapping) else "shared"
    if arguments["scope"] != expected_scope:
        return {"status": "rejected", "effects": [], "value": {"reason": "configuration-scope-mismatch"}}
    if arguments["answer"] == "defer" and (
        not isinstance(decision, Mapping) or decision.get("required", True) is not False
    ):
        return {"status": "rejected", "effects": [], "value": {"reason": "required-configuration-cannot-defer"}}
    relative = LOCAL_ANSWERS if arguments["scope"] == "local" else SHARED_ANSWERS
    path = root / relative
    answers = _json(path)
    answers[arguments["rule_id"]] = {
        "rule_revision": arguments["rule_revision"],
        "answer": arguments["answer"],
        "scope": arguments["scope"],
        "disposition": "deferred" if arguments["answer"] == "defer" else "configured",
    }
    atomic_write_json(path, answers)
    return {
        "status": "applied",
        "effects": ["repository-configuration"],
        "value": answers[arguments["rule_id"]],
    }


def _recover_answer(arguments: dict[str, Any]) -> dict[str, Any] | None:
    root = Path(arguments["target"]).resolve()
    answer = _answers(root).get(arguments["rule_id"])
    if isinstance(answer, Mapping) and answer.get("rule_revision") == arguments["rule_revision"]:
        return {"status": "applied", "effects": ["repository-configuration"], "value": dict(answer)}
    return None


def _correction_revision(correction: Mapping[str, Any]) -> str:
    return semantic_digest(
        {
            "correction_id": correction.get("correction_id"),
            "statement": correction.get("statement"),
            "subject": dict(correction.get("subject", {})),
            "applicability": dict(correction.get("applicability", {})),
            "provenance": dict(correction.get("provenance", {})),
            "future_usefulness": correction.get("future_usefulness"),
            "existing_owner": dict(correction.get("existing_owner", {})),
            "deterministic_owner_failure": dict(correction.get("deterministic_owner_failure", {})),
        }
    )


def _accept_correction(arguments: dict[str, Any]) -> dict[str, Any]:
    root = Path(arguments["target"]).resolve()
    correction = arguments["correction"]
    evidence = correction.get("existing_owner", {}) if isinstance(correction, Mapping) else {}
    subject = correction.get("subject", {}) if isinstance(correction, Mapping) else {}
    current = repository_rule_revision(root, arguments["owner_ref"])
    valid = (
        isinstance(evidence, Mapping)
        and isinstance(subject, Mapping)
        and _correction_revision(correction) == arguments["correction_revision"]
        and correction.get("provenance", {}).get("authority") == "human"
        and evidence.get("owner") == "repository"
        and evidence.get("ref") == arguments["owner_ref"]
        and evidence.get("revision") == arguments["owner_revision"]
        and current == arguments["owner_revision"]
        and subject.get("kind") == "repository-rule"
        and subject.get("id") == arguments["owner_ref"]
    )
    if not valid:
        return {"status": "rejected", "effects": [], "value": {"reason": "correction-not-enforced-by-owner"}}
    return {
        "status": "unchanged",
        "effects": [],
        "value": {
            "correction_revision": arguments["correction_revision"],
            "owner": "repository",
            "owner_ref": arguments["owner_ref"],
            "owner_revision": current,
            "disposition": "already-owned",
            "justification": "the exact repository rule already enforces this correction",
        },
    }


def repository_module() -> Module:
    contract = operation_contract("repository.answer")
    correction_contract = operation_contract("repository.accept-correction")
    return Module(
        name="repository",
        owns=("repository-configuration",),
        required_capabilities=("contribution/procedures", "contribution/decisions", "operation/durable-commit"),
        contribute=_contribute,
        operations=(
            Operation(
                "repository.answer",
                contract["input"],
                tuple(contract["effects"]),
                _answer,
                _recover_answer,
            ),
            Operation(
                "repository.accept-correction",
                correction_contract["input"],
                tuple(correction_contract["effects"]),
                _accept_correction,
                _accept_correction,
                accepted_handoffs=("correction",),
            ),
        ),
        currentness=lambda context: (
            semantic_digest(
                {
                    "instructions": "sha256:"
                    + hashlib.sha256((Path(str(context["target"])) / "AGENTS.md").read_bytes()).hexdigest(),
                    "shared_answers": _json(Path(str(context["target"])) / SHARED_ANSWERS),
                    "local_answers": _json(Path(str(context["target"])) / LOCAL_ANSWERS),
                    "task": context.get("task"),
                    "changed_paths": context.get("changed_paths", []),
                    "configuration": context.get("configuration"),
                }
            )
            if (Path(str(context["target"])) / "AGENTS.md").is_file()
            else None
        ),
    )
