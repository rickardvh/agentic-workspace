#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[4]
ISSUE_TEMPLATE_ROOT = REPO_ROOT / ".github" / "ISSUE_TEMPLATE"
TEMPLATE_BY_KIND = {
    "direction": "01-direction-proposal.yml",
    "proposal": "01-direction-proposal.yml",
    "planning": "01-direction-proposal.yml",
    "bug": "02-bug-regression.yml",
    "regression": "02-bug-regression.yml",
    "review": "03-review-friction.yml",
    "friction": "03-review-friction.yml",
    "dogfooding": "03-review-friction.yml",
}

COMPLETION_BOUNDARY_FIELDS = {
    "final_satisfaction",
    "evidence_required_for_final_completion",
    "non_solutions",
    "completion_rule",
}

DEFAULT_NON_SOLUTIONS = """The following do not close this issue unless explicitly listed in the acceptance criteria:

- documenting the problem without changing the affected behavior;
- adding an inventory without completing the requested change;
- reclassifying or renaming the current behavior while preserving the old dependency/path;
- adding a follow-up issue instead of completing the stated outcome;
- changing tests to accept the current behavior rather than making the intended behavior true."""

DEFAULT_COMPLETION_RULE = (
    "A PR may close this issue only if the intended outcome is true in the ordinary path, "
    "not merely documented, inventoried, reclassified, or deferred."
)

ISSUE_BODY_REQUEST_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["kind", "template", "fields"],
    "additionalProperties": False,
    "properties": {
        "kind": {"const": "agentic-workspace/issue-body-request/v1"},
        "template": {"enum": sorted(TEMPLATE_BY_KIND)},
        "title": {"type": "string"},
        "fields": {
            "type": "object",
            "minProperties": 1,
            "additionalProperties": {
                "type": "object",
                "required": ["kind", "value"],
                "additionalProperties": False,
                "properties": {
                    "kind": {"enum": ["markdown", "text", "scalar"]},
                    "value": {"type": "string"},
                },
            },
        },
        "source_refs": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["kind"],
                "additionalProperties": {"type": ["string", "number", "boolean"]},
                "properties": {
                    "kind": {"type": "string", "minLength": 1},
                    "id": {"type": "string"},
                    "path": {"type": "string"},
                    "url": {"type": "string"},
                },
                "anyOf": [
                    {"required": ["id"]},
                    {"required": ["path"]},
                    {"required": ["url"]},
                ],
            },
        },
    },
}
ISSUE_BODY_REQUEST_VALIDATOR = Draft202012Validator(ISSUE_BODY_REQUEST_SCHEMA)


def _parse_field(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("fields must use id=value")
    key, field_value = value.split("=", 1)
    key = key.strip()
    if not key:
        raise argparse.ArgumentTypeError("field id must not be blank")
    return key, field_value


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a GitHub issue body from this repo's issue-form templates.")
    parser.add_argument("--kind", choices=sorted(TEMPLATE_BY_KIND), help="Issue template kind to render.")
    parser.add_argument("--title", default="", help="Issue title without the template prefix.")
    parser.add_argument("--target", default=str(REPO_ROOT), help="Repository root for Planning source loading.")
    parser.add_argument(
        "--input-json",
        default="",
        metavar="PATH",
        help="Read an agentic-workspace/issue-body-request/v1 JSON request from PATH, or '-' for stdin.",
    )
    parser.add_argument("--from-lane", default="", metavar="ID", help="Render from a Planning lane record by id.")
    parser.add_argument(
        "--from-decomposition",
        default="",
        metavar="PATH",
        help="Render from a Planning decomposition JSON file.",
    )
    parser.add_argument(
        "--lane-id",
        default="",
        help="Candidate lane id to select when --from-decomposition contains multiple lanes.",
    )
    parser.add_argument(
        "--field",
        action="append",
        type=_parse_field,
        default=[],
        metavar="ID=VALUE",
        help="Template field value. Repeat for multiple fields.",
    )
    parser.add_argument("--format", choices=("body", "json"), default="body", help="Output body only or JSON metadata.")
    return parser.parse_args(argv)


def _repo_relative(path: Path, *, target_root: Path) -> str:
    try:
        return path.resolve().relative_to(target_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _slugify(value: str) -> str:
    chars: list[str] = []
    previous_dash = False
    for char in value.strip().lower():
        if char.isalnum():
            chars.append(char)
            previous_dash = False
        elif not previous_dash:
            chars.append("-")
            previous_dash = True
    return "".join(chars).strip("-")


def _typed(value: str) -> dict[str, str]:
    return {"kind": "markdown", "value": value}


def _issue_body_request(*, title: str, fields: dict[str, str], source_refs: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "kind": "agentic-workspace/issue-body-request/v1",
        "template": "direction",
        "title": title,
        "fields": {field_id: _typed(value) for field_id, value in fields.items() if value.strip()},
        "source_refs": source_refs,
    }


def _references_text(source_refs: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for ref in source_refs:
        label = ref.get("id") or ref.get("path") or ref.get("url") or ref.get("kind", "reference")
        details = [ref.get("path", ""), ref.get("url", "")]
        suffix = " ".join(f"({detail})" for detail in details if detail and detail != label)
        lines.append(f"- {label} {suffix}".strip())
    return "\n".join(lines)


def _load_template(kind: str) -> dict[str, Any]:
    path = ISSUE_TEMPLATE_ROOT / TEMPLATE_BY_KIND[kind]
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"Cannot read issue template {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"Issue template {path} did not parse to an object.")
    return payload


def _field_label(item: dict[str, Any]) -> str:
    attributes = item.get("attributes")
    if isinstance(attributes, dict):
        label = str(attributes.get("label", "")).strip()
        if label:
            return label
    return str(item.get("id", "")).replace("_", " ").title()


def _default_value(item: dict[str, Any]) -> str:
    item_type = str(item.get("type", ""))
    attributes = item.get("attributes")
    if isinstance(attributes, dict):
        value = str(attributes.get("value", "")).strip()
        if value:
            return value
    options = attributes.get("options") if isinstance(attributes, dict) else None
    if item_type == "dropdown" and isinstance(options, list) and options:
        first = options[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict):
            return str(first.get("label", "")).strip()
    if item_type == "checkboxes" and isinstance(options, list):
        lines = []
        for option in options:
            if isinstance(option, dict):
                label = str(option.get("label", "")).strip()
                if label:
                    lines.append(f"- [ ] {label}")
        return "\n".join(lines)
    if isinstance(attributes, dict):
        placeholder = str(attributes.get("placeholder", "")).strip()
        if placeholder:
            return f"TODO: {placeholder}"
    return "TODO"


def _first_field(fields: dict[str, str], *field_ids: str) -> str:
    for field_id in field_ids:
        value = str(fields.get(field_id, "")).strip()
        if value:
            return value
    return ""


def _completion_boundary_default(*, field_id: str, fields: dict[str, str]) -> str:
    if field_id not in COMPLETION_BOUNDARY_FIELDS:
        return ""
    final_hint = _first_field(
        fields,
        "intended_outcome",
        "expected_behavior",
        "outcome",
        "desired_signal",
        "acceptance",
    )
    evidence_hint = _first_field(
        fields,
        "acceptance",
        "evidence",
        "reproduction",
        "expected_behavior",
        "desired_signal",
    )
    if field_id == "final_satisfaction":
        if final_hint:
            return f"Final completion requires satisfying: {final_hint}"
        return "The issue is complete only when the final intended outcome is delivered and proven, or explicitly re-scoped by the issue owner."
    if field_id == "evidence_required_for_final_completion":
        if evidence_hint:
            return f"Final completion evidence must prove the final intended state, including: {evidence_hint}"
        return "Proof or review evidence must show the final intended outcome, not only a useful local change."
    if field_id == "non_solutions":
        return DEFAULT_NON_SOLUTIONS
    if field_id == "completion_rule":
        return DEFAULT_COMPLETION_RULE
    return ""


def _load_request(path: str) -> dict[str, Any]:
    try:
        raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read issue body request JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("issue body request must be a JSON object")
    return payload


def _load_json_object(path: Path, *, description: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {description} {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{description} {path} must be a JSON object")
    return payload


def _state_lane_surface(*, target_root: Path, lane_id: str) -> str:
    state_path = target_root / ".agentic-workspace" / "planning" / "state.toml"
    try:
        state = tomllib.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return ""
    roadmap = state.get("roadmap", {})
    lanes = roadmap.get("lanes", []) if isinstance(roadmap, dict) else []
    if not isinstance(lanes, list):
        return ""
    for lane in lanes:
        if not isinstance(lane, dict) or str(lane.get("id", "")).strip() != lane_id:
            continue
        return str(lane.get("owner_surface") or lane.get("surface") or "").strip()
    return ""


def _lane_record_path(*, target_root: Path, lane_id: str) -> Path:
    slug = _slugify(lane_id)
    state_surface = _state_lane_surface(target_root=target_root, lane_id=lane_id)
    candidates = []
    if state_surface:
        candidates.append(target_root / state_surface)
    candidates.extend(
        [
            target_root / ".agentic-workspace" / "planning" / "lanes" / f"{slug}.lane.json",
            target_root / ".agentic-workspace" / "planning" / "lanes" / "archive" / f"{slug}.lane.json",
        ]
    )
    for path in candidates:
        if path.is_file():
            return path
    raise ValueError(f"Planning lane record {lane_id!r} was not found in state, lanes, or lane archive")


def _lane_request_from_record(record: dict[str, Any], *, source_ref: dict[str, str]) -> dict[str, Any]:
    lane_id = str(record.get("id", "")).strip()
    title = str(record.get("title", "")).strip() or lane_id
    outcome = str(record.get("lane_outcome") or "").strip()
    purpose = str(record.get("purpose_for_parent") or "").strip()
    proof = str(record.get("proof_strategy") or "").strip()
    parent = str(record.get("parent_decomposition_ref") or "").strip()
    references = [source_ref]
    if parent:
        references.append({"kind": "planning-decomposition", "path": parent})
    fields = {
        "issue_kind": "Parent direction / lane",
        "parent_issue": parent,
        "problem_intent": purpose or outcome or f"Create a routable issue for Planning lane {lane_id}.",
        "intended_outcome": outcome or f"Planning lane {lane_id} is represented as a GitHub issue.",
        "larger_picture": purpose or f"This issue is generated from Planning lane {lane_id}.",
        "scope": "\n".join(
            line
            for line in [
                "In scope:",
                f"- Lane: {lane_id}",
                f"- Owner surface: {source_ref.get('path', '')}" if source_ref.get("path") else "",
                "",
                "Out of scope:",
                "- Shell-composed semantic field extraction.",
            ]
            if line or line == ""
        ).strip(),
        "acceptance": proof or "The issue body accurately reflects the structured Planning lane record.",
        "final_satisfaction": outcome or "The generated issue is complete when the lane outcome is delivered and proven.",
        "evidence_required_for_final_completion": proof or "Lane proof aggregation must show the final intended state.",
        "planning_expectations": "Generated from structured Planning lane data; do not reconstruct this body with shell property interpolation.",
        "related_references": _references_text(references),
    }
    return _issue_body_request(title=title, fields=fields, source_refs=references)


def request_from_lane(*, target_root: Path, lane_id: str) -> dict[str, Any]:
    path = _lane_record_path(target_root=target_root, lane_id=lane_id)
    record = _load_json_object(path, description="Planning lane record")
    if record.get("kind") != "planning-lane/v1":
        raise ValueError(f"{path} is not a planning-lane/v1 record")
    return _lane_request_from_record(
        record,
        source_ref={
            "kind": "planning-lane",
            "id": str(record.get("id", lane_id)),
            "path": _repo_relative(path, target_root=target_root),
        },
    )


def request_from_decomposition(*, target_root: Path, decomposition: str, lane_id: str = "") -> dict[str, Any]:
    path = (target_root / decomposition).resolve() if not Path(decomposition).is_absolute() else Path(decomposition)
    record = _load_json_object(path, description="Planning decomposition")
    if record.get("kind") != "planning-decomposition/v1":
        raise ValueError(f"{path} is not a planning-decomposition/v1 record")
    lanes = record.get("candidate_lanes")
    if not isinstance(lanes, list) or not lanes:
        raise ValueError(f"{path} does not contain candidate_lanes")
    lane: dict[str, Any] | None = None
    if lane_id:
        lane = next((item for item in lanes if isinstance(item, dict) and str(item.get("id", "")).strip() == lane_id), None)
        if lane is None:
            raise ValueError(f"candidate lane {lane_id!r} was not found in {path}")
    elif len(lanes) == 1 and isinstance(lanes[0], dict):
        lane = lanes[0]
    else:
        raise ValueError("--lane-id is required when a decomposition contains multiple candidate lanes")
    source_path = _repo_relative(path, target_root=target_root)
    source_ref = {
        "kind": "planning-decomposition",
        "id": str(lane.get("id", "")),
        "path": source_path,
    }
    fields = {
        "issue_kind": "Parent direction / lane",
        "parent_issue": source_path,
        "problem_intent": str(lane.get("slice_contribution_to_parent") or lane.get("outcome") or "").strip(),
        "intended_outcome": str(lane.get("outcome") or "").strip(),
        "larger_picture": str(record.get("larger_intended_outcome") or "").strip(),
        "scope": "\n".join(
            [
                "In scope:",
                f"- Candidate lane: {lane.get('id', '')}",
                f"- Owner surface: {lane.get('owner_surface', '')}",
                "",
                "Out of scope:",
                "- Shell/object interpolation of decomposition fields.",
            ]
        ),
        "acceptance": str(lane.get("proof") or "").strip(),
        "final_satisfaction": str(lane.get("outcome") or "").strip(),
        "evidence_required_for_final_completion": str(lane.get("proof") or record.get("parent_acceptance", {}).get("parent_proof_required") or "").strip(),
        "planning_expectations": "Generated from structured Planning decomposition data; select lanes with --lane-id.",
        "related_references": _references_text([source_ref]),
    }
    return _issue_body_request(title=str(lane.get("title", "")).strip(), fields=fields, source_refs=[source_ref])


def _request_fields(payload: dict[str, Any]) -> dict[str, str]:
    raw_fields = payload.get("fields")
    if not isinstance(raw_fields, dict):
        raise ValueError("issue body request must contain object field 'fields'")
    fields: dict[str, str] = {}
    for field_id, field_payload in raw_fields.items():
        normalized_id = str(field_id).strip()
        if not normalized_id:
            raise ValueError("issue body request field ids must not be blank")
        if not isinstance(field_payload, dict):
            raise ValueError(f"field {normalized_id!r} must be an object with kind and value")
        field_kind = str(field_payload.get("kind", "")).strip()
        if field_kind not in {"markdown", "text", "scalar"}:
            raise ValueError(f"field {normalized_id!r} kind must be one of markdown, text, or scalar")
        value = field_payload.get("value")
        if not isinstance(value, str):
            raise ValueError(f"field {normalized_id!r} value must be a string")
        fields[normalized_id] = value
    return fields


def validate_issue_body_request(payload: dict[str, Any]) -> dict[str, Any]:
    schema_errors = sorted(ISSUE_BODY_REQUEST_VALIDATOR.iter_errors(payload), key=lambda error: list(error.path))
    if schema_errors:
        error = schema_errors[0]
        location = ".".join(str(part) for part in error.path) or "<root>"
        raise ValueError(f"issue body request schema error at {location}: {error.message}")
    template = str(payload["template"]).strip()
    title = str(payload.get("title", ""))
    source_refs = payload.get("source_refs", [])
    return {
        "template": template,
        "title": title,
        "fields": _request_fields(payload),
        "source_refs": source_refs,
    }


def render_issue_request(payload: dict[str, Any]) -> dict[str, Any]:
    request = validate_issue_body_request(payload)
    rendered = render_issue(kind=request["template"], title=request["title"], fields=request["fields"])
    rendered["request_kind"] = "agentic-workspace/issue-body-request/v1"
    rendered["source_refs"] = request["source_refs"]
    return rendered


def render_issue(*, kind: str, title: str, fields: dict[str, str]) -> dict[str, Any]:
    template = _load_template(kind)
    title_prefix = str(template.get("title", "")).strip()
    labels = template.get("labels", [])
    if not isinstance(labels, list):
        labels = []
    sections: list[str] = []
    for item in template.get("body", []):
        if not isinstance(item, dict) or item.get("type") == "markdown":
            continue
        field_id = str(item.get("id", "")).strip()
        if not field_id:
            continue
        value = fields.get(field_id, "").strip()
        if not value:
            value = _completion_boundary_default(field_id=field_id, fields=fields)
        if not value:
            value = _default_value(item).strip()
        sections.append(f"## {_field_label(item)}\n{value or 'TODO'}")
    raw_title = title.strip()
    normalized_title = raw_title
    prefix = title_prefix.rstrip()
    duplicate_prefix_normalized = False
    if prefix and raw_title.startswith(prefix):
        normalized_title = raw_title.removeprefix(prefix).strip()
        duplicate_prefix_normalized = True
    rendered_title = f"{prefix} {normalized_title}".strip() if normalized_title else prefix
    return {
        "template": TEMPLATE_BY_KIND[kind],
        "title_prefix": prefix,
        "input_title": raw_title,
        "normalized_title": normalized_title,
        "duplicate_prefix_normalized": duplicate_prefix_normalized,
        "title": rendered_title,
        "labels": [str(label) for label in labels],
        "body": "\n\n".join(sections) + "\n",
    }


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        source_modes = [bool(args.input_json), bool(args.from_lane), bool(args.from_decomposition)]
        if sum(1 for enabled in source_modes if enabled) > 1:
            raise ValueError("--input-json, --from-lane, and --from-decomposition are mutually exclusive")
        if any(source_modes):
            if args.kind or args.field:
                raise ValueError("structured source modes must not be combined with --kind or --field")
        target_root = Path(args.target).resolve()
        if args.input_json:
            rendered = render_issue_request(_load_request(args.input_json))
        elif args.from_lane:
            rendered = render_issue_request(request_from_lane(target_root=target_root, lane_id=args.from_lane))
        elif args.from_decomposition:
            rendered = render_issue_request(
                request_from_decomposition(
                    target_root=target_root,
                    decomposition=args.from_decomposition,
                    lane_id=args.lane_id,
                )
            )
        else:
            if not args.kind:
                raise ValueError("--kind is required unless --input-json is supplied")
            if args.lane_id:
                raise ValueError("--lane-id requires --from-decomposition")
            fields = dict(args.field)
            rendered = render_issue(kind=args.kind, title=args.title, fields=fields)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if args.format == "json":
        json.dump(rendered, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(rendered["body"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
