from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_AW = REPO_ROOT / "scripts" / "run_agentic_workspace.py"

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

ACTION_KEYWORDS = (
    "action",
    "allowed_next_action",
    "command",
    "commands",
    "next",
    "next_action",
    "proof_commands",
    "required_next_action",
    "run",
    "status",
)

SELECTOR_KEYWORDS = (
    "detail_command",
    "detail_commands",
    "selector",
    "selectors",
    "select_command",
    "verbose",
)

OWNER_BY_KEYWORD = (
    (("proof", "validation", "test"), "verification/proof-selection"),
    (("memory",), "memory routing"),
    (("planning", "plan", "lane", "execplan", "todo"), "planning"),
    (("handoff", "delegation", "delegate"), "planning handoff/delegation"),
    (("closeout", "closure", "claim", "residue", "intent"), "workspace closeout/intent"),
    (("compatibility", "cli", "install", "payload", "doctor", "start"), "workspace lifecycle/startup"),
    (("report", "diagnostic", "warning", "detail"), "workspace ordinary outputs"),
)

MEASUREMENT_BY_COST = {
    "output noise": "Compare byte share, empty/default ratio, repeated strings, and actionability density before and after reductions.",
    "reread/re-grounding": "Correlate repeated concepts and low actionability with rereads or fresh-session reorientation failures.",
    "proof/test cost": "Measure proof command volume and repeated proof/test fields before broad reruns.",
    "review/repair churn": "Measure repeated diagnostic text and warnings before review/repair loops.",
    "planning residue": "Measure planning/todo/execplan byte share and stale active-state fields.",
    "handoff friction": "Measure handoff/delegation field size and missing exact next-action fields.",
    "recovery friction": "Measure recovery/repair command count and diagnostic byte share.",
    "outside-AW provider/tool friction": "Record separately unless AW can route, cache, or summarize it safely.",
}

REDUCTION_BY_COST = {
    "output noise": "Move large low-action fields behind selectors, collapse repeated metadata, or shorten ordinary projections.",
    "reread/re-grounding": "Route repeated concepts to one owner surface with compact freshness and detail selectors.",
    "proof/test cost": "Expose proof status first and defer broad command detail until selected.",
    "review/repair churn": "Cluster repeated diagnostics and keep the actionable root cause first.",
    "planning residue": "Keep inactive lane residue in roadmap/promotion surfaces instead of active ordinary state.",
    "handoff friction": "Emit a compact handoff packet with exact next action, proof burden, and stop conditions.",
    "recovery friction": "Expose a short recovery ladder before verbose diagnostics.",
    "outside-AW provider/tool friction": "Keep outside-AW friction separate from AW-owned reduction candidates.",
}


@dataclass(frozen=True)
class CorpusCommand:
    sample_id: str
    description: str
    command: tuple[str, ...]
    owner_surface: str


DEFAULT_CORPUS = (
    CorpusCommand(
        sample_id="start-task-json",
        description="Startup routing output for a bounded #1691 task.",
        command=(sys.executable, str(RUN_AW), "start", "--task", "Build actual JSON completion-cost corpus for #1691", "--format", "json"),
        owner_surface="workspace lifecycle/startup",
    ),
    CorpusCommand(
        sample_id="summary-json",
        description="Compact Planning/workspace summary output.",
        command=(sys.executable, str(RUN_AW), "summary", "--target", ".", "--format", "json"),
        owner_surface="planning/reporting",
    ),
    CorpusCommand(
        sample_id="implement-static-checker-json",
        description="Implement-context output for a narrow changed checker path.",
        command=(
            sys.executable,
            str(RUN_AW),
            "implement",
            "--changed",
            "scripts/check/check_completion_cost_schema_analysis.py",
            "--task",
            "Probe ordinary implement JSON for #1691",
            "--format",
            "json",
        ),
        owner_surface="workspace implementation routing",
    ),
    CorpusCommand(
        sample_id="doctor-planning-json",
        description="Planning doctor lifecycle output.",
        command=(sys.executable, str(RUN_AW), "doctor", "--target", ".", "--modules", "planning", "--format", "json"),
        owner_surface="workspace lifecycle/startup",
    ),
)


def _json_bytes(value: Any) -> int:
    return len(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _repo_relative(path: Path) -> str:
    return os.path.relpath(path, REPO_ROOT).replace(os.sep, "/")


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _field_path(parts: tuple[str, ...]) -> str:
    return ".".join(parts).replace(".[]", "[]")


def _walk(value: Any, path: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], Any]]:
    entries = [(path, value)]
    if isinstance(value, dict):
        for key, child in value.items():
            entries.extend(_walk(child, (*path, str(key))))
    elif isinstance(value, list):
        for child in value:
            entries.extend(_walk(child, (*path, "[]")))
    return entries


def _is_empty_or_default(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {} or value is False


def _looks_like_prose(value: str) -> bool:
    if len(value) >= 80:
        return True
    return len(value) >= 30 and " " in value


def _is_actionable(path: str, value: Any) -> bool:
    lowered = path.lower()
    if any(keyword in lowered for keyword in ACTION_KEYWORDS):
        return True
    return isinstance(value, str) and ("agentic-workspace" in value or value.startswith(("uv ", "make ", "git ", "gh ")))


def _has_selector_signal(path: str, value: Any) -> bool:
    lowered = path.lower()
    if any(keyword in lowered for keyword in SELECTOR_KEYWORDS):
        return True
    return isinstance(value, str) and ("--select" in value or "--verbose" in value)


def _owner_surface(path: str, fallback: str) -> str:
    lowered = path.lower()
    for keywords, owner in OWNER_BY_KEYWORD:
        if any(keyword in lowered for keyword in keywords):
            return owner
    return fallback


def _cost_type(path: str, observation_type: str) -> str:
    lowered = path.lower()
    if "proof" in lowered or "validation" in lowered or "test" in lowered:
        return "proof/test cost"
    if "diagnostic" in lowered or "warning" in lowered or observation_type == "repeated-string":
        return "review/repair churn"
    if "planning" in lowered or "todo" in lowered or "execplan" in lowered or "residue" in lowered:
        return "planning residue"
    if "memory" in lowered or "intent" in lowered or "context" in lowered or observation_type == "duplicate-concept":
        return "reread/re-grounding"
    if "handoff" in lowered or "delegation" in lowered:
        return "handoff friction"
    return "output noise"


def _observation(
    *,
    sample_id: str,
    field_path: str,
    observation_type: str,
    reason: str,
    owner_fallback: str,
    byte_share: float,
    value: int | float | str,
) -> dict[str, Any]:
    cost_type = _cost_type(field_path, observation_type)
    return {
        "sample_id": sample_id,
        "field_path": field_path,
        "observation_type": observation_type,
        "suspected_cost_type": cost_type,
        "owner_surface": _owner_surface(field_path, owner_fallback),
        "reason": reason,
        "value": value,
        "byte_share": round(byte_share, 4),
        "candidate_measurement": MEASUREMENT_BY_COST[cost_type],
        "candidate_reduction": REDUCTION_BY_COST[cost_type],
    }


def analyze_payload(sample_id: str, payload: Any, *, owner_surface: str = "workspace ordinary outputs") -> dict[str, Any]:
    entries = _walk(payload)
    total_bytes = _json_bytes(payload)
    field_sizes: dict[str, int] = defaultdict(int)
    top_field_sizes: dict[str, int] = defaultdict(int)
    key_counts: Counter[str] = Counter()
    repeated_strings: Counter[str] = Counter()
    repeated_string_paths: dict[str, set[str]] = defaultdict(set)
    empty_count = 0
    prose_bytes = 0
    actionable_count = 0
    selector_count = 0
    field_count = 0

    for path_parts, value in entries:
        if not path_parts:
            continue
        path = _field_path(path_parts)
        field_count += 1
        size = _json_bytes(value)
        field_sizes[path] += size
        if len(path_parts) == 1:
            top_field_sizes[path_parts[0]] = size
        key_counts[path_parts[-1]] += 1
        if _is_empty_or_default(value):
            empty_count += 1
        if isinstance(value, str):
            if _looks_like_prose(value):
                prose_bytes += len(value.encode("utf-8"))
            if len(value) >= 12:
                repeated_strings[value] += 1
                repeated_string_paths[value].add(path)
        if _is_actionable(path, value):
            actionable_count += 1
        if _has_selector_signal(path, value):
            selector_count += 1

    top_fields = [
        {
            "field_path": path,
            "bytes": size,
            "byte_share": round(size / total_bytes, 4) if total_bytes else 0,
        }
        for path, size in sorted(field_sizes.items(), key=lambda item: item[1], reverse=True)[:12]
    ]
    top_level_fields = [
        {
            "field_path": path,
            "bytes": size,
            "byte_share": round(size / total_bytes, 4) if total_bytes else 0,
        }
        for path, size in sorted(top_field_sizes.items(), key=lambda item: item[1], reverse=True)[:8]
    ]
    repeated = [
        {
            "value_preview": value[:120],
            "count": count,
            "paths": sorted(repeated_string_paths[value])[:8],
            "bytes": len(value.encode("utf-8")) * count,
        }
        for value, count in repeated_strings.most_common()
        if count > 1
    ][:8]
    duplicate_concepts = [
        {"concept": key, "count": count}
        for key, count in key_counts.most_common()
        if key != "[]" and count >= 4
    ][:8]

    observations: list[dict[str, Any]] = []
    for item in top_level_fields[:4]:
        if item["byte_share"] >= 0.18 or item["bytes"] >= 1200:
            observations.append(
                _observation(
                    sample_id=sample_id,
                    field_path=item["field_path"],
                    observation_type="large-top-level-field",
                    reason="Top-level field has high byte share in actual ordinary JSON output.",
                    owner_fallback=owner_surface,
                    byte_share=item["byte_share"],
                    value=item["bytes"],
                )
            )
    empty_ratio = empty_count / field_count if field_count else 0
    if empty_ratio >= 0.2:
        observations.append(
            _observation(
                sample_id=sample_id,
                field_path="<whole-output>",
                observation_type="empty-default-ratio",
                reason="Actual output contains many empty/default fields that may be cheap to hide or omit.",
                owner_fallback=owner_surface,
                byte_share=0,
                value=round(empty_ratio, 4),
            )
        )
    if repeated:
        first = repeated[0]
        observations.append(
            _observation(
                sample_id=sample_id,
                field_path="; ".join(first["paths"][:3]),
                observation_type="repeated-string",
                reason="Repeated string values increase real output bytes and can force rereading duplicated guidance.",
                owner_fallback=owner_surface,
                byte_share=round(first["bytes"] / total_bytes, 4) if total_bytes else 0,
                value=first["count"],
            )
        )
    actionability_density = actionable_count / field_count if field_count else 0
    if actionability_density < 0.08 and total_bytes >= 1000:
        observations.append(
            _observation(
                sample_id=sample_id,
                field_path="<whole-output>",
                observation_type="low-actionability-density",
                reason="Few fields are direct next actions, commands, or statuses relative to total output size.",
                owner_fallback=owner_surface,
                byte_share=0,
                value=round(actionability_density, 4),
            )
        )
    prose_share = prose_bytes / total_bytes if total_bytes else 0
    if prose_share >= 0.25:
        observations.append(
            _observation(
                sample_id=sample_id,
                field_path="<whole-output>",
                observation_type="prose-byte-share",
                reason="Prose-like strings are a large share of actual output bytes.",
                owner_fallback=owner_surface,
                byte_share=round(prose_share, 4),
                value=prose_bytes,
            )
        )
    if duplicate_concepts:
        first_concept = duplicate_concepts[0]
        observations.append(
            _observation(
                sample_id=sample_id,
                field_path=first_concept["concept"],
                observation_type="duplicate-concept",
                reason="The same concept key appears in several locations and may be a reread or owner-routing cost.",
                owner_fallback=owner_surface,
                byte_share=0,
                value=first_concept["count"],
            )
        )

    observations.sort(key=lambda item: (item["suspected_cost_type"], -float(item["byte_share"]), item["field_path"]))
    return {
        "sample_id": sample_id,
        "status": "measured",
        "total_bytes": total_bytes,
        "field_count": field_count,
        "empty_default_field_count": empty_count,
        "empty_default_ratio": round(empty_ratio, 4),
        "prose_bytes": prose_bytes,
        "prose_byte_share": round(prose_share, 4),
        "structured_bytes": max(total_bytes - prose_bytes, 0),
        "actionable_field_count": actionable_count,
        "actionability_density": round(actionability_density, 4),
        "selector_signal_count": selector_count,
        "top_fields": top_fields,
        "top_level_fields": top_level_fields,
        "repeated_strings": repeated,
        "duplicate_concepts": duplicate_concepts,
        "observations": observations,
    }


def _extract_json(stdout: str) -> Any:
    stripped = stdout.strip()
    if not stripped:
        raise ValueError("command produced empty stdout")
    return json.loads(stripped)


def capture_live_sample(command: CorpusCommand, *, timeout_seconds: int = 45) -> dict[str, Any]:
    result = subprocess.run(
        command.command,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
    )
    sample: dict[str, Any] = {
        "sample_id": command.sample_id,
        "description": command.description,
        "command": [str(part) for part in command.command],
        "owner_surface": command.owner_surface,
        "exit_code": result.returncode,
    }
    if result.returncode != 0:
        sample.update(
            {
                "status": "capture-failed",
                "stderr_preview": result.stderr[:1000],
                "stdout_preview": result.stdout[:1000],
            }
        )
        return sample
    try:
        sample["payload"] = _extract_json(result.stdout)
        sample["status"] = "captured"
    except json.JSONDecodeError as exc:
        sample.update(
            {
                "status": "parse-failed",
                "error": str(exc),
                "stdout_preview": result.stdout[:1000],
            }
        )
    return sample


def _load_samples_from_dir(path: Path) -> list[dict[str, Any]]:
    samples = []
    for file_path in sorted(path.glob("*.json")):
        samples.append(
            {
                "sample_id": file_path.stem,
                "description": f"Fixture sample from {_repo_relative(file_path)}",
                "command": [],
                "owner_surface": "workspace ordinary outputs",
                "status": "captured",
                "payload": _load_json(file_path),
            }
        )
    return samples


def analyze_samples(samples: list[dict[str, Any]]) -> dict[str, Any]:
    analyzed_samples = []
    observations = []
    skipped_samples = []
    for sample in samples:
        if sample.get("status") != "captured" or "payload" not in sample:
            skipped_samples.append({key: sample.get(key) for key in ("sample_id", "status", "exit_code", "error", "stderr_preview")})
            continue
        analysis = analyze_payload(
            str(sample["sample_id"]),
            sample["payload"],
            owner_surface=str(sample.get("owner_surface") or "workspace ordinary outputs"),
        )
        analysis["description"] = sample.get("description", "")
        analysis["command"] = sample.get("command", [])
        analysis["owner_surface"] = sample.get("owner_surface", "workspace ordinary outputs")
        analyzed_samples.append(analysis)
        observations.extend(analysis["observations"])

    observations.sort(key=lambda item: (-float(item["byte_share"]), item["sample_id"], item["field_path"]))
    counts_by_cost_type = {cost_type: 0 for cost_type in COST_TYPES}
    for observation in observations:
        counts_by_cost_type[observation["suspected_cost_type"]] += 1
    return {
        "kind": "agentic-workspace/completion-cost-json-corpus/v1",
        "status": "observations-present" if observations else "no-observations",
        "ordinary_loop_surface": False,
        "measurement_route": {
            "lane": "GitHub #1680",
            "issue": "GitHub #1691",
            "rule": "Actual JSON observations rank likely completion-cost sources; reductions still need safety-preserving before/after proof.",
        },
        "sample_count": len(samples),
        "analyzed_sample_count": len(analyzed_samples),
        "skipped_sample_count": len(skipped_samples),
        "observation_count": len(observations),
        "counts_by_cost_type": {key: value for key, value in counts_by_cost_type.items() if value},
        "samples": analyzed_samples,
        "skipped_samples": skipped_samples,
        "ranked_observations": observations[:25],
    }


def capture_default_corpus(*, timeout_seconds: int = 45) -> list[dict[str, Any]]:
    return [capture_live_sample(command, timeout_seconds=timeout_seconds) for command in DEFAULT_CORPUS]


def _format_text(payload: dict[str, Any]) -> str:
    lines = [
        f"completion-cost JSON corpus: {payload['status']}",
        f"analyzed samples: {payload['analyzed_sample_count']} / {payload['sample_count']}",
        f"observations: {payload['observation_count']}",
    ]
    for observation in payload["ranked_observations"][:10]:
        lines.append(
            f"- {observation['sample_id']} {observation['field_path']}: {observation['suspected_cost_type']} "
            f"{observation['observation_type']} share={observation['byte_share']}"
        )
    if payload["skipped_samples"]:
        skipped = ", ".join(str(item["sample_id"]) for item in payload["skipped_samples"])
        lines.append(f"skipped samples: {skipped}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture and analyze actual ordinary AW JSON outputs for completion-cost ranking.")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument("--from-dir", type=Path, help="Analyze checked-in or generated JSON fixture files instead of live command output.")
    parser.add_argument("--timeout-seconds", type=int, default=45)
    parser.add_argument("--min-analyzed-samples", type=int, default=3)
    args = parser.parse_args(argv)

    samples = _load_samples_from_dir(args.from_dir) if args.from_dir else capture_default_corpus(timeout_seconds=args.timeout_seconds)
    payload = analyze_samples(samples)
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_format_text(payload))
    if payload["analyzed_sample_count"] < args.min_analyzed_samples:
        print(
            f"expected at least {args.min_analyzed_samples} analyzed samples, got {payload['analyzed_sample_count']}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
