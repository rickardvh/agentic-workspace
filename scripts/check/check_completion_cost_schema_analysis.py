from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = REPO_ROOT / "src" / "agentic_workspace" / "contracts"
OPERATION_ROOT = CONTRACT_ROOT / "operations"
SCHEMA_ROOT = CONTRACT_ROOT / "schemas"

ORDINARY_OPERATION_IDS = (
    "start.context",
    "implement.context",
    "summary.report",
    "report.combined",
    "config.report",
    "defaults.report",
)

OPERATION_SCHEMA_FALLBACKS = {
    "report.combined": "schemas/workspace_report.schema.json",
}

COST_TYPES = (
    "output noise",
    "reread/re-grounding",
    "proof/test cost",
    "review/repair churn",
    "planning residue",
    "handoff friction",
    "recovery friction",
    "outside-AW provider/tool friction",
)

OWNER_BY_KEYWORD = (
    (("proof", "validation", "test"), "verification/proof-selection"),
    (("memory",), "memory routing"),
    (("planning", "plan", "lane", "execplan", "todo"), "planning"),
    (("handoff", "delegation", "delegate"), "planning handoff/delegation"),
    (("closeout", "closure", "claim", "residue", "intent"), "workspace closeout/intent"),
    (("compatibility", "cli", "install", "payload"), "workspace lifecycle/startup"),
    (("report", "diagnostic", "warning", "detail"), "workspace ordinary outputs"),
)

MEASUREMENT_BY_COST = {
    "output noise": "Measure byte share, empty/default ratio, and actionability density in actual ordinary JSON outputs.",
    "reread/re-grounding": "Correlate with repeated field reads, selector use, and long-horizon reorientation failures.",
    "proof/test cost": "Measure proof command count, repeated broad-proof runs, and failure clustering before reruns.",
    "review/repair churn": "Measure review-loop repeats and duplicated diagnostic text in command logs.",
    "planning residue": "Measure active/roadmap residue volume and stale projection frequency.",
    "handoff friction": "Measure handoff packet size, missing next-action fields, and continuation failures.",
    "recovery friction": "Measure recovery commands needed before a fresh session can resume safely.",
    "outside-AW provider/tool friction": "Record separately; do not route to AW reduction without corroboration.",
}

REDUCTION_BY_COST = {
    "output noise": "Move default-heavy or advisory detail behind selectors, merge duplicates, or shorten ordinary projection.",
    "reread/re-grounding": "Route to one owner surface and expose compact freshness/detail selectors.",
    "proof/test cost": "Add proof liveness checks, retry ladders, or failure clustering before broad reruns.",
    "review/repair churn": "Cluster repeated diagnostics and expose the root actionable failure first.",
    "planning residue": "Close, archive, or route residue to one owner surface with explicit promotion triggers.",
    "handoff friction": "Emit smaller handoff packets with exact next action, proof burden, and stop conditions.",
    "recovery friction": "Add sharper recovery next actions or selector-first diagnostics.",
    "outside-AW provider/tool friction": "Keep as external friction unless AW can route or cache around it safely.",
}


@dataclass(frozen=True)
class Surface:
    operation_id: str
    command: str
    operation_path: Path
    schema_path: Path | None
    selector_available: bool
    detail_available: bool
    skipped_reason: str = ""


def _repo_relative(path: Path) -> str:
    return os.path.relpath(path, REPO_ROOT).replace(os.sep, "/")


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{_repo_relative(path)} must contain a JSON object")
    return payload


def _operation_path(operation_id: str) -> Path:
    return OPERATION_ROOT / f"{operation_id}.json"


def _operation_schema_ref(operation_id: str, operation: dict[str, Any]) -> str:
    output = operation.get("output")
    if isinstance(output, dict):
        schema_ref = output.get("schema_ref")
        if isinstance(schema_ref, str) and schema_ref.strip():
            return schema_ref.strip()
    return OPERATION_SCHEMA_FALLBACKS.get(operation_id, "")


def _surface_from_operation(operation_id: str) -> Surface:
    operation_path = _operation_path(operation_id)
    operation = _load_json(operation_path)
    command_surface = operation.get("command_surface") if isinstance(operation.get("command_surface"), dict) else {}
    inputs = operation.get("inputs") if isinstance(operation.get("inputs"), list) else []
    input_names = {str(item.get("name")) for item in inputs if isinstance(item, dict)}
    guards = operation.get("guards") if isinstance(operation.get("guards"), list) else []
    reads = operation.get("reads") if isinstance(operation.get("reads"), list) else []
    schema_ref = _operation_schema_ref(operation_id, operation)
    schema_path = (CONTRACT_ROOT / schema_ref).resolve() if schema_ref else None
    if schema_path and not schema_path.exists():
        raise FileNotFoundError(f"{operation_id} references missing schema {schema_ref}")
    detail_available = (
        "verbose" in input_names
        or "section" in input_names
        or any("detail" in str(item).lower() or "verbose" in str(item).lower() for item in [*guards, *reads])
    )
    return Surface(
        operation_id=operation_id,
        command=str(command_surface.get("command") or operation_id),
        operation_path=operation_path,
        schema_path=schema_path,
        selector_available="select" in input_names,
        detail_available=detail_available,
        skipped_reason="" if schema_path else "operation has no local output schema_ref or analyzer fallback",
    )


def _resolve_ref(schema: dict[str, Any], ref: str) -> dict[str, Any]:
    prefix = "#/$defs/"
    if not ref.startswith(prefix):
        return {}
    defs = schema.get("$defs") if isinstance(schema.get("$defs"), dict) else {}
    target = defs.get(ref.removeprefix(prefix))
    return target if isinstance(target, dict) else {}


def _merged_node(schema: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    ref = node.get("$ref")
    if not isinstance(ref, str):
        return node
    resolved = _resolve_ref(schema, ref)
    if not resolved:
        return node
    merged = dict(resolved)
    for key, value in node.items():
        if key != "$ref":
            merged[key] = value
    return merged


def _node_type(node: dict[str, Any]) -> set[str]:
    raw = node.get("type")
    if isinstance(raw, str):
        return {raw}
    if isinstance(raw, list):
        return {str(item) for item in raw}
    if "$ref" in node:
        return {"ref"}
    if "properties" in node:
        return {"object"}
    if "items" in node:
        return {"array"}
    return set()


def _walk_schema(
    schema: dict[str, Any],
    node: dict[str, Any],
    *,
    path: tuple[str, ...] = (),
    required: frozenset[str] = frozenset(),
    seen_refs: frozenset[str] = frozenset(),
) -> list[tuple[tuple[str, ...], dict[str, Any], bool]]:
    node = _merged_node(schema, node)
    entries = [(path, node, bool(path and path[-1] in required))]
    properties = node.get("properties")
    if isinstance(properties, dict):
        child_required = frozenset(str(item) for item in node.get("required", []) if isinstance(item, str))
        for name, child in properties.items():
            if isinstance(child, dict):
                entries.extend(_walk_schema(schema, child, path=(*path, str(name)), required=child_required, seen_refs=seen_refs))
    items = node.get("items")
    if isinstance(items, dict):
        entries.extend(_walk_schema(schema, items, path=(*path, "[]"), required=frozenset(), seen_refs=seen_refs))
    ref = node.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/$defs/") and ref not in seen_refs:
        resolved = _resolve_ref(schema, ref)
        if resolved:
            entries.extend(_walk_schema(schema, resolved, path=path, required=required, seen_refs=frozenset({*seen_refs, ref})))
    return entries


def _classify_cost(path: str, description: str, reason_id: str) -> str:
    haystack = f"{path} {description}".lower()
    if "proof" in haystack or "validation" in haystack or "test" in haystack:
        return "proof/test cost"
    if "handoff" in haystack or "delegation" in haystack or "delegate" in haystack:
        return "handoff friction"
    if "closeout" in haystack or "closure" in haystack or "residue" in haystack:
        return "planning residue"
    if "recovery" in haystack or "repair" in haystack or "warning" in haystack or "diagnostic" in haystack:
        return "recovery friction" if "recovery" in haystack else "review/repair churn"
    if "memory" in haystack or "intent" in haystack or "context" in haystack or "continuation" in haystack:
        return "reread/re-grounding"
    if reason_id in {"unbounded_object", "required_large_structure", "deep_required_state"}:
        return "output noise"
    return "output noise"


def _owner_surface(path: str, description: str) -> str:
    haystack = f"{path} {description}".lower()
    for keywords, owner in OWNER_BY_KEYWORD:
        if any(keyword in haystack for keyword in keywords):
            return owner
    return "workspace ordinary outputs"


def _finding(
    *,
    surface: Surface,
    schema_path: Path,
    field_path: str,
    reason_id: str,
    reason: str,
    description: str,
) -> dict[str, Any]:
    cost_type = _classify_cost(field_path, description, reason_id)
    return {
        "surface": surface.operation_id,
        "command": surface.command,
        "schema": _repo_relative(schema_path),
        "field_path": field_path,
        "suspected_cost_type": cost_type,
        "owner_surface": _owner_surface(field_path, description),
        "reason": reason,
        "candidate_measurement": MEASUREMENT_BY_COST[cost_type],
        "candidate_reduction": REDUCTION_BY_COST[cost_type],
        "selector_available": surface.selector_available,
        "detail_available": surface.detail_available,
        "confidence": "medium" if surface.selector_available or surface.detail_available else "high",
    }


def analyze_surface(surface: Surface, *, max_findings_per_surface: int = 12) -> list[dict[str, Any]]:
    if surface.schema_path is None:
        return []
    schema = _load_json(surface.schema_path)
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for path_parts, node, is_required in _walk_schema(schema, schema):
        if not path_parts:
            continue
        node = _merged_node(schema, node)
        field_path = ".".join(path_parts).replace(".[]", "[]")
        description = str(node.get("description") or "")
        types = _node_type(node)
        reason_id = ""
        reason = ""

        if is_required and ("object" in types or "array" in types or "ref" in types):
            reason_id = "required_large_structure"
            reason = "Required structured field can force ordinary readers to process nested state even when the next action is elsewhere."
        if len([part for part in path_parts if part != "[]"]) >= 4 and any(
            token in field_path.lower() for token in ("next", "proof", "closure", "closeout", "claim", "intent", "residue")
        ):
            reason_id = "deep_required_state" if is_required else "deep_state"
            reason = "Deep next-action, proof, intent, or closure state is a likely reread target and should have selector/detail routing."
        if node.get("additionalProperties") is True and any(
            token in field_path.lower() for token in ("diagnostic", "warning", "detail", "context", "advisory", "routing")
        ):
            reason_id = "unbounded_object"
            reason = "Unbounded diagnostic/advisory object can grow in ordinary output without schema-level field budget."
        if description and any(token in description.lower() for token in ("advisory", "diagnostic", "verbose", "detail", "warning")):
            if not surface.selector_available and not surface.detail_available:
                reason_id = "no_selector_escape_hatch"
                reason = "Advisory or diagnostic field appears on an ordinary surface without an obvious selector or detail escape hatch."
            elif not reason_id and is_required:
                reason_id = "required_advisory_detail"
                reason = "Required advisory/diagnostic field may be necessary, but should be measured for ordinary-output byte share and actionability."

        if reason_id:
            key = (field_path, reason_id)
            if key not in seen:
                seen.add(key)
                findings.append(
                    _finding(
                        surface=surface,
                        schema_path=surface.schema_path,
                        field_path=field_path,
                        reason_id=reason_id,
                        reason=reason,
                        description=description,
                    )
                )

    findings.sort(key=lambda item: (item["surface"], item["field_path"], item["reason"]))
    return findings[:max_findings_per_surface]


def analyze_operations(operation_ids: tuple[str, ...] = ORDINARY_OPERATION_IDS, *, max_findings_per_surface: int = 12) -> dict[str, Any]:
    surfaces = [_surface_from_operation(operation_id) for operation_id in operation_ids]
    analyzed = [surface for surface in surfaces if surface.schema_path is not None]
    skipped = [
        {
            "surface": surface.operation_id,
            "command": surface.command,
            "operation": _repo_relative(surface.operation_path),
            "reason": surface.skipped_reason,
        }
        for surface in surfaces
        if surface.schema_path is None
    ]
    findings = [
        finding
        for surface in analyzed
        for finding in analyze_surface(surface, max_findings_per_surface=max_findings_per_surface)
    ]
    counts_by_cost_type = {cost_type: 0 for cost_type in COST_TYPES}
    for finding in findings:
        counts_by_cost_type[finding["suspected_cost_type"]] += 1
    counts_by_surface = {surface.operation_id: 0 for surface in analyzed}
    for finding in findings:
        counts_by_surface[finding["surface"]] += 1
    return {
        "kind": "agentic-workspace/completion-cost-schema-analysis/v1",
        "status": "findings-present" if findings else "no-findings",
        "ordinary_surface_count": len(surfaces),
        "analyzed_surface_count": len(analyzed),
        "skipped_surface_count": len(skipped),
        "finding_count": len(findings),
        "analyzed_surfaces": [
            {
                "surface": surface.operation_id,
                "command": surface.command,
                "operation": _repo_relative(surface.operation_path),
                "schema": _repo_relative(surface.schema_path) if surface.schema_path else "",
                "selector_available": surface.selector_available,
                "detail_available": surface.detail_available,
                "finding_count": counts_by_surface.get(surface.operation_id, 0),
            }
            for surface in analyzed
        ],
        "skipped_surfaces": skipped,
        "counts_by_cost_type": {key: value for key, value in counts_by_cost_type.items() if value},
        "findings": findings,
        "measurement_route": {
            "next_slice": "GitHub #1691 actual JSON completion-cost corpus",
            "lane": "GitHub #1680",
            "rule": "Static findings are suspects for measurement and evaluation correlation; they are not deletion proof.",
        },
        "ordinary_loop_surface": False,
    }


def _format_text(payload: dict[str, Any]) -> str:
    lines = [
        f"completion-cost schema analysis: {payload['status']}",
        f"analyzed surfaces: {payload['analyzed_surface_count']} / {payload['ordinary_surface_count']}",
        f"findings: {payload['finding_count']}",
    ]
    for finding in payload["findings"][:10]:
        lines.append(
            f"- {finding['surface']} {finding['field_path']}: {finding['suspected_cost_type']} ({finding['owner_surface']})"
        )
    if payload["skipped_surfaces"]:
        skipped = ", ".join(item["surface"] for item in payload["skipped_surfaces"])
        lines.append(f"skipped without schema refs: {skipped}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze ordinary AW output schemas for static completion-cost suspects.")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument("--max-findings-per-surface", type=int, default=12)
    parser.add_argument(
        "--min-analyzed-surfaces",
        type=int,
        default=3,
        help="Fail only when fewer ordinary surfaces with schema refs are available.",
    )
    args = parser.parse_args(argv)

    payload = analyze_operations(max_findings_per_surface=args.max_findings_per_surface)
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_format_text(payload))
    if payload["analyzed_surface_count"] < args.min_analyzed_surfaces:
        print(
            f"expected at least {args.min_analyzed_surfaces} analyzed ordinary surfaces, got {payload['analyzed_surface_count']}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
