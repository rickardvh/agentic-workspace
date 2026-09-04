from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from agentic_workspace.workspace import Workspace

MAX_ADAPTER_OUTPUT_BYTES = 1_000_000
MAX_EVIDENCE_ITEMS = 50
MAX_EVIDENCE_STRING = 4_096


class ProviderAdapter(Protocol):
    """Explicit boundary for optional live-provider evaluation."""

    def probe(self, provider: str) -> Mapping[str, object]: ...

    def execute(self, request: Mapping[str, object]) -> Mapping[str, object]: ...


class CommandAdapter:
    """JSON adapter invoked only when a maintainer supplies a command."""

    def __init__(self, command: Sequence[str], *, timeout_seconds: float = 120.0) -> None:
        if not command:
            raise ValueError("adapter command must not be empty")
        self._command = list(command)
        self._timeout_seconds = timeout_seconds

    def _call(self, request: Mapping[str, object]) -> Mapping[str, object]:
        completed = subprocess.run(
            self._command,
            input=json.dumps(request),
            capture_output=True,
            text=True,
            timeout=self._timeout_seconds,
            check=True,
        )
        if len(completed.stdout.encode("utf-8")) > MAX_ADAPTER_OUTPUT_BYTES:
            raise ValueError("provider adapter response exceeds evidence limit")
        response = json.loads(completed.stdout)
        if not isinstance(response, dict):
            raise ValueError("provider adapter response must be an object")
        return response

    def probe(self, provider: str) -> Mapping[str, object]:
        return self._call({"kind": "probe", "provider": provider})

    def execute(self, request: Mapping[str, object]) -> Mapping[str, object]:
        return self._call(request)


def _availability(provider: str | None, adapter: ProviderAdapter | None) -> dict[str, object]:
    if provider is None:
        return {
            "provider": None,
            "configured": False,
            "status": "unknown",
            "available": None,
            "provenance": "provider-not-configured",
        }
    if adapter is None:
        return {
            "provider": provider,
            "configured": True,
            "status": "unknown",
            "available": None,
            "provenance": "adapter-not-configured",
        }
    try:
        probe = dict(adapter.probe(provider))
    except Exception as error:
        return {
            "provider": provider,
            "configured": True,
            "status": "unavailable",
            "available": False,
            "provenance": "adapter-probe-error",
            "detail": type(error).__name__,
        }
    status = probe.get("status")
    if status not in {"available", "unavailable", "unknown"}:
        status = "unknown"
    return {
        "provider": provider,
        "configured": True,
        "status": status,
        "available": True if status == "available" else False if status == "unavailable" else None,
        "provenance": str(probe.get("provenance") or "adapter-probe")[:MAX_EVIDENCE_STRING],
    }


def _bounded(value: object, *, depth: int = 0) -> object:
    if depth >= 6:
        return "<depth-limit>"
    if isinstance(value, str):
        return value[:MAX_EVIDENCE_STRING]
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, Mapping):
        items = list(value.items())[:MAX_EVIDENCE_ITEMS]
        return {str(key)[:MAX_EVIDENCE_STRING]: _bounded(item, depth=depth + 1) for key, item in items}
    if isinstance(value, Sequence) and not isinstance(value, bytes):
        return [_bounded(item, depth=depth + 1) for item in value[:MAX_EVIDENCE_ITEMS]]
    return f"<{type(value).__name__}>"


def _bounded_count(value: object) -> int:
    return min(max(value, 0), 1_000) if isinstance(value, int) and not isinstance(value, bool) else 0


def _workspace_evidence(repository: Path, intent: Mapping[str, object]) -> dict[str, object]:
    workspace = Workspace(repository)
    decision = workspace.start(intent=intent)
    evidence: dict[str, object] = {
        "decision_status": decision["status"],
        "primary_action": decision.get("primary_action"),
    }
    if decision["status"] == "actionable":
        result = workspace.invoke(decision["primary_action"])
        evidence["operation_result"] = result.get("value")
        evidence["next_decision"] = result["next_decision"]
    return evidence


def _live_evidence(
    adapter: ProviderAdapter,
    *,
    provider: str,
    scenario: Mapping[str, object],
    condition: str,
    workspace_evidence: Mapping[str, object] | None,
) -> dict[str, object]:
    request: dict[str, object] = {
        "kind": "evaluation",
        "provider": provider,
        "scenario_id": scenario["id"],
        "condition": condition,
        "intent": scenario["intent"],
    }
    if workspace_evidence is not None:
        request["workspace_evidence"] = workspace_evidence
    started = time.perf_counter()
    try:
        response = dict(adapter.execute(request))
    except Exception as error:
        return {
            "condition": condition,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            "effective_provider_input": request,
            "tool_calls": [],
            "retries": 0,
            "repairs": 0,
            "correct": None,
            "authority_outcome": "unknown",
            "unknowns": [f"adapter-error:{type(error).__name__}"],
        }
    return {
        "condition": condition,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "effective_provider_input": _bounded(response.get("effective_provider_input", request)),
        "tool_calls": _bounded(response.get("tool_calls", [])),
        "retries": _bounded_count(response.get("retries", 0)),
        "repairs": _bounded_count(response.get("repairs", 0)),
        "correct": response.get("correct") if isinstance(response.get("correct"), bool) else None,
        "authority_outcome": str(response.get("authority_outcome", "unknown"))[:MAX_EVIDENCE_STRING],
        "unknowns": _bounded(response.get("unknowns", [])),
    }


def run(root: Path, provider: str | None, adapter: ProviderAdapter | None = None) -> dict[str, Any]:
    definition = json.loads((root / "tools/model-evaluation/scenarios.json").read_text(encoding="utf-8"))
    results: list[dict[str, object]] = []
    live_results: list[dict[str, object]] = []
    availability = _availability(provider, adapter)
    with tempfile.TemporaryDirectory(prefix="aw-model-evaluation-") as temporary:
        for scenario in definition["scenarios"]:
            repository = Path(temporary) / scenario["id"]
            repository.mkdir(parents=True)
            workspace_evidence = _workspace_evidence(repository, scenario["intent"])
            results.append(
                {
                    "id": scenario["id"],
                    "expected_status": scenario["expected_status"],
                    "observed_status": workspace_evidence["decision_status"],
                    "passed": workspace_evidence["decision_status"] == scenario["expected_status"],
                }
            )
            live = scenario.get("live") and availability["available"] is True
            if live and provider is not None and adapter is not None:
                live_results.append(
                    {
                        "id": scenario["id"],
                        "direct": _live_evidence(
                            adapter,
                            provider=provider,
                            scenario=scenario,
                            condition="direct",
                            workspace_evidence=None,
                        ),
                        "assisted": _live_evidence(
                            adapter,
                            provider=provider,
                            scenario=scenario,
                            condition="assisted",
                            workspace_evidence=workspace_evidence,
                        ),
                    }
                )
    return {
        "kind": "agentic-workspace/model-evaluation/v1",
        "provider_availability": availability,
        "results": results,
        "live_results": live_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--provider")
    parser.add_argument("--adapter-command", nargs="+")
    args = parser.parse_args()
    adapter = CommandAdapter(args.adapter_command) if args.adapter_command else None
    report = run(args.root.resolve(), args.provider, adapter)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all(item["passed"] for item in report["results"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
