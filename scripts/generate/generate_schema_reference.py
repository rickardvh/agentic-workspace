from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA = Path("src/agentic_workspace/contracts/schemas/workspace_config.schema.json")
DEFAULT_OUTPUT = Path("docs/reference/workspace-config.md")
SCHEMA_ROOT = Path("src/agentic_workspace/contracts/schemas")


@dataclass(frozen=True)
class ReferenceTarget:
    schema_path: Path
    output_path: Path


def _default_targets() -> tuple[ReferenceTarget, ...]:
    targets: list[ReferenceTarget] = []
    for schema_path in sorted((REPO_ROOT / SCHEMA_ROOT).glob("*.schema.json")):
        relative_schema_path = schema_path.relative_to(REPO_ROOT)
        output_name = schema_path.name.removesuffix(".schema.json").replace("_", "-")
        if relative_schema_path == DEFAULT_SCHEMA:
            output_path = DEFAULT_OUTPUT
        else:
            output_path = Path("docs/reference") / f"{output_name}.md"
        targets.append(ReferenceTarget(relative_schema_path, output_path))
    return tuple(targets)


DEFAULT_TARGETS = _default_targets()
MECHANICAL_DESCRIPTION_PATTERNS = (
    re.compile(r"^The .+ field in .+\.$"),
    re.compile(r"^Item .+ accepted by .+ in .+\.$"),
    re.compile(r"^Reusable .+ definition for .+\.$"),
    re.compile(r"^Allowed .+ variant for .+\.$"),
    re.compile(r"^Additional named .+ entry for .+ in .+\.$"),
    re.compile(r"^Pattern-matched .+ entry for .+ in .+\.$"),
    re.compile(r"^Schema for .+\.$"),
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _format_json(value: Any) -> str:
    return "`" + json.dumps(value, sort_keys=True) + "`"


def _is_mechanical_description(value: str) -> bool:
    return any(pattern.match(value) for pattern in MECHANICAL_DESCRIPTION_PATTERNS)


def _format_examples(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, list):
        return _format_json(value)
    return "<br>".join(_format_json(item) for item in value)


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


def _schema_type(schema: dict[str, Any]) -> str:
    if "$ref" in schema:
        return f"ref `{schema['$ref']}`"
    if "const" in schema:
        return f"const {_format_json(schema['const'])}"
    if "enum" in schema:
        return "enum " + ", ".join(_format_json(item) for item in schema["enum"])
    raw_type = schema.get("type")
    if isinstance(raw_type, list):
        return " | ".join(str(item) for item in raw_type)
    if isinstance(raw_type, str):
        if raw_type == "array" and isinstance(schema.get("items"), dict):
            return f"array of {_schema_type(schema['items'])}"
        return raw_type
    if "anyOf" in schema:
        return "anyOf"
    return ""


def _anchor_for(path: str) -> str:
    anchor = path.lower()
    for char in (".", "/", "_", "$", "#", "[", "]", "^", "+"):
        anchor = anchor.replace(char, "-")
    anchor = "".join(char for char in anchor if char.isalnum() or char == "-")
    while "--" in anchor:
        anchor = anchor.replace("--", "-")
    return anchor.strip("-")


def _resolve_ref(schema: dict[str, Any], ref: str) -> dict[str, Any]:
    prefix = "#/$defs/"
    if not ref.startswith(prefix):
        return {}
    name = ref[len(prefix) :]
    target = schema.get("$defs", {}).get(name)
    return target if isinstance(target, dict) else {}


def _iter_fields(
    *,
    root_schema: dict[str, Any],
    schema: dict[str, Any],
    path: str,
    required: set[str],
    seen_refs: set[str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    properties = schema.get("properties", {})
    if isinstance(properties, dict):
        for name, child in properties.items():
            if not isinstance(child, dict):
                continue
            child_path = f"{path}.{name}" if path else name
            effective_child = child
            ref = child.get("$ref")
            if isinstance(ref, str):
                resolved = _resolve_ref(root_schema, ref)
                effective_child = {**resolved, **child} if resolved else child
            row = _field_row(child_path=child_path, child=effective_child, required=name in required)
            rows.append(row)
            child_seen_refs = set(seen_refs)
            if isinstance(ref, str):
                if ref in child_seen_refs:
                    continue
                child_seen_refs.add(ref)
            child_required = set(effective_child.get("required", [])) if isinstance(effective_child.get("required"), list) else set()
            rows.extend(
                _iter_fields(
                    root_schema=root_schema,
                    schema=effective_child,
                    path=child_path,
                    required=child_required,
                    seen_refs=child_seen_refs,
                )
            )
    pattern_properties = schema.get("patternProperties", {})
    if isinstance(pattern_properties, dict):
        for pattern, child in pattern_properties.items():
            if not isinstance(child, dict):
                continue
            child_path = f"{path}.<{pattern}>" if path else f"<{pattern}>"
            effective_child = child
            ref = child.get("$ref")
            if isinstance(ref, str):
                resolved = _resolve_ref(root_schema, ref)
                effective_child = {**resolved, **child} if resolved else child
            rows.append(_field_row(child_path=child_path, child=effective_child, required=False))
            child_required = set(effective_child.get("required", [])) if isinstance(effective_child.get("required"), list) else set()
            rows.extend(
                _iter_fields(
                    root_schema=root_schema,
                    schema=effective_child,
                    path=child_path,
                    required=child_required,
                    seen_refs=set(seen_refs),
                )
            )
    additional = schema.get("additionalProperties")
    if isinstance(additional, dict):
        child_path = f"{path}.<name>" if path else "<name>"
        rows.append(_field_row(child_path=child_path, child=additional, required=False))
        child_required = set(additional.get("required", [])) if isinstance(additional.get("required"), list) else set()
        rows.extend(
            _iter_fields(
                root_schema=root_schema,
                schema=additional,
                path=child_path,
                required=child_required,
                seen_refs=set(seen_refs),
            )
        )
    return rows


def _field_row(*, child_path: str, child: dict[str, Any], required: bool) -> dict[str, str]:
    extensions = []
    for key in sorted(child):
        if key.startswith("x-agentic-workspace-"):
            extensions.append(f"{key}: {json.dumps(child[key], sort_keys=True)}")
    return {
        "path": child_path,
        "type": _schema_type(child),
        "required": "yes" if required else "no",
        "default": _format_json(child["default"]) if "default" in child else "",
        "description": str(child.get("description", "")),
        "examples": _format_examples(child.get("examples")),
        "annotations": "<br>".join(extensions),
    }


def render_schema_reference(schema_path: Path, *, repo_root: Path = REPO_ROOT) -> str:
    absolute_schema_path = repo_root / schema_path
    schema = _load_json(absolute_schema_path)
    title = str(schema.get("title") or schema_path.stem)
    description = str(schema.get("description") or "")
    rows = [
        _field_row(child_path="(root)", child=schema, required=True),
        *_iter_fields(
            root_schema=schema,
            schema=schema,
            path="",
            required=set(schema.get("required", [])) if isinstance(schema.get("required"), list) else set(),
            seen_refs=set(),
        ),
    ]

    lines = [
        "<!-- GENERATED FILE: edit the source schema and rerun `make render-schema-reference`. -->",
        f"# {title}",
        "",
        description,
        "",
        f"- Source schema: `{schema_path.as_posix()}`",
        "- Generated by: `scripts/generate/generate_schema_reference.py`",
        "",
    ]
    see_also = schema.get("x-agentic-workspace-see-also")
    if isinstance(see_also, list) and see_also:
        lines.extend(["## See Also", ""])
        for item in see_also:
            lines.append(f"- `{item}`")
        lines.append("")

    lines.extend(
        [
            "## Fields",
            "",
            "| Field | Type | Required | Default | Description | Examples | Annotations |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        field = row["path"]
        lines.append(
            "| "
            + " | ".join(
                _escape_table(value)
                for value in (
                    f"`{field}`" if field != "(root)" else "(root)",
                    row["type"],
                    row["required"],
                    row["default"],
                    row["description"],
                    row["examples"],
                    row["annotations"],
                )
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def _annotation_errors(schema_path: Path, *, repo_root: Path = REPO_ROOT) -> list[str]:
    schema = _load_json(repo_root / schema_path)
    errors: list[str] = []
    rows = [
        _field_row(child_path="(root)", child=schema, required=True),
        *_iter_fields(
            root_schema=schema,
            schema=schema,
            path="",
            required=set(schema.get("required", [])) if isinstance(schema.get("required"), list) else set(),
            seen_refs=set(),
        ),
    ]
    for row in rows:
        if not row["description"]:
            errors.append(f"{schema_path.as_posix()} field {row['path']} is missing description")
        elif _is_mechanical_description(row["description"]):
            errors.append(f"{schema_path.as_posix()} field {row['path']} has mechanical description: {row['description']}")
    if not schema.get("x-agentic-workspace-doc-role"):
        errors.append(f"{schema_path.as_posix()} root is missing x-agentic-workspace-doc-role")
    if schema_path == DEFAULT_SCHEMA:
        for public_field in (
            "workspace.default_preset",
            "workspace.agent_instructions_file",
            "workspace.workflow_artifact_profile",
            "workspace.improvement_latitude",
            "workspace.optimization_bias",
            "workspace.advanced_features",
        ):
            matching = next((row for row in rows if row["path"] == public_field), None)
            if matching is None:
                errors.append(f"{schema_path.as_posix()} field {public_field} is missing from generated rows")
            elif not matching["default"]:
                errors.append(f"{schema_path.as_posix()} field {public_field} is missing default annotation")
    return errors


def render_targets(targets: tuple[ReferenceTarget, ...] = DEFAULT_TARGETS, *, repo_root: Path = REPO_ROOT) -> list[tuple[Path, str]]:
    return [(target.output_path, render_schema_reference(target.schema_path, repo_root=repo_root)) for target in targets]


def generate(*, targets: tuple[ReferenceTarget, ...] = DEFAULT_TARGETS, repo_root: Path = REPO_ROOT, check: bool = False) -> list[Path]:
    stale: list[Path] = []
    for output_path, content in render_targets(targets, repo_root=repo_root):
        absolute_output_path = repo_root / output_path
        if check:
            current = absolute_output_path.read_text(encoding="utf-8") if absolute_output_path.exists() else ""
            if current != content:
                stale.append(output_path)
            continue
        absolute_output_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_output_path.write_text(content, encoding="utf-8")
    return stale


def _parse_schema_target(raw: str) -> ReferenceTarget:
    if "=" in raw:
        schema, output = raw.split("=", 1)
        return ReferenceTarget(Path(schema), Path(output))
    schema_path = Path(raw)
    output_name = schema_path.name.removesuffix(".schema.json").replace("_", "-")
    return ReferenceTarget(schema_path, Path("docs/reference") / f"{output_name}.md")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Markdown reference docs from annotated JSON Schemas.")
    parser.add_argument(
        "--schema",
        action="append",
        help="Schema path, or schema=output. Defaults to workspace_config.schema.json.",
    )
    parser.add_argument("--check", action="store_true", help="Fail if generated docs are stale.")
    parser.add_argument("--check-annotations", action="store_true", help="Fail if configured schemas miss required doc annotations.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    targets = tuple(_parse_schema_target(item) for item in args.schema) if args.schema else DEFAULT_TARGETS
    errors: list[str] = []
    if args.check_annotations:
        for target in targets:
            errors.extend(_annotation_errors(target.schema_path))
    stale = generate(targets=targets, check=bool(args.check))
    if stale:
        errors.extend(f"{path.as_posix()} is stale; rerun `make render-schema-reference`." for path in stale)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    if args.check or args.check_annotations:
        print("[ok] schema reference docs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
