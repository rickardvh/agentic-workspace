"""Compile source-owned instruction clauses into bounded operating effects."""

from __future__ import annotations

import fnmatch
import hashlib
import json
from typing import Any

EFFECT_KINDS = {"surface", "prefer", "require", "restrict"}
PREDICATE_OPERATORS = {"present", "is", "one_of", "intersects", "matches", "current"}
ENFORCING_EFFECTS = {"require", "restrict"}
REPO_REQUIREMENT_CLASSES = {"invariant", "current-evidence", "guideline"}
TARGET_PREFIXES = {"surface", "skill", "operation", "evidence", "human", "action", "effect", "claim"}
EFFECT_TARGET_CLASSES = {
    "surface": {"surface"},
    "prefer": {"surface", "skill", "operation"},
    "require": {"action", "effect", "operation", "claim"},
    "restrict": {"action", "effect", "operation", "claim"},
}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _target_class(target: str) -> str:
    return target.partition(":")[0]


def _source_current(source: dict[str, Any]) -> bool:
    return bool(source.get("owner") and source.get("revision") and source.get("current") is True)


def _source_valid(source: dict[str, Any]) -> bool:
    return bool(source.get("owner") and source.get("revision") and isinstance(source.get("current"), bool))


def _fact_index(facts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(fact.get("id")): fact for fact in facts if str(fact.get("id") or "")}


def _predicate_leaf(predicate: dict[str, Any], facts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    operator = str(predicate.get("operator") or "")
    fact_ref = str(predicate.get("fact") or "")
    fact = facts.get(fact_ref)
    if operator not in PREDICATE_OPERATORS:
        return {"result": "unknown", "reason": "unknown-operator", "fact": fact_ref, "operator": operator}
    if fact is None:
        return {"result": "unknown", "reason": "missing-fact", "fact": fact_ref, "operator": operator}
    source = _as_dict(fact.get("source"))
    if operator == "present":
        result = "true"
    elif operator == "current":
        result = "true" if _source_current(source) else "false"
    elif not _source_current(source):
        return {"result": "unknown", "reason": "stale-fact", "fact": fact_ref, "operator": operator}
    else:
        value = fact.get("value")
        expected = predicate.get("value")
        if operator == "is":
            matched = value == expected
        elif operator == "one_of":
            matched = value in _as_list(predicate.get("values"))
        elif operator == "intersects":
            matched = bool(set(_as_list(value)) & set(_as_list(predicate.get("values"))))
        else:
            matched = isinstance(value, str) and isinstance(expected, str) and fnmatch.fnmatch(value, expected)
        result = "true" if matched else "false"
    return {"result": result, "reason": "evaluated", "fact": fact_ref, "operator": operator}


def evaluate_predicate(predicate: dict[str, Any], facts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Evaluate a bounded predicate with explicit true/false/unknown semantics."""

    compound = [key for key in ("all", "any", "none") if key in predicate]
    if not compound:
        return _predicate_leaf(predicate, facts)
    if len(compound) != 1:
        return {"result": "unknown", "reason": "ambiguous-composition", "children": []}
    mode = compound[0]
    children = [evaluate_predicate(_as_dict(item), facts) for item in _as_list(predicate.get(mode))]
    results = [str(child.get("result") or "unknown") for child in children]
    if not children:
        result = "true" if mode in {"all", "none"} else "false"
    elif mode == "all":
        result = "false" if "false" in results else "unknown" if "unknown" in results else "true"
    elif mode == "any":
        result = "true" if "true" in results else "unknown" if "unknown" in results else "false"
    else:
        result = "false" if "true" in results else "unknown" if "unknown" in results else "true"
    return {"result": result, "reason": f"{mode}-composition", "children": children}


def validate_instruction_program(program: dict[str, Any]) -> list[dict[str, str]]:
    """Return deterministic conformance diagnostics without executing clauses."""

    facts = [_as_dict(item) for item in _as_list(program.get("facts"))]
    clauses = [_as_dict(item) for item in _as_list(program.get("clauses"))]
    capabilities = [_as_dict(item) for item in _as_list(program.get("capabilities"))]
    fact_ids = {str(item.get("id") or "") for item in facts}
    fact_types = {str(item.get("id") or ""): str(item.get("type") or "") for item in facts}
    capability_ids = {str(item.get("id") or "") for item in capabilities}
    diagnostics: list[dict[str, str]] = [
        {str(key): str(value) for key, value in _as_dict(item).items() if str(key)}
        for item in _as_list(program.get("source_diagnostics"))
        if isinstance(item, dict) and str(item.get("code") or "")
    ]
    for fact in facts:
        if not str(fact.get("id") or "") or not _source_valid(_as_dict(fact.get("source"))):
            diagnostics.append({"code": "invalid-fact-identity", "ref": str(fact.get("id") or "")})
    for capability in capabilities:
        if not str(capability.get("id") or "") or not _source_valid(_as_dict(capability.get("source"))):
            diagnostics.append({"code": "invalid-capability-identity", "ref": str(capability.get("id") or "")})
    for clause in clauses:
        clause_id = str(clause.get("id") or "")
        source = _as_dict(clause.get("source"))
        authority = _as_dict(clause.get("authority"))
        allowed_effects = {str(item) for item in _as_list(authority.get("effects"))}
        allowed_targets = [str(item) for item in _as_list(authority.get("target_patterns"))]
        if not clause_id or not _source_current(source):
            diagnostics.append({"code": "invalid-clause-source", "ref": clause_id})

        def inspect_predicate(predicate: dict[str, Any]) -> None:
            for mode in ("all", "any", "none"):
                if mode in predicate:
                    for child in _as_list(predicate.get(mode)):
                        inspect_predicate(_as_dict(child))
                    return
            operator = str(predicate.get("operator") or "")
            fact_ref = str(predicate.get("fact") or "")
            if operator not in PREDICATE_OPERATORS:
                diagnostics.append({"code": "unknown-predicate-operator", "ref": f"{clause_id}:{operator}"})
            if fact_ref not in fact_ids:
                diagnostics.append({"code": "unknown-fact-reference", "ref": f"{clause_id}:{fact_ref}"})
            fact_type = fact_types.get(fact_ref, "")
            allowed_types = {
                "present": {"boolean", "string", "string-set", "identity"},
                "current": {"boolean", "string", "string-set", "identity"},
                "is": {"boolean", "string", "identity"},
                "one_of": {"string", "identity"},
                "intersects": {"string-set"},
                "matches": {"string", "identity"},
            }.get(operator, set())
            if fact_type and fact_type not in allowed_types:
                diagnostics.append({"code": "invalid-predicate-type", "ref": f"{clause_id}:{operator}:{fact_type}"})

        inspect_predicate(_as_dict(clause.get("when")))
        for effect in [_as_dict(item) for item in _as_list(clause.get("effects"))]:
            kind = str(effect.get("kind") or "")
            target = str(effect.get("target") or "")
            if kind not in EFFECT_KINDS:
                diagnostics.append({"code": "unknown-effect", "ref": f"{clause_id}:{kind}"})
                continue
            if _target_class(target) not in TARGET_PREFIXES:
                diagnostics.append({"code": "invalid-target-class", "ref": f"{clause_id}:{target}"})
            elif kind in EFFECT_TARGET_CLASSES and _target_class(target) not in EFFECT_TARGET_CLASSES[kind]:
                diagnostics.append({"code": "incompatible-effect-target", "ref": f"{clause_id}:{kind}:{target}"})
            if kind not in allowed_effects or not any(fnmatch.fnmatch(target, pattern) for pattern in allowed_targets):
                diagnostics.append({"code": "unauthorized-effect", "ref": f"{clause_id}:{kind}:{target}"})
            satisfier = str(effect.get("satisfier") or "")
            if kind == "require" and not satisfier:
                diagnostics.append({"code": "missing-satisfier", "ref": f"{clause_id}:{target}"})
            if kind == "require" and satisfier and satisfier not in capability_ids and satisfier not in fact_ids:
                diagnostics.append({"code": "unknown-satisfier", "ref": f"{clause_id}:{satisfier}"})
    required_targets = {
        str(effect.get("target") or "")
        for clause in clauses
        for effect in [_as_dict(item) for item in _as_list(clause.get("effects"))]
        if effect.get("kind") == "require"
    }
    restricted_targets = {
        str(effect.get("target") or "")
        for clause in clauses
        for effect in [_as_dict(item) for item in _as_list(clause.get("effects"))]
        if effect.get("kind") == "restrict"
    }
    for target in sorted(required_targets & restricted_targets):
        diagnostics.append({"code": "requirement-restriction-conflict", "ref": target})
    return sorted(diagnostics, key=lambda item: (item["code"], item["ref"]))


def _target_relevant(target: str, current_targets: set[str]) -> bool:
    return any(fnmatch.fnmatch(current, target) or fnmatch.fnmatch(target, current) for current in current_targets)


def compile_instruction_program(program: dict[str, Any], *, current_targets: list[str] | None = None) -> dict[str, Any]:
    """Compile clauses into explanation-first effects; never execute or widen authority."""

    facts = [_as_dict(item) for item in _as_list(program.get("facts"))]
    clauses = [_as_dict(item) for item in _as_list(program.get("clauses"))]
    capabilities = [_as_dict(item) for item in _as_list(program.get("capabilities"))]
    source_diagnostics = [_as_dict(item) for item in _as_list(program.get("source_diagnostics"))]
    if not facts and not clauses and not capabilities and not source_diagnostics:
        return {
            "kind": "agentic-workspace/instruction-clause-projection/v1",
            "status": "not-requested",
            "snapshot_revision": "",
            "effects": {"surface": [], "prefer": [], "require": [], "restrict": []},
            "blockers": [],
            "diagnostics": [],
            "evaluations": [],
        }
    diagnostics = validate_instruction_program(program)
    facts_by_id = _fact_index(facts)
    capabilities_by_id = {str(item.get("id")): item for item in capabilities if str(item.get("id") or "")}
    relevant_targets = {str(item) for item in (current_targets or []) if str(item)}
    composed: dict[str, dict[str, dict[str, Any]]] = {kind: {} for kind in EFFECT_KINDS}
    evaluations: list[dict[str, Any]] = []
    blockers: list[dict[str, str]] = []
    fatal_codes = {
        "invalid-fact-identity",
        "invalid-capability-identity",
        "invalid-clause-source",
        "unknown-predicate-operator",
        "unknown-effect",
        "invalid-target-class",
        "invalid-predicate-type",
        "incompatible-effect-target",
        "unauthorized-effect",
        "missing-effect-target",
        "missing-satisfier",
        "invalid-bounded-control",
        "invalid-repo-requirement",
    }
    for diagnostic in source_diagnostics:
        if diagnostic.get("code") in {"missing-effect-target", "invalid-bounded-control", "invalid-repo-requirement"}:
            blockers.append(
                {
                    "reason_code": "missing-authority",
                    "owner": str(diagnostic.get("owner") or "instruction-source"),
                    "repair": str(diagnostic.get("repair") or "resolve the affected instruction target through its source owner"),
                    "clause_id": str(diagnostic.get("ref") or "source-adapter"),
                    "target": "unknown",
                }
            )
    for clause in clauses:
        clause_id = str(clause.get("id") or "")
        for diagnostic in diagnostics:
            if diagnostic.get("code") != "missing-satisfier" or not str(diagnostic.get("ref") or "").startswith(f"{clause_id}:"):
                continue
            target = str(diagnostic.get("ref") or "").removeprefix(f"{clause_id}:")
            if _target_relevant(target, relevant_targets):
                blockers.append(
                    {
                        "reason_code": "missing-capability",
                        "owner": str(_as_dict(clause.get("source")).get("owner") or "instruction-source"),
                        "repair": f"name the source-owned satisfier required before {target}",
                        "clause_id": clause_id,
                        "target": target,
                    }
                )
        clause_invalid = any(
            item["code"] in fatal_codes and (item["ref"] == clause_id or item["ref"].startswith(f"{clause_id}:")) for item in diagnostics
        )
        evaluation = evaluate_predicate(_as_dict(clause.get("when")), facts_by_id)
        result = str(evaluation.get("result") or "unknown")
        emitted: list[dict[str, Any]] = []
        for effect in [_as_dict(item) for item in _as_list(clause.get("effects"))]:
            kind = str(effect.get("kind") or "")
            target = str(effect.get("target") or "")
            if clause_invalid or kind not in EFFECT_KINDS:
                continue
            if result == "unknown" and kind in ENFORCING_EFFECTS and _target_relevant(target, relevant_targets):
                blockers.append(
                    {
                        "reason_code": "stale-revision",
                        "owner": str(_as_dict(clause.get("source")).get("owner") or "instruction-source"),
                        "repair": f"resolve clause applicability for {clause_id} before {target}",
                        "clause_id": clause_id,
                        "target": target,
                    }
                )
            if result != "true":
                continue
            identity = target
            if kind == "require":
                satisfier = str(effect.get("satisfier") or "")
                identity = f"{target}|{satisfier}"
                capability = capabilities_by_id.get(satisfier)
                fact = facts_by_id.get(satisfier)
                satisfied = bool(capability and capability.get("current") is True) or bool(
                    fact and _source_current(_as_dict(fact.get("source"))) and fact.get("value") is True
                )
                effect = {**effect, "satisfied": satisfied}
                if not satisfied and _target_relevant(target, relevant_targets):
                    requirement = _as_dict(effect.get("requirement"))
                    evidence_state = str(_as_dict(capability).get("evidence_state") or requirement.get("evidence_state") or "missing")
                    reason_code = {
                        "failed": "failed-evidence",
                        "stale": "stale-revision",
                        "stale-intent": "stale-revision",
                        "unknown": "unresolved-evidence",
                        "unavailable": "unavailable-evidence",
                        "invalid": "invalid-evidence",
                    }.get(evidence_state, "missing-capability")
                    detail_route = str(_as_dict(capability).get("detail_route") or requirement.get("detail_route") or "")
                    blockers.append(
                        {
                            "reason_code": reason_code,
                            "owner": str(_as_dict(clause.get("source")).get("owner") or "instruction-source"),
                            "repair": detail_route or f"satisfy {satisfier or target} through its source owner",
                            "clause_id": clause_id,
                            "target": target,
                        }
                    )
            elif kind == "restrict" and _target_relevant(target, relevant_targets):
                blockers.append(
                    {
                        "reason_code": "denied-effect",
                        "owner": str(_as_dict(clause.get("source")).get("owner") or "instruction-source"),
                        "repair": f"remove the restricted target or reconcile {clause_id}",
                        "clause_id": clause_id,
                        "target": target,
                    }
                )
            projected = {**effect, "clause_id": clause_id, "source": _as_dict(clause.get("source"))}
            composed[kind].setdefault(identity, projected)
            emitted.append(projected)
        evaluations.append({"clause_id": clause_id, "condition": evaluation, "emitted_effects": emitted})
    for requirement in composed["require"].values():
        target = str(requirement.get("target") or "")
        if target in composed["restrict"]:
            blockers.append(
                {
                    "reason_code": "conflicting-input",
                    "owner": "instruction-source-owners",
                    "repair": f"resolve requirement/restriction conflict for {target}",
                    "clause_id": str(requirement.get("clause_id") or ""),
                    "target": target,
                }
            )
    snapshot = {
        "facts": [{"id": item.get("id"), "source": item.get("source")} for item in facts],
        "clauses": [{"id": item.get("id"), "source": item.get("source")} for item in clauses],
        "capabilities": [
            {
                "id": item.get("id"),
                "current": item.get("current"),
                "evidence_state": item.get("evidence_state"),
                "measurement": item.get("measurement"),
                "source": item.get("source"),
            }
            for item in capabilities
        ],
        "source_diagnostics": source_diagnostics,
    }
    return {
        "kind": "agentic-workspace/instruction-clause-projection/v1",
        "status": "invalid" if any(item["code"] in fatal_codes for item in diagnostics) else "blocked" if blockers else "compiled",
        "snapshot_revision": _digest(snapshot),
        "effects": {kind: list(composed[kind].values()) for kind in sorted(EFFECT_KINDS)},
        "blockers": sorted(blockers, key=lambda item: (item["reason_code"], item["target"], item["clause_id"])),
        "diagnostics": diagnostics,
        "evaluations": evaluations,
        "composition": {
            "surface": "set-union by target",
            "prefer": "advisory first occurrence by target",
            "require": "accumulate and deduplicate by target+satisfier",
            "restrict": "conservative set-union by target",
        },
        "authority_rule": "Clauses may surface, prefer, require, or restrict only declared targets; they never grant permission or execute effects.",
    }


def instruction_program_from_existing_mechanisms(inputs: dict[str, Any]) -> dict[str, Any]:
    """Compile representative existing owner formats into the shared IR."""

    mechanisms = _as_dict(inputs.get("instruction_mechanisms"))
    if not mechanisms:
        return _as_dict(inputs.get("instruction_program"))
    source_program = _as_dict(inputs.get("instruction_program"))
    facts = [
        *[_as_dict(item) for item in _as_list(source_program.get("facts"))],
        *[_as_dict(item) for item in _as_list(mechanisms.get("source_facts"))],
    ]
    clauses = [_as_dict(item) for item in _as_list(source_program.get("clauses"))]
    source_diagnostics = [
        {str(key): str(value) for key, value in _as_dict(item).items()} for item in _as_list(source_program.get("source_diagnostics"))
    ]
    capabilities = [
        *[_as_dict(item) for item in _as_list(source_program.get("capabilities"))],
        *[_as_dict(item) for item in _as_list(inputs.get("instruction_capabilities"))],
    ]
    adapters = [
        ("scoped_instructions", "surface", "surface"),
        ("skill_routing", "prefer", "skill"),
        ("assurance_requirements", "require", ""),
        ("claim_restrictions", "restrict", "claim"),
    ]
    for mechanism, effect_kind, default_target_class in adapters:
        for index, item in enumerate([_as_dict(value) for value in _as_list(mechanisms.get(mechanism))]):
            item_id = str(item.get("id") or f"{mechanism}-{index + 1}")
            owner = str(item.get("owner") or mechanism)
            revision = str(item.get("revision") or "")
            fact_id = f"mechanism:{item_id}:applicable"
            target = str(item.get("target") or (f"{default_target_class}:{item_id}" if default_target_class else ""))
            if effect_kind == "require" and not target:
                source_diagnostics.append(
                    {
                        "code": "missing-effect-target",
                        "ref": f"adapter:{mechanism}:{item_id}",
                        "owner": owner,
                        "repair": f"derive the affected action, effect, operation, or claim target from {owner}",
                    }
                )
                continue
            effect: dict[str, Any] = {"kind": effect_kind, "target": target}
            if effect_kind == "require":
                effect["satisfier"] = str(item.get("satisfier") or "")
            source = {"owner": owner, "revision": revision, "current": bool(revision)}
            facts.append({"id": fact_id, "type": "boolean", "value": item.get("applicable", True), "source": source})
            clauses.append(
                {
                    "id": f"adapter:{mechanism}:{item_id}",
                    "source": source,
                    "when": {"fact": fact_id, "operator": "is", "value": True},
                    "effects": [effect],
                    "authority": {"effects": [effect_kind], "target_patterns": [target]},
                }
            )
    for index, item in enumerate([_as_dict(value) for value in _as_list(mechanisms.get("repo_requirements"))]):
        item_id = str(item.get("id") or f"repo-requirement-{index + 1}")
        owner = str(item.get("owner") or "repo-requirements")
        revision = str(item.get("revision") or "")
        requirement_class = str(item.get("requirement_class") or "")
        effect_kind = "prefer" if requirement_class == "guideline" else "require"
        target = str(item.get("target") or "")
        satisfier = str(item.get("satisfier") or "")
        source_intent_ref = str(item.get("source_intent_ref") or "")
        source_intent_revision = str(item.get("source_intent_revision") or "")
        source_intent_current = item.get("source_intent_current")
        if (
            requirement_class not in REPO_REQUIREMENT_CLASSES
            or not source_intent_ref
            or not source_intent_revision
            or not isinstance(source_intent_current, bool)
        ):
            source_diagnostics.append(
                {
                    "code": "invalid-repo-requirement",
                    "ref": f"adapter:repo_requirements:{item_id}",
                    "owner": owner,
                    "repair": "use a supported class and bind the strongest current source intent ref, revision, and currentness",
                }
            )
            continue
        if not target or (effect_kind == "require" and not satisfier):
            source_diagnostics.append(
                {
                    "code": "invalid-repo-requirement",
                    "ref": f"adapter:repo_requirements:{item_id}",
                    "owner": owner,
                    "repair": "provide one existing bounded target and a source-owned satisfier for hard requirements",
                }
            )
            continue
        fact_id = f"repo-requirement:{item_id}:applicable"
        source = {"owner": owner, "revision": revision, "current": bool(revision)}
        facts.append({"id": fact_id, "type": "boolean", "value": item.get("applicable", True), "source": source})
        requirement = {
            key: item.get(key)
            for key in (
                "id",
                "requirement_class",
                "source_intent_ref",
                "source_intent_revision",
                "source_intent_current",
                "evidence_owner",
                "evidence_state",
                "detail_route",
                "measurement",
            )
            if item.get(key) is not None
        }
        effect = {"kind": effect_kind, "target": target, "requirement": requirement}
        if effect_kind == "require":
            effect["satisfier"] = satisfier
        clauses.append(
            {
                "id": f"repo-requirement:{item_id}",
                "source": source,
                "when": {"fact": fact_id, "operator": "is", "value": True},
                "effects": [effect],
                "authority": {"effects": [effect_kind], "target_patterns": [target]},
            }
        )
    for index, item in enumerate([_as_dict(value) for value in _as_list(mechanisms.get("bounded_controls"))]):
        item_id = str(item.get("id") or f"bounded-control-{index + 1}")
        owner = str(item.get("owner") or "bounded-controls")
        revision = str(item.get("revision") or "")
        effect_kind = str(item.get("effect") or "")
        target = str(item.get("target") or "")
        if effect_kind not in EFFECT_KINDS or not target:
            source_diagnostics.append(
                {
                    "code": "invalid-bounded-control",
                    "ref": f"adapter:bounded_controls:{item_id}",
                    "owner": owner,
                    "repair": "provide one surface/prefer/require/restrict effect with an explicit bounded target",
                }
            )
            continue
        fact_id = f"mechanism:{item_id}:applicable"
        effect: dict[str, Any] = {"kind": effect_kind, "target": target}
        if effect_kind == "require":
            effect["satisfier"] = str(item.get("satisfier") or "")
        source = {"owner": owner, "revision": revision, "current": bool(revision)}
        facts.append({"id": fact_id, "type": "boolean", "value": item.get("applicable", True), "source": source})
        clauses.append(
            {
                "id": f"adapter:bounded_controls:{item_id}",
                "source": source,
                "when": {"fact": fact_id, "operator": "is", "value": True},
                "effects": [effect],
                "authority": {"effects": [effect_kind], "target_patterns": [target]},
            }
        )
    return {
        "kind": "agentic-workspace/instruction-program/v1",
        "facts": facts,
        "clauses": clauses,
        "capabilities": capabilities,
        "source_diagnostics": source_diagnostics,
    }
