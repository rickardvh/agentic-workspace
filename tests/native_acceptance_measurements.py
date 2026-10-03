"""Finite repository acceptance producers; stdout is native measurement evidence.

Build and fixture preparation are outside the timed cold native processes. Each
selected read is validated against its exact Planning owner; unselected retained
closeout history is the control. No timing, threshold or passing result is stored.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import tempfile
import tomllib
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = 7
METHOD = {"unit": "seconds", "environment": "maintained-local-cold-native-process", "source_revision": "native-acceptance-measurements-v2"}
SUBJECT = "planning-owner-exact-detail-closeout-history-1000"
SUBJECT_REVISION = "tests/native_acceptance_measurements.py@selected-planning-v2"
METHODS = {
    "selected_planning_read_budget": {
        **METHOD,
        "metric": "selected-planning-read-latency",
        "comparator": "lte",
        "aggregation": "median",
        "subject": SUBJECT,
        "subject_revision": SUBJECT_REVISION,
        "evidence_label": "selected_planning_read_cold_median",
    },
    "selected_planning_scaling_budget": {
        **METHOD,
        "metric": "selected-planning-read-latency",
        "comparator": "ratio-lte",
        "aggregation": "ratio",
        "subject": SUBJECT,
        "subject_revision": SUBJECT_REVISION,
        "evidence_label": "selected_planning_read_history_ratio",
        "control_subject": "planning-owner-exact-detail-closeout-history-empty",
        "control_revision": SUBJECT_REVISION,
    },
    "invalid_selector_rejection_budget": {
        **METHOD,
        "metric": "invalid-selector-rejection-latency",
        "comparator": "lte",
        "aggregation": "median",
        "subject": "start-invalid-operating-detail-reference",
        "subject_revision": "tests/native_acceptance_measurements.py@invalid-reference-v2",
        "evidence_label": "invalid_selector_cold_median",
    },
}


def invoke(binary: Path, context: dict, verb: str = "start") -> tuple[subprocess.CompletedProcess, float]:
    began = perf_counter()
    result = subprocess.run([str(binary), verb, "--input", "-"], input=json.dumps(context).encode(), capture_output=True)
    return result, perf_counter() - began


def successful(binary: Path, context: dict, verb: str = "start") -> dict:
    result, _ = invoke(binary, context, verb)
    if result.returncode:
        raise RuntimeError(result.stderr.decode())
    return json.loads(result.stdout)


def planning_fixture(binary: Path, root: Path) -> tuple[dict, str]:
    original = json.loads((ROOT / "tests/fixtures/native_planning/delegation-lane-sweep.plan.json").read_bytes())
    fields = (
        "title",
        "owner_level",
        "intent",
        "parent",
        "scope",
        "relationships",
        "next_action",
        "proof",
        "continuation",
        "canonical_core",
        "references",
        "blockers",
    )
    material = {key: original[key] for key in fields}
    material["relationships"] = {"dependencies": {"refs": []}}
    material["material_lifetimes"] = {"next_action": "durable", "external_posture": "observation", "continuation_frontier": "durable"}
    context = {"target": str(root), "task": "Inspect the selected Planning owner", "changed": [], "projection": "full"}
    request = successful(binary, context)["planning"]["creation_requests"][0]
    request["arguments"] = {"material": material}
    ready = successful(binary, {**context, "request": request})
    created = successful(binary, {**context, "invocation": ready["decision_packet"]["primary_action"]}, "invoke")["value"]
    context = {**created["selection_context"], "projection": "full"}
    selected = successful(binary, {**context, "request": created["selection_request"]})
    successful(binary, {**context, "invocation": selected["decision_packet"]["primary_action"]}, "invoke")
    compact = successful(binary, {**context, "projection": "compact"})
    return {**context, "reference": compact["detail_refs"]["/planning"]}, created["owner_id"]


def selected_read(binary: Path, context: dict, owner: str) -> float:
    result, elapsed = invoke(binary, context)
    if result.returncode:
        raise RuntimeError(result.stderr.decode())
    detail = json.loads(result.stdout)
    assert detail["selector"] == "/planning" and detail["currentness"] == "reobserved"
    assert detail["value"]["selected_owner"]["id"] == owner
    assert detail["value"]["current_owner"]["current"] is True
    assert detail["value"]["terminal_retention"]["status"] == "quiet"
    return elapsed


def record(requirements: dict, name: str, samples: list[float], baseline: list[float] | None = None) -> dict:
    requirement = requirements[name]
    condition = requirement["measurement"]
    method = METHODS[name]
    if any(condition.get(key) != value for key, value in method.items()):
        raise ValueError(f"{name}: declared identity differs from this producer's measured operation")
    measurement = {key: value for key, value in method.items() if key != "evidence_label"}
    measurement["threshold"] = condition["threshold"]
    observed = statistics.median(samples)
    evaluated = observed
    if baseline is not None:
        control = statistics.median(baseline)
        measurement.update(baseline_value=control, control_samples=baseline, control_sample_count=len(baseline))
        evaluated /= control
    passed = evaluated <= condition["threshold"] + condition.get("tolerance", 0)
    measurement.update(
        kind="agentic-workspace/measurement-evidence/v1",
        status="passed" if passed else "failed",
        observed_value=observed,
        sample_count=len(samples),
        requirement_revision=requirement["source_intent_revision"],
        detail_ref="native-proof-command-artifact",
        samples=samples,
    )
    return {"requirement_id": name, "evidence_label": method["evidence_label"], "measurement": measurement}


def produce(binary: Path, root: Path, mode: str) -> dict:
    requirements = tomllib.loads((ROOT / ".agentic-workspace/verification/manifest.toml").read_text())["assurance"]["requirements"]
    if mode == "selected-planning-read":
        empty_root, loaded_root = root / "empty", root / "history-1000"
        empty_root.mkdir()
        loaded_root.mkdir()
        baseline = []
        loaded = []
        # Equivalent native owners and work in two fixed targets. Prepare history
        # once, outside sampling; repeatedly rewriting it between timed calls
        # measures filesystem/antivirus contention instead of stable read cost.
        history = loaded_root / ".agentic-workspace/planning/closeout-evidence"
        history.mkdir(parents=True)
        (empty_root / ".agentic-workspace/planning/closeout-evidence").mkdir(parents=True)
        # This retained namespace was the original budget's historical input.
        # These records are unadmitted former evidence, never current authority.
        for number in range(1000):
            (history / f"closed-{number}.closeout.json").write_text(
                json.dumps({"kind": "planning-closeout-evidence/v1", "plan_id": f"closed-{number}", "claim_level": "slice"})
            )
        empty_context, empty_owner = planning_fixture(binary, empty_root)
        loaded_context, loaded_owner = planning_fixture(binary, loaded_root)
        # Exact references are already discovered. Validate prepared targets
        # before starting paired cold-process samples; setup grants no custody.
        successful(binary, empty_context)
        successful(binary, loaded_context)
        for index in range(SAMPLES):
            # Alternate order so warm filesystem state does not favour one side.
            if index % 2 == 0:
                baseline.append(selected_read(binary, empty_context, empty_owner))
            loaded.append(selected_read(binary, loaded_context, loaded_owner))
            if index % 2:
                baseline.append(selected_read(binary, empty_context, empty_owner))
        records = [
            record(requirements, "selected_planning_read_budget", loaded),
            record(requirements, "selected_planning_scaling_budget", loaded, baseline),
        ]
    else:
        # Unknown current operating references replace the retired upgrade route.
        # The actual public CLI must fail with its typed, bounded error and leave
        # this empty target unchanged on every cold process.
        context = {"target": str(root), "task": "Inspect an invalid operating reference", "reference": "detail:unknown:sha256:" + "0" * 64}
        samples = []
        for _ in range(SAMPLES):
            result, elapsed = invoke(binary, context)
            assert result.returncode == 2 and result.stdout == b"" and len(result.stderr) <= 512
            assert json.loads(result.stderr)["error"]["code"] == "invalid-source-decision"
            assert list(root.iterdir()) == []
            samples.append(elapsed)
        records = [record(requirements, "invalid_selector_rejection_budget", samples)]
    return {"kind": "agentic-workspace/assurance-evidence-records/v1", "records": records}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["selected-planning-read", "invalid-selector"])
    parser.add_argument("--native-cli", type=Path)
    args = parser.parse_args()
    binary = args.native_cli
    if binary is None:
        subprocess.run(["cargo", "build", "--locked", "--workspace", "--bins"], cwd=ROOT, stdout=subprocess.DEVNULL, check=True)
        binary = ROOT / "target/debug" / ("agentic-workspace.exe" if os.name == "nt" else "agentic-workspace")
    with tempfile.TemporaryDirectory(prefix="aw-acceptance-measurement-") as temporary:
        result = produce(binary.resolve(), Path(temporary).resolve(), args.mode)
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
