"""Small Markdown-first repository instruction authoring and compilation surface."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from agentic_workspace.semantic_task_routes import (
    current_semantic_task_route_fact,
    discover_semantic_routes,
    route_selector_matches,
    select_semantic_task_routes,
)

INSTRUCTION_DIR = Path(".agentic-workspace/instructions")
FRONTMATTER_FIELDS = ("paths", "routes", "read", "use", "checks", "protect")
_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_DISPOSITION_PREFIX = "<!-- agentic-workspace:context-disposition "


@dataclass(frozen=True)
class InstructionDocument:
    identity: str
    source_ref: str
    revision: str
    metadata: dict[str, list[Any]]
    body: str
    has_guidance: bool
    body_loaded: bool
    diagnostics: tuple[dict[str, str], ...]


def _digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _instruction_text_without_dispositions(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.startswith(_DISPOSITION_PREFIX)).rstrip() + "\n"


def instruction_maintenance_disposition(path: Path, *, candidate_id: str) -> dict[str, Any]:
    """Read one source-owned semantic disposition and revalidate its source semantics."""

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    for line in reversed(text.splitlines()):
        if not line.startswith(_DISPOSITION_PREFIX) or not line.endswith(" -->"):
            continue
        try:
            record = json.loads(line[len(_DISPOSITION_PREFIX) : -4])
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and record.get("candidate_id") == candidate_id:
            current_semantic_revision = _digest(_instruction_text_without_dispositions(text))
            return {
                **record,
                "current_semantic_revision": current_semantic_revision,
                "status": "current" if record.get("source_semantic_revision") == current_semantic_revision else "stale",
            }
    return {}


def _instruction_disposition_marker(*, base_text: str, record: dict[str, Any]) -> str:
    clean = _instruction_text_without_dispositions(base_text)
    payload = {**record, "source_semantic_revision": _digest(clean)}
    retained_lines: list[str] = []
    for line in base_text.splitlines():
        if line.startswith(_DISPOSITION_PREFIX) and line.endswith(" -->"):
            try:
                existing = json.loads(line[len(_DISPOSITION_PREFIX) : -4])
            except json.JSONDecodeError:
                existing = {}
            if isinstance(existing, dict) and existing.get("candidate_id") == record.get("candidate_id"):
                continue
        retained_lines.append(line)
    retained = "\n".join(retained_lines).rstrip()
    return retained + "\n\n" + _DISPOSITION_PREFIX + json.dumps(payload, sort_keys=True, separators=(",", ":")) + " -->\n"


def _valid_repo_pattern(value: str) -> bool:
    normalized = value.strip()
    if not normalized or "\\" in normalized or normalized.startswith(("/", "~")) or re.match(r"^[A-Za-z]:", normalized):
        return False
    return ".." not in Path(normalized).parts


def _frontmatter(path: Path, *, load_body: bool) -> tuple[dict[str, list[Any]], str, bool, bool, list[dict[str, str]]]:
    metadata: dict[str, list[Any]] = {field: [] for field in FRONTMATTER_FIELDS}
    diagnostics: list[dict[str, str]] = []
    try:
        handle = path.open(encoding="utf-8")
    except OSError as exc:
        return metadata, "", False, False, [{"field": "file", "code": "unreadable", "message": str(exc)}]
    with handle:
        first = handle.readline()
        if first.rstrip("\r\n") != "---":
            remainder = handle.read()
            body = first + remainder if load_body else ""
            return metadata, body.strip(), bool((first + remainder).strip()), load_body, diagnostics
        current = ""
        closed = False
        for raw in handle:
            line = raw.rstrip("\r\n")
            if line == "---":
                closed = True
                break
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if not line.startswith((" ", "-")) and ":" in line:
                key, value = line.split(":", 1)
                current = key.strip()
                if current not in FRONTMATTER_FIELDS:
                    diagnostics.append({"field": current, "code": "unknown-field", "message": f"use only {', '.join(FRONTMATTER_FIELDS)}"})
                    continue
                value = value.strip()
                if value:
                    if value.startswith("[") and value.endswith("]"):
                        metadata[current].extend(item.strip().strip("'\"") for item in value[1:-1].split(",") if item.strip())
                    else:
                        diagnostics.append({"field": current, "code": "invalid-shape", "message": "use a YAML list or a short inline list"})
                continue
            stripped = line.strip()
            if stripped.startswith("-") and current in FRONTMATTER_FIELDS:
                value = stripped[1:].strip()
                if current == "checks" and value.startswith("run:"):
                    command = value.removeprefix("run:").strip()
                    metadata[current].append({"run": command})
                else:
                    metadata[current].append(value.strip("'\""))
                continue
            diagnostics.append({"field": current or "frontmatter", "code": "invalid-syntax", "message": f"cannot parse `{stripped}`"})
        if not closed:
            diagnostics.append({"field": "frontmatter", "code": "unterminated", "message": "add the closing --- line"})
            return metadata, "", False, False, diagnostics
        remainder = handle.read()
        body = remainder.strip() if load_body else ""
        return metadata, body, bool(remainder.strip()), load_body, diagnostics


def _validate_metadata(metadata: dict[str, list[Any]]) -> list[dict[str, str]]:
    diagnostics: list[dict[str, str]] = []
    for field in ("paths", "read", "protect"):
        for index, value in enumerate(metadata[field]):
            if not isinstance(value, str) or not _valid_repo_pattern(value):
                diagnostics.append(
                    {
                        "field": f"{field}[{index}]",
                        "code": "invalid-repo-pattern",
                        "message": "use a non-empty repo-relative path or glob without `..`, a drive, or a leading slash",
                    }
                )
    for index, value in enumerate(metadata["routes"]):
        normalized = str(value).strip().strip("/")
        route_id = normalized.removesuffix("/**")
        if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*(?:/[a-z0-9][a-z0-9-]*)+", route_id):
            diagnostics.append(
                {
                    "field": f"routes[{index}]",
                    "code": "invalid-semantic-route-selector",
                    "message": "use an exact route id or an explicit /** subtree selector",
                }
            )
    for index, value in enumerate(metadata["use"]):
        if not isinstance(value, str) or not value.strip():
            diagnostics.append({"field": f"use[{index}]", "code": "invalid-reference", "message": "name one admitted capability"})
    for index, value in enumerate(metadata["checks"]):
        if isinstance(value, dict):
            command = str(value.get("run") or "").strip()
            if set(value) != {"run"} or not command or "\n" in command:
                diagnostics.append(
                    {"field": f"checks[{index}]", "code": "invalid-inline-check", "message": "use `- run: <trusted repo command>`"}
                )
        elif not isinstance(value, str) or not value.strip():
            diagnostics.append({"field": f"checks[{index}]", "code": "invalid-reference", "message": "name one admitted check"})
    return diagnostics


def read_instruction(path: Path, *, root: Path, load_body: bool = False) -> InstructionDocument:
    try:
        source_ref = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        source_ref = path.as_posix()
    metadata, body, has_guidance, body_loaded, diagnostics = _frontmatter(path, load_body=load_body)
    diagnostics.extend(_validate_metadata(metadata))
    try:
        revision = _digest(path.read_text(encoding="utf-8"))
    except OSError:
        revision = ""
    return InstructionDocument(
        identity=path.stem,
        source_ref=source_ref,
        revision=revision,
        metadata=metadata,
        body=body,
        has_guidance=has_guidance,
        body_loaded=body_loaded,
        diagnostics=tuple(diagnostics),
    )


def instruction_documents(root: Path, *, load_bodies: bool = False) -> list[InstructionDocument]:
    directory = root / INSTRUCTION_DIR
    if not directory.is_dir():
        return []
    return [read_instruction(path, root=root, load_body=load_bodies) for path in sorted(directory.glob("*.md")) if path.is_file()]


def _matched_paths(patterns: list[str], changed_paths: Iterable[str]) -> list[str]:
    normalized = [str(path).replace("\\", "/") for path in changed_paths]
    return sorted({path for path in normalized for pattern in patterns if fnmatch.fnmatch(path, pattern)})


def instruction_applies(
    document: InstructionDocument,
    *,
    changed_paths: list[str],
    selected_routes: list[str] | None = None,
    route_posture: str = "unresolved",
) -> tuple[bool, str, list[str]]:
    patterns = [str(item) for item in document.metadata["paths"]]
    matched = _matched_paths(patterns, changed_paths)
    path_applies = not patterns or bool(matched)
    route_selectors = [str(item) for item in document.metadata["routes"]]
    route_applies = not route_selectors or (
        route_posture == "selected" and any(route_selector_matches(selector, selected_routes or []) for selector in route_selectors)
    )
    if path_applies and route_applies:
        reasons: list[str] = []
        if patterns:
            reasons.append(f"{matched[0]} matches {next(pattern for pattern in patterns if fnmatch.fnmatch(matched[0], pattern))}")
        else:
            reasons.append("global path scope")
        if route_selectors:
            reasons.append("selected semantic route matches " + ", ".join(route_selectors))
        return True, "; ".join(reasons), matched
    reasons = []
    if not path_applies:
        reasons.append("no changed or target path matches " + ", ".join(patterns))
    if not route_applies:
        reasons.append(
            "semantic route selection is " + route_posture
            if route_posture != "selected"
            else "no selected semantic route matches " + ", ".join(route_selectors)
        )
    return False, "; ".join(reasons), matched


def _capability_candidates(root: Path) -> dict[str, list[str]]:
    identities: set[str] = set()
    for skills_root in (root / ".agentic-workspace/skills", root / ".agents/skills", root / "tools/skills"):
        if skills_root.is_dir():
            identities.update(f"skill:{path.parent.name}" for path in skills_root.glob("*/SKILL.md"))
    registry = Path(__file__).resolve().parent / "contracts" / "operation_contracts.json"
    if registry.is_file():
        try:
            payload = json.loads(registry.read_text(encoding="utf-8"))
            identities.update(
                f"operation:{item['id']}" for item in payload.get("operations", []) if isinstance(item, dict) and item.get("id")
            )
        except (OSError, json.JSONDecodeError):
            pass
    config_path = root / ".agentic-workspace/config.toml"
    if config_path.is_file():
        try:
            config = tomllib.loads(config_path.read_text(encoding="utf-8-sig"))
            requirements = config.get("assurance", {}).get("requirements", {})
            if isinstance(requirements, dict):
                identities.update(
                    f"requirement:{requirement_id}"
                    for requirement_id, requirement in requirements.items()
                    if isinstance(requirement, dict) and requirement.get("requirement_class")
                )
        except (OSError, tomllib.TOMLDecodeError):
            pass
    candidates: dict[str, list[str]] = {}
    for identity in sorted(identities):
        short = identity.partition(":")[2].rsplit(".", 1)[-1]
        candidates.setdefault(short, []).append(identity)
        candidates.setdefault(identity, []).append(identity)
    return candidates


def _resolve_reference(value: str, *, candidates: dict[str, list[str]], field: str) -> tuple[str, dict[str, str] | None]:
    matches = sorted(set(candidates.get(value, [])))
    if len(matches) == 1:
        return matches[0], None
    if not matches:
        return "", {"field": field, "code": "missing-reference", "message": f"`{value}` is not an admitted capability"}
    return "", {
        "field": field,
        "code": "ambiguous-reference",
        "message": f"`{value}` matches {', '.join(matches)}; use a qualified identity",
    }


def inspect_instructions(
    root: Path,
    *,
    task: str = "",
    changed_paths: list[str] | None = None,
    include_ir: bool = False,
    evidence: dict[str, bool] | None = None,
) -> dict[str, Any]:
    del task  # Semantic applicability is an explicit current-task fact, never inferred from prompt text.
    changed = [str(item).replace("\\", "/") for item in (changed_paths or [])]
    route_fact = current_semantic_task_route_fact(root)
    route_posture = str(route_fact.get("posture") or "unresolved") if route_fact.get("status") == "current" else "unresolved"
    selected_routes = [str(item) for item in route_fact.get("routes", [])] if route_posture == "selected" else []
    candidates = _capability_candidates(root)
    records: list[dict[str, Any]] = []
    diagnostics: list[dict[str, str]] = []
    program: dict[str, Any] = {
        "kind": "agentic-workspace/instruction-program/v1",
        "facts": [],
        "clauses": [],
        "capabilities": [],
        "source_diagnostics": [],
    }
    for shallow in instruction_documents(root):
        applies, reason, matched = instruction_applies(
            shallow,
            changed_paths=changed,
            selected_routes=selected_routes,
            route_posture=route_posture,
        )
        document = read_instruction(root / shallow.source_ref, root=root, load_body=applies)
        item_diagnostics = [dict(item) for item in document.diagnostics]
        resolved_use: list[str] = []
        resolved_checks: list[dict[str, str]] = []
        for index, value in enumerate(document.metadata["use"]):
            resolved, diagnostic = _resolve_reference(str(value), candidates=candidates, field=f"use[{index}]")
            if diagnostic:
                item_diagnostics.append(diagnostic)
            else:
                resolved_use.append(resolved)
        for index, value in enumerate(document.metadata["read"]):
            reference = str(value)
            if not any(marker in reference for marker in "*?[") and not (root / reference).is_file():
                item_diagnostics.append(
                    {
                        "field": f"read[{index}]",
                        "code": "missing-resource",
                        "message": f"`{reference}` is not a readable repo-owned file",
                    }
                )
        for index, value in enumerate(document.metadata["checks"]):
            if isinstance(value, dict):
                command = str(value.get("run") or "").strip()
                check_id = "instruction-check:" + document.identity + ":" + hashlib.sha256(command.encode()).hexdigest()[:16]
                resolved_checks.append({"identity": check_id, "command": command, "kind": "inline"})
            else:
                resolved, diagnostic = _resolve_reference(str(value), candidates=candidates, field=f"checks[{index}]")
                if diagnostic:
                    item_diagnostics.append(diagnostic)
                else:
                    check_id = "instruction-check:" + resolved
                    resolved_checks.append(
                        {
                            "identity": check_id,
                            "reference": resolved,
                            "kind": "requirement" if resolved.startswith("requirement:") else "named",
                        }
                    )
        for diagnostic in item_diagnostics:
            diagnostics.append({"source_ref": document.source_ref, **diagnostic})
        record = {
            "id": document.identity,
            "source_ref": document.source_ref,
            "revision": document.revision,
            "scope": document.metadata["paths"] or ["global"],
            "routes": document.metadata["routes"],
            "valid": not item_diagnostics,
            "applies": applies,
            "reason": reason,
            "matched_paths": matched,
            "body_loaded": document.body_loaded,
            "features": [
                name
                for name, present in (
                    ("guidance", document.has_guidance),
                    ("routes", bool(document.metadata["routes"])),
                    ("read", bool(document.metadata["read"])),
                    ("use", bool(document.metadata["use"])),
                    ("checks", bool(document.metadata["checks"])),
                    ("protect", bool(document.metadata["protect"])),
                )
                if present
            ],
            "guidance": document.body if applies else "",
            "read": document.metadata["read"] if applies else [],
            "use": resolved_use if applies else [],
            "checks": resolved_checks if applies else [],
            "protect": document.metadata["protect"] if applies else [],
            "diagnostics": item_diagnostics,
        }
        records.append(record)
        if applies and item_diagnostics:
            program["source_diagnostics"].extend(
                {
                    "code": "invalid-bounded-control",
                    "ref": f"{document.source_ref}:{diagnostic['field']}",
                    "owner": "repo-instructions",
                    "repair": diagnostic["message"],
                }
                for diagnostic in item_diagnostics
            )
        if not applies or item_diagnostics:
            continue
        fact_id = f"instruction:{document.identity}:applies"
        source = {
            "owner": "repo-instructions",
            "revision": _digest(
                document.revision + str(route_fact.get("current_source_revision") or route_fact.get("source_revision") or "")
            ),
            "current": route_fact.get("status") != "stale",
        }
        program["facts"].append({"id": fact_id, "type": "boolean", "value": True, "source": source})
        effects: list[dict[str, str]] = []
        if document.body:
            effects.append({"kind": "surface", "target": f"surface:instruction:{document.identity}"})
        effects.extend({"kind": "surface", "target": f"surface:{ref}"} for ref in document.metadata["read"])
        effects.extend({"kind": "prefer", "target": ref} for ref in resolved_use)
        for check in resolved_checks:
            if check["kind"] == "requirement":
                effects.append({"kind": "surface", "target": f"surface:{check['reference']}"})
                continue
            satisfier = check["identity"]
            effects.append({"kind": "require", "target": "claim:complete", "satisfier": satisfier})
            program["capabilities"].append(
                {
                    "id": satisfier,
                    "kind": "evidence",
                    "current": bool((evidence or {}).get(satisfier, False)),
                    "source": {"owner": "proof", "revision": document.revision, "current": True},
                }
            )
        effects.extend({"kind": "restrict", "target": f"effect:write:{pattern}"} for pattern in document.metadata["protect"])
        if effects:
            program["clauses"].append(
                {
                    "id": f"scoped-markdown:{document.identity}",
                    "source": source,
                    "when": {"fact": fact_id, "operator": "is", "value": True},
                    "effects": effects,
                    "authority": {
                        "effects": sorted({effect["kind"] for effect in effects}),
                        "target_patterns": [effect["target"] for effect in effects],
                    },
                }
            )
    payload: dict[str, Any] = {
        "kind": "agentic-workspace/scoped-instruction-inspection/v1",
        "status": "invalid" if diagnostics else "valid",
        "instruction_count": len(records),
        "applicable_count": sum(item["applies"] for item in records),
        "instructions": records,
        "diagnostics": diagnostics,
        "semantic_task_routes": route_fact,
        "progressive_disclosure": {
            "irrelevant_bodies_loaded": sum(item["body_loaded"] for item in records if not item["applies"]),
            "rule": "Only matching global, path, or explicitly selected-route instruction bodies enter the current operating contract.",
        },
    }
    if include_ir:
        payload["instruction_program"] = program
    return payload


def instruction_program_for_operating_decision(
    *, root: Path, task: str, changed_paths: list[str], evidence: dict[str, bool] | None = None
) -> dict[str, Any]:
    return inspect_instructions(root, task=task, changed_paths=changed_paths, include_ir=True, evidence=evidence)["instruction_program"]


def _render_text(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    for item in payload.get("instructions", []):
        scope = "global" if item["scope"] == ["global"] else ", ".join(item["scope"])
        state = "valid" if item["valid"] else "invalid"
        lines.append(f"{item['id']:<20} {scope:<24} {state}")
        if item.get("applies"):
            lines.append(f"  because {item['reason']}")
            if item.get("features"):
                lines.append("  " + " · ".join(item["features"]))
        elif "reason" in item:
            lines.append(f"  not applicable: {item['reason']}")
    for diagnostic in payload.get("diagnostics", []):
        lines.extend(["", str(diagnostic["source_ref"]), f"  {diagnostic['field']}: {diagnostic['message']}"])
    return "\n".join(lines) if lines else "No scoped repository instructions found."


def _write_scaffold(root: Path, *, name: str, paths: list[str]) -> dict[str, Any]:
    if not _NAME.fullmatch(name):
        raise ValueError("instruction name must use lowercase letters, digits, and hyphens")
    invalid = [pattern for pattern in paths if not _valid_repo_pattern(pattern)]
    if invalid:
        raise ValueError(f"invalid repo-relative path pattern: {invalid[0]}")
    destination = root / INSTRUCTION_DIR / f"{name}.md"
    if destination.exists():
        raise FileExistsError(f"instruction already exists: {destination.relative_to(root).as_posix()}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    title = " ".join(part.capitalize() for part in name.split("-"))
    frontmatter = ""
    if paths:
        frontmatter = "---\npaths:\n" + "".join(f"  - {pattern}\n" for pattern in paths) + "---\n\n"
    destination.write_text(f"{frontmatter}# {title}\n\n<!-- Write the guidance an agent needs in this scope. -->\n", encoding="utf-8")
    return {
        "kind": "agentic-workspace/scoped-instruction-create-result/v1",
        "status": "created",
        "source_ref": destination.relative_to(root).as_posix(),
        "scope": paths or ["global"],
    }


def _apply_admitted_adaptation(root: Path, *, values: dict[str, Any]) -> dict[str, Any]:
    authority_ref = str(values.get("adaptation_authority_path") or "").strip().replace("\\", "/")
    expected_revision = str(values.get("adaptation_expected_revision") or "").strip()
    admitted_by = str(values.get("owner_admission_by") or "").strip()
    if str(values.get("owner_admission") or "") != "admitted" or not admitted_by:
        raise ValueError("instruction adaptation requires explicit owner admission and an admitting owner")
    authority_path = (root / authority_ref).resolve()
    instruction_root = (root / INSTRUCTION_DIR).resolve()
    try:
        authority_path.relative_to(instruction_root)
    except ValueError as exc:
        raise ValueError("instruction adaptation authority must stay inside .agentic-workspace/instructions") from exc
    if authority_path.suffix != ".md" or not authority_path.is_file():
        raise ValueError("instruction adaptation authority must name one existing Markdown instruction")
    current = read_instruction(authority_path, root=root, load_body=True)
    if current.revision != expected_revision:
        return {
            "kind": "agentic-workspace/scoped-instruction-adaptation-result/v1",
            "status": "blocked-stale-authority-revision",
            "authority_path": authority_ref,
            "expected_authority_revision": expected_revision,
            "current_authority_revision": current.revision,
            "post_authority_revision": current.revision,
            "validation_status": "not-run",
            "rollback": {"available": True, "performed": False, "restored_pre_apply_bytes": False},
        }
    disposition_raw = str(values.get("adaptation_disposition_json") or "").strip()
    disposition: dict[str, Any] = {}
    if disposition_raw:
        try:
            parsed_disposition = json.loads(disposition_raw)
        except json.JSONDecodeError as exc:
            raise ValueError("instruction adaptation disposition must be a JSON object") from exc
        if not isinstance(parsed_disposition, dict):
            raise ValueError("instruction adaptation disposition must be a JSON object")
        allowed_disposition_fields = {"candidate_id", "choice", "decision_revision", "defer_until", "admitted_by"}
        if set(parsed_disposition) - allowed_disposition_fields:
            raise ValueError("instruction adaptation disposition contains unsupported fields")
        if not str(parsed_disposition.get("candidate_id") or "") or parsed_disposition.get("choice") not in {
            "admit",
            "update",
            "retain",
            "defer",
            "dismiss",
        }:
            raise ValueError("instruction adaptation disposition requires candidate identity and supported choice")
        if parsed_disposition.get("choice") == "defer" and not str(parsed_disposition.get("defer_until") or ""):
            raise ValueError("deferred instruction disposition requires a re-entry trigger")
        disposition = {**parsed_disposition, "admitted_by": admitted_by}
    prior_bytes = authority_path.read_bytes()
    prior_text = prior_bytes.decode("utf-8")
    if str(values.get("adaptation_mode") or "") == "disposition":
        if not disposition:
            raise ValueError("instruction disposition mode requires a source-owned disposition record")
        updated_text = _instruction_disposition_marker(base_text=prior_text, record=disposition)
        if bool(values.get("dry_run")):
            return {
                "kind": "agentic-workspace/scoped-instruction-adaptation-result/v1",
                "status": "dry-run",
                "authority_path": authority_ref,
                "expected_authority_revision": expected_revision,
                "post_authority_revision": current.revision,
                "validation_status": "simulated",
                "disposition_record": disposition,
                "rollback": {"available": True, "performed": False, "restored_pre_apply_bytes": False},
            }
        temporary = authority_path.with_name(f"{authority_path.name}.{expected_revision.removeprefix('sha256:')[:12]}.tmp")
        try:
            temporary.write_text(updated_text, encoding="utf-8")
            temporary.replace(authority_path)
            updated = read_instruction(authority_path, root=root, load_body=True)
            if updated.diagnostics:
                authority_path.write_bytes(prior_bytes)
                return {
                    "kind": "agentic-workspace/scoped-instruction-adaptation-result/v1",
                    "status": "blocked-validation-failed",
                    "authority_path": authority_ref,
                    "expected_authority_revision": expected_revision,
                    "post_authority_revision": expected_revision,
                    "validation_status": "failed",
                    "validation_failures": [dict(item) for item in updated.diagnostics],
                    "rollback": {"available": True, "performed": True, "restored_pre_apply_bytes": True},
                }
            persisted = instruction_maintenance_disposition(authority_path, candidate_id=str(disposition["candidate_id"]))
            return {
                "kind": "agentic-workspace/scoped-instruction-adaptation-result/v1",
                "status": "applied",
                "authority_path": authority_ref,
                "expected_authority_revision": expected_revision,
                "post_authority_revision": updated.revision,
                "validation_status": "passed",
                "disposition_record": persisted,
                "owner_admission": {"status": "admitted", "admitted_by": admitted_by},
                "rollback": {"available": True, "performed": False, "restored_pre_apply_bytes": False},
            }
        except Exception:
            if authority_path.read_bytes() != prior_bytes:
                authority_path.write_bytes(prior_bytes)
            raise
        finally:
            temporary.unlink(missing_ok=True)
    try:
        delta = json.loads(str(values.get("adaptation_delta_json") or ""))
    except json.JSONDecodeError as exc:
        raise ValueError("instruction adaptation delta must be a JSON object") from exc
    if not isinstance(delta, dict) or set(delta) - {"action", "heading", "guidance", "positive_paths", "negative_paths"}:
        raise ValueError("instruction adaptation delta contains unsupported fields")
    if delta.get("action") != "append_guidance":
        raise ValueError("instruction adaptation supports only append_guidance")
    heading = str(delta.get("heading") or "").strip()
    guidance = str(delta.get("guidance") or "").strip()
    positive_paths = [str(item) for item in delta.get("positive_paths", [])] if isinstance(delta.get("positive_paths"), list) else []
    negative_paths = [str(item) for item in delta.get("negative_paths", [])] if isinstance(delta.get("negative_paths"), list) else []
    if not heading or not guidance or len(heading) > 120 or len(guidance) > 4000:
        raise ValueError("instruction adaptation requires bounded heading and guidance text")
    if any(marker in heading or marker in guidance for marker in ("---", "<!--")):
        raise ValueError("instruction adaptation cannot inject frontmatter or hidden controls")
    if not positive_paths or any(not _valid_repo_pattern(path) for path in [*positive_paths, *negative_paths]):
        raise ValueError("instruction adaptation requires valid positive applicability paths")
    section = f"## {heading}\n\n{guidance}"
    if section in prior_text and not disposition:
        return {
            "kind": "agentic-workspace/scoped-instruction-adaptation-result/v1",
            "status": "already-applied",
            "authority_path": authority_ref,
            "expected_authority_revision": expected_revision,
            "post_authority_revision": current.revision,
            "validation_status": "passed",
            "owner_admission": {"status": "admitted", "admitted_by": admitted_by},
            "rollback": {"available": True, "performed": False, "restored_pre_apply_bytes": False},
        }
    if bool(values.get("dry_run")):
        return {
            "kind": "agentic-workspace/scoped-instruction-adaptation-result/v1",
            "status": "dry-run",
            "authority_path": authority_ref,
            "expected_authority_revision": expected_revision,
            "post_authority_revision": current.revision,
            "validation_status": "simulated",
            "owner_admission": {"status": "admitted", "admitted_by": admitted_by},
            "rollback": {"available": True, "performed": False, "restored_pre_apply_bytes": False},
        }
    temporary = authority_path.with_name(f"{authority_path.name}.{expected_revision.removeprefix('sha256:')[:12]}.tmp")
    try:
        if read_instruction(authority_path, root=root).revision != expected_revision:
            return {
                "kind": "agentic-workspace/scoped-instruction-adaptation-result/v1",
                "status": "blocked-stale-authority-revision",
                "authority_path": authority_ref,
                "expected_authority_revision": expected_revision,
                "current_authority_revision": read_instruction(authority_path, root=root).revision,
                "post_authority_revision": read_instruction(authority_path, root=root).revision,
                "validation_status": "not-run",
                "rollback": {"available": True, "performed": False, "restored_pre_apply_bytes": False},
            }
        updated_text = prior_text if section in prior_text else prior_text.rstrip() + f"\n\n{section}\n"
        if disposition:
            updated_text = _instruction_disposition_marker(base_text=updated_text, record=disposition)
        temporary.write_text(updated_text, encoding="utf-8")
        temporary.replace(authority_path)
        updated = read_instruction(authority_path, root=root, load_body=True)
        failures = [dict(item) for item in updated.diagnostics]
        for path in positive_paths:
            applies, _, _ = instruction_applies(updated, changed_paths=[path])
            if not applies:
                failures.append({"field": "positive_paths", "code": "not-applicable", "message": path})
        for path in negative_paths:
            applies, _, _ = instruction_applies(updated, changed_paths=[path])
            if applies:
                failures.append({"field": "negative_paths", "code": "unexpectedly-applicable", "message": path})
        if inspect_instructions(root, changed_paths=positive_paths).get("status") != "valid":
            failures.append({"field": "instruction-set", "code": "invalid", "message": "static instruction check failed"})
        if failures:
            authority_path.write_bytes(prior_bytes)
            return {
                "kind": "agentic-workspace/scoped-instruction-adaptation-result/v1",
                "status": "blocked-validation-failed",
                "authority_path": authority_ref,
                "expected_authority_revision": expected_revision,
                "post_authority_revision": expected_revision,
                "validation_status": "failed",
                "validation_failures": failures,
                "owner_admission": {"status": "admitted", "admitted_by": admitted_by},
                "rollback": {"available": True, "performed": True, "restored_pre_apply_bytes": True},
            }
        return {
            "kind": "agentic-workspace/scoped-instruction-adaptation-result/v1",
            "status": "applied",
            "authority_path": authority_ref,
            "expected_authority_revision": expected_revision,
            "post_authority_revision": updated.revision,
            "validation_status": "passed",
            "validated_positive_paths": positive_paths,
            "validated_negative_paths": negative_paths,
            "owner_admission": {"status": "admitted", "admitted_by": admitted_by},
            "rollback": {"available": True, "performed": False, "restored_pre_apply_bytes": False},
        }
    except Exception:
        if authority_path.read_bytes() != prior_bytes:
            authority_path.write_bytes(prior_bytes)
        raise
    finally:
        temporary.unlink(missing_ok=True)


def _migration_advice(root: Path, source: str) -> dict[str, Any]:
    path = (root / source).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("migration source must stay inside the repository") from exc
    text = path.read_text(encoding="utf-8")
    headings = [line.lstrip("#").strip() for line in text.splitlines() if line.startswith("## ")]
    return {
        "kind": "agentic-workspace/scoped-instruction-migration-advice/v1",
        "status": "review-required",
        "source_ref": path.relative_to(root).as_posix(),
        "candidate_headings": headings,
        "writes_applied": False,
        "steps": [
            "Choose one coherent guidance block and its intended scope.",
            "Scaffold a scoped instruction and move the guidance with human or agent judgment.",
            "Run instructions check and positive/negative instructions explain scenarios.",
            "Remove the static block only after behavior is verified; retain a thin bootstrap.",
        ],
    }


def apply_instruction_operation(*, target_root: Path, operation_id: str, values: dict[str, Any]) -> dict[str, Any]:
    """Execute one generated instruction operation while retaining semantic ownership here."""

    try:
        if operation_id == "instructions.create":
            payload = (
                _apply_admitted_adaptation(target_root, values=values)
                if values.get("adaptation_mode")
                else _write_scaffold(
                    target_root,
                    name=str(values.get("name") or ""),
                    paths=[str(item) for item in values.get("paths", [])],
                )
            )
        elif operation_id == "instructions.migrate":
            payload = _migration_advice(target_root, str(values.get("source") or ""))
        elif operation_id == "instructions.routes":
            payload = discover_semantic_routes(
                target_root,
                parent=str(values.get("parent") or ""),
                exact=str(values.get("exact") or ""),
            )
        elif operation_id == "instructions.route-select":
            payload = select_semantic_task_routes(
                target_root,
                posture=str(values.get("posture") or ""),
                routes=[str(item) for item in values.get("route", [])],
                expected_source_revision=str(values.get("expected_source_revision") or ""),
                current_work_id=str(values.get("current_work_id") or ""),
                dry_run=bool(values.get("dry_run", False)),
            )
        elif operation_id in {"instructions.list", "instructions.check", "instructions.explain"}:
            payload = inspect_instructions(
                target_root,
                task=str(values.get("task") or ""),
                changed_paths=[str(item) for item in values.get("changed", [])],
                include_ir=bool(values.get("verbose", False)),
            )
        else:
            raise ValueError(f"unsupported instruction operation: {operation_id}")
    except (OSError, ValueError) as exc:
        return {
            "kind": "agentic-workspace/scoped-instruction-error/v1",
            "operation_id": operation_id,
            "status": "failed",
            "message": str(exc),
            "exit_status": 2,
            "outcome": "blocked",
            "mutation_applied": False,
            "reason_code": "instruction-operation-rejected",
            "conflict_owner": "scoped-instructions",
            "recovery_command": "agentic-workspace instructions check --target . --format json",
        }
    payload["operation_id"] = operation_id
    if operation_id == "instructions.routes":
        payload["message"] = "\n".join(str(item.get("id") or "") for item in payload.get("routes", []))
    elif operation_id == "instructions.route-select":
        payload["message"] = f"Semantic task route selection: {payload.get('status', 'unknown')}"
    else:
        payload["message"] = _render_text(payload)
    if operation_id == "instructions.check" and payload.get("status") == "invalid":
        payload["exit_status"] = 2
    if operation_id == "instructions.create" and values.get("adaptation_mode"):
        status = str(payload.get("status") or "")
        payload.update(
            {
                "outcome": "applied" if status in {"applied", "already-applied"} else "planned" if status == "dry-run" else "blocked",
                "mutation_applied": status == "applied",
                "reason_code": f"instruction-adaptation-{status}",
                "conflict_owner": "" if status in {"applied", "already-applied", "dry-run"} else "scoped-instructions",
                "recovery_command": ""
                if status in {"applied", "already-applied", "dry-run"}
                else "agentic-workspace instructions check --target . --format json",
            }
        )
    elif operation_id == "instructions.create" and payload.get("status") == "created":
        payload.update(
            {
                "outcome": "applied",
                "mutation_applied": True,
                "reason_code": "instruction-created",
                "conflict_owner": "",
                "recovery_command": "",
            }
        )
    return payload
