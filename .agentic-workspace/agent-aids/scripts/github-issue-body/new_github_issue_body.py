#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
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


def _digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _identity(path: Path, root: Path) -> dict[str, str]:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"source path must stay inside the repository: {path}")
    return {"path": resolved.relative_to(root.resolve()).as_posix(), "revision": _digest(resolved.read_bytes())}


def _load_request(path: str) -> dict[str, Any]:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("request must be a JSON object")
    return payload


def validate_issue_body_request(payload: dict[str, Any]) -> dict[str, Any]:
    errors = sorted(ISSUE_BODY_REQUEST_VALIDATOR.iter_errors(payload), key=lambda error: str(list(error.path)))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.path) or "<root>"
        raise ValueError(f"issue body request schema error at {location}: {error.message}")
    return payload


def _required(item: dict[str, Any]) -> bool:
    return bool(item.get("validations", {}).get("required")) or (
        item.get("type") == "checkboxes" and any(option.get("required") for option in item["attributes"].get("options", []))
    )


def render_issue_request(
    payload: dict[str, Any], *, target_root: Path = REPO_ROOT, previous: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Prepare fresh every time; a previous packet is comparison data only."""
    validate_issue_body_request(payload)
    root = target_root.resolve()
    template_path = root / ".github" / "ISSUE_TEMPLATE" / TEMPLATE_BY_KIND[payload["template"]]
    template_bytes = template_path.read_bytes()
    template = yaml.safe_load(template_bytes)
    if not isinstance(template, dict) or not isinstance(template.get("body"), list):
        raise ValueError("current issue form must define a body")
    definitions: dict[str, dict[str, Any]] = {}
    for item in template["body"]:
        if not isinstance(item, dict):
            raise ValueError("current issue form contains a malformed field")
        if item.get("type") == "markdown":
            continue
        field_id = item.get("id")
        attributes = item.get("attributes", {})
        validations = item.get("validations", {})
        if not isinstance(attributes, dict) or not isinstance(validations, dict):
            raise ValueError("current issue form has malformed attributes or validations")
        if "render" in attributes and (
            item.get("type") != "textarea"
            or not isinstance(attributes["render"], str)
            or not re.fullmatch(r"[A-Za-z0-9_+.-]+", attributes["render"])
        ):
            raise ValueError(f"unsupported render attribute for {field_id}; use the Markdown procedure")
        if item.get("type") in {"dropdown", "checkboxes"}:
            options = attributes.get("options")
            if not isinstance(options, list) or not options:
                raise ValueError("current issue form options must be a nonempty list")
            if item["type"] == "dropdown" and not all(isinstance(option, str) for option in options):
                raise ValueError("current dropdown options must be strings")
            if item["type"] == "checkboxes" and not all(
                isinstance(option, dict) and isinstance(option.get("label"), str) for option in options
            ):
                raise ValueError("current checkbox options must have string labels")
        if not field_id or field_id in definitions or not attributes.get("label"):
            raise ValueError("current issue form has missing/duplicate field identities or labels")
        if item.get("type") not in {"input", "textarea", "dropdown", "checkboxes"} or attributes.get("multiple"):
            raise ValueError(f"unsupported current form field {field_id}; use the Markdown procedure")
        definitions[field_id] = item

    fields = {key: value["value"] for key, value in payload["fields"].items()}
    problems: list[dict[str, str]] = []
    for field_id in sorted(fields.keys() - definitions.keys()):
        problems.append({"field": field_id, "reason": "unknown field in current form"})
    sections = []
    for field_id, item in definitions.items():
        value = fields.get(field_id, "")
        if not value.strip():
            if _required(item):
                problems.append({"field": field_id, "reason": "required shaped value missing"})
            continue
        attributes = item["attributes"]
        # Reject obvious placeholders, not substantive discussion of TODO handling.
        if re.fullmatch(r"(?is)(?:TODO(?:\s*:.*)?|TBD|\.\.\.|- \[ \] \.\.\.)", value.strip()):
            problems.append({"field": field_id, "reason": "placeholder requires shaped content"})
        if item["type"] == "dropdown" and value not in attributes.get("options", []):
            problems.append({"field": field_id, "reason": "value is not a current form option"})
        if item["type"] == "checkboxes":
            options = attributes.get("options", [])
            checked = {f"- [x] {option['label']}" for option in options}
            allowed = checked | {f"- [ ] {option['label']}" for option in options}
            lines = value.splitlines()
            required = {f"- [x] {option['label']}" for option in options if option.get("required")}
            if not set(lines) <= allowed or len(lines) != len(set(lines)) or not required <= set(lines):
                problems.append({"field": field_id, "reason": "supply current checkbox options and explicitly check required options"})
        if "render" in attributes:
            # Keep supplied backtick fences inside the code block, never as structure.
            fence = "`" * max(3, 1 + max((len(run) for run in re.findall(r"`+", value)), default=0))
            ending = "" if value.endswith("\n") else "\n"
            value = f"{fence}{attributes['render']}\n{value}{ending}{fence}"
        sections.append(f"## {attributes['label']}\n{value}")

    prefix = str(template.get("title", "")).strip()
    raw_title = payload.get("title", "").strip()
    duplicate = bool(prefix and raw_title.startswith(prefix))
    title = raw_title.removeprefix(prefix).strip() if duplicate else raw_title
    if not title or re.fullmatch(r"(?i)TODO|TBD|\.\.\.", title):
        problems.append({"field": "title", "reason": "substantive title missing"})
    labels = template.get("labels", [])
    if not isinstance(labels, list) or not all(isinstance(label, str) for label in labels):
        raise ValueError("current form labels must be a list of strings")

    sources = []
    for ref in payload.get("source_refs", []):
        if "path" in ref:
            sources.append({"reference": ref, "identity": _identity(root / ref["path"], root), "status": "observed"})
        else:
            # Supplied issue IDs/URLs are not observed external state.
            sources.append({"reference": ref, "status": "external-currentness-unobserved"})
    identities = {
        "template": {"path": template_path.relative_to(root).as_posix(), "revision": _digest(template_bytes)},
        "helper": _identity(Path(__file__), REPO_ROOT),
        "shaped_input": {"revision": _digest(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8"))},
        "sources": sources,
    }
    changed = []
    comparison = "not-requested"
    if previous is not None:
        prior = previous.get("identities")
        if previous.get("kind") != "agentic-workspace/issue-preparation/v1" or not isinstance(prior, dict):
            comparison = "unavailable"
        else:
            changed = [key for key, value in identities.items() if prior.get(key) != value]
            comparison = "stale" if changed else "current"
    result = {
        "kind": "agentic-workspace/issue-preparation/v1",
        "request_kind": payload["kind"],
        "status": "needs-input" if problems else "prepared",
        "authority": "read-only preparation; no semantic, external-currentness, or issue-write authority",
        "template": template_path.name,
        "title_prefix": prefix,
        "input_title": raw_title,
        "normalized_title": title,
        "duplicate_prefix_normalized": duplicate,
        "title": f"{prefix} {title}".strip(),
        "labels": labels,
        "body": None if problems else "\n\n".join(sections) + "\n",
        "problems": problems,
        "identities": identities,
        "source_refs": payload.get("source_refs", []),
        "comparison": {"status": comparison, "changed": changed, "scope": "declared local preparation inputs only"},
    }
    if problems:
        result["form_fields"] = [
            {
                "id": key,
                "type": item["type"],
                "required": _required(item),
                "attributes": item["attributes"],
            }
            for key, item in definitions.items()
        ]
    return result


def render_issue(*, kind: str, title: str, fields: dict[str, str], target_root: Path = REPO_ROOT) -> dict[str, Any]:
    return render_issue_request(
        {
            "kind": "agentic-workspace/issue-body-request/v1",
            "template": kind,
            "title": title,
            "fields": {key: {"kind": "markdown", "value": value} for key, value in fields.items()},
        },
        target_root=target_root,
    )


def prepare_creation(payload: dict[str, Any], *, repository: str, task: str, target_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Pure external request; the caller's transport owns write authorization."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or not task.strip():
        raise ValueError("An exact owner/repository and nonblank task are required")
    prepared = render_issue_request(payload, target_root=target_root)
    if prepared["status"] != "prepared":
        return prepared
    material = {
        "repository": repository,
        "task": task,
        "preparation": prepared,
        "write": {key: prepared[key] for key in ("title", "body", "labels")},
    }
    return {
        "kind": "agentic-workspace/issue-creation-request/v1",
        "status": "prepared",
        "request_id": _digest(json.dumps(material, sort_keys=True, ensure_ascii=False).encode()),
        "material": material,
        "authority": "No write authority; an authorized actor must carry this exact request through its GitHub transport.",
        "recovery": "After a possibly committed attempt, reobserve the issue; never retry creation from this packet alone.",
    }


def validate_creation_request(request: dict[str, Any]) -> dict[str, Any]:
    material = request.get("material")
    if request.get("kind") != "agentic-workspace/issue-creation-request/v1" or not isinstance(material, dict):
        raise ValueError("Expected the exact prepared creation request")
    expected = _digest(json.dumps(material, sort_keys=True, ensure_ascii=False).encode())
    if request.get("request_id") != expected:
        raise ValueError("Creation material changed; prepare again before effect")
    if material.get("write") != {key: material["preparation"].get(key) for key in ("title", "body", "labels")}:
        raise ValueError("Creation request and prepared issue disagree")
    return material


def observe_created_issue(repository: str, number: int) -> dict[str, Any]:
    """Read one exact object through the caller's existing GitHub transport."""
    response = subprocess.run(
        ["gh", "api", f"repos/{repository}/issues/{number}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=True,
    )
    return json.loads(response.stdout)


def continue_creation(
    request: dict[str, Any],
    result: dict[str, Any],
    *,
    current: dict[str, Any] | None = None,
    observer=None,
    continuation=None,
) -> dict[str, Any]:
    """Admit an actor's effect report by reobservation; never perform creation."""
    material = validate_creation_request(request)
    observer = observer or observe_created_issue
    if result.get("request_id") != request["request_id"]:
        raise ValueError("External result belongs to a different creation request")
    outcome = result.get("outcome")
    if outcome not in {"rejected-before-effect", "confirmed", "uncertain"}:
        raise ValueError("External actor must distinguish rejection, confirmed effect and uncertainty")
    response: dict[str, Any] = {
        "kind": "agentic-workspace/issue-creation-result/v1",
        "request_id": request["request_id"],
        "retry_creation": False,
        "effect_outcome": "unknown",
        "status": "effect-uncertain",
        "continuation": {"status": "not-requested"},
        "currentness": "current" if current and current.get("request_id") == request["request_id"] else "stale-or-unavailable",
    }
    if outcome == "rejected-before-effect":
        if result.get("effect_attempted") is not False or not result.get("reason"):
            raise ValueError("Rejection requires the authorized actor's explicit no-effect report and reason")
        response.update(status="rejected-before-effect", effect_outcome="not-committed", reason=result["reason"])
        return response
    number = result.get("number")
    if type(number) is not int or number <= 0:
        response["recovery"] = (
            "Ask the authorized transport to reobserve the possibly created issue and return its exact number; do not repeat create."
        )
        return response
    try:
        observed = observer(material["repository"], number)
        expected_url = f"https://github.com/{material['repository']}/issues/{number}"
        if observed.get("number") != number or observed.get("html_url") != expected_url or observed.get("pull_request"):
            raise ValueError("Reobserved object does not match the exact repository/issue")
        actual = {
            "title": observed.get("title"),
            "body": observed.get("body"),
            "labels": sorted(label["name"] for label in observed.get("labels", [])),
        }
        expected = {**material["write"], "labels": sorted(material["write"]["labels"])}
        if actual != expected:
            response.update(
                status="external-result-mismatch",
                observed_issue={"number": number, "url": expected_url},
                recovery="Reconcile this observed object with the authorized actor; a mismatch is not permission to create again.",
            )
            return response
        response.update(status="created", effect_outcome="committed", issue={"number": number, "url": expected_url, **actual})
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as error:
        response["recovery"] = "Reobserve the exact issue through the authorized transport; creation must not be replayed."
        response["observation_error"] = type(error).__name__
        return response
    if continuation is not None:
        if response["currentness"] != "current":
            response["continuation"] = {
                "status": "unavailable",
                "reason": "Reprepare current owner continuation after material drift; creation remains committed.",
            }
        else:
            try:
                response["continuation"] = {"status": "returned-owner-result", "result": continuation(response["issue"])}
            except (OSError, subprocess.SubprocessError, ValueError) as error:
                response["continuation"] = {"status": "unavailable", "reason": type(error).__name__}
    return response


def _parse_field(value: str) -> tuple[str, str]:
    if "=" not in value or not value.split("=", 1)[0].strip():
        raise argparse.ArgumentTypeError("fields must use nonblank id=value")
    key, field_value = value.split("=", 1)
    return key.strip(), field_value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only preparation of shaped issues from the current repository form.")
    parser.add_argument("--input-json", default="", metavar="PATH", help="Shaped request JSON, or '-' for stdin.")
    parser.add_argument("--kind", choices=sorted(TEMPLATE_BY_KIND))
    parser.add_argument("--title", default="")
    parser.add_argument("--field", action="append", type=_parse_field, default=[])
    parser.add_argument("--target", default=str(REPO_ROOT), help="Repository containing the current forms and local source refs.")
    parser.add_argument("--previous", default="", metavar="PATH", help="Compare a prior preparation; always prepare fresh.")
    parser.add_argument("--repository", default="", help="Exact owner/repo for compound preparation.")
    parser.add_argument("--task", default="", help="Work identity for compound preparation.")
    parser.add_argument("--creation-request", default="", help="Exact prior compound request; compare before effect or resume after it.")
    parser.add_argument("--external-result", default="", help="Actor report bound to request_id; this helper only reobserves GitHub.")
    parser.add_argument(
        "--continuation-input", default="", help="Separately authorized current native owner request; never inferred from creation."
    )
    parser.add_argument("--native-cli", default="agentic-workspace")
    parser.add_argument("--format", choices=("body", "json"), default="json")
    args = parser.parse_args(argv)
    try:
        if args.input_json and (args.kind or args.field or args.title):
            raise ValueError("--input-json cannot be mixed with --kind, --field, or --title")
        if len(dict(args.field)) != len(args.field):
            raise ValueError("duplicate --field values are ambiguous")
        if args.input_json:
            try:
                payload = _load_request(args.input_json)
            except (ValueError, OSError):
                if not args.external_result:
                    raise
                payload = {}  # Still reobserve a possibly committed external effect.
        else:
            if not args.kind and not args.external_result:
                raise ValueError("--kind or --input-json is required")
            payload = {
                "kind": "agentic-workspace/issue-body-request/v1",
                "template": args.kind,
                "title": args.title,
                "fields": {key: {"kind": "markdown", "value": value} for key, value in args.field},
            }
        if args.external_result and not args.creation_request:
            raise ValueError("External result requires its exact creation request")
        if args.continuation_input and not args.external_result:
            raise ValueError("Owner continuation requires a confirmed external result")
        if args.repository or args.creation_request:
            prior = _load_request(args.creation_request) if args.creation_request else None
            try:
                current = prepare_creation(payload, repository=args.repository, task=args.task, target_root=Path(args.target))
            except (ValueError, OSError, yaml.YAMLError):
                if not args.external_result:
                    raise
                current = None  # A later preparation error cannot erase an external effect.
            if args.external_result:

                def owner_continuation(issue):
                    # The owner receives only its exact caller-supplied request. An
                    # issue result never fabricates an owner ingestion operation.
                    response = subprocess.run(
                        [
                            args.native_cli,
                            "start",
                            "--target",
                            args.target,
                            "--task",
                            args.task,
                            "--input",
                            args.continuation_input,
                            "--format",
                            "json",
                        ],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        timeout=60,
                        check=True,
                    )
                    return json.loads(response.stdout)

                result = continue_creation(
                    prior,
                    _load_request(args.external_result),
                    current=current,
                    continuation=owner_continuation if args.continuation_input else None,
                )
            elif prior:
                validate_creation_request(prior)
                result = (
                    current
                    if current and current.get("request_id") == prior["request_id"]
                    else {"status": "stale", "retry_creation": False, "reason": "Reprepare and renew authorization before any effect."}
                )
            else:
                result = current
        else:
            result = render_issue_request(
                payload, target_root=Path(args.target), previous=_load_request(args.previous) if args.previous else None
            )
    except (ValueError, OSError, yaml.YAMLError) as exc:
        print(
            json.dumps(
                {"status": "unavailable", "reason": str(exc), "recovery": "Repair input/environment or use the Markdown procedure."}
            ),
            file=sys.stderr,
        )
        return 2
    if args.format == "body":
        if result.get("body") is not None:
            sys.stdout.write(result["body"])
        else:
            print(json.dumps(result), file=sys.stderr)
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] in {"prepared", "created", "rejected-before-effect"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
