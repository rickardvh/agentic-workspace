#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

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
    parser.add_argument("--kind", required=True, choices=sorted(TEMPLATE_BY_KIND), help="Issue template kind to render.")
    parser.add_argument("--title", default="", help="Issue title without the template prefix.")
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
        value = fields.get(field_id, _default_value(item)).strip()
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
    fields = dict(args.field)
    rendered = render_issue(kind=args.kind, title=args.title, fields=fields)
    if args.format == "json":
        json.dump(rendered, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(rendered["body"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
