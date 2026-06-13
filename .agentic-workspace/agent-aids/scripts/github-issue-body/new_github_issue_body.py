#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
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
    "bounded_slice_success",
    "partial_pr_may_close",
    "required_follow_up_owner",
    "required_residual_intent",
    "evidence_required_for_final_completion",
}

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
    parser.add_argument(
        "--input-json",
        default="",
        metavar="PATH",
        help="Read an agentic-workspace/issue-body-request/v1 JSON request from PATH, or '-' for stdin.",
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
    if field_id == "bounded_slice_success":
        return (
            "A partial slice may land when it is coherent, proves its local behavior, records remaining intent, "
            "and names the continuation owner."
        )
    if field_id == "partial_pr_may_close":
        return "no"
    if field_id == "required_follow_up_owner":
        return "This issue remains the follow-up owner unless a specific owner is named."
    if field_id == "required_residual_intent":
        return "Any part of final satisfaction not delivered by a partial slice remains open here."
    if field_id == "evidence_required_for_final_completion":
        if evidence_hint:
            return f"Final completion evidence must prove the final intended state, including: {evidence_hint}"
        return "Proof or review evidence must show the final intended outcome, not only a useful local change."
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
        if args.input_json:
            if args.kind or args.field:
                raise ValueError("--input-json must not be combined with --kind or --field")
            rendered = render_issue_request(_load_request(args.input_json))
        else:
            if not args.kind:
                raise ValueError("--kind is required unless --input-json is supplied")
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
