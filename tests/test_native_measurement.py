"""Only current selected native producer output can satisfy a measurement."""

from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path

from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


def test_measurement_output_admission_and_remaining_review(tmp_path: Path, shared_core_binary: Path, native_cli: Path) -> None:
    source = tmp_path / ".agentic-workspace/verification/manifest.toml"
    source.parent.mkdir(parents=True)
    producer = tmp_path / "measure.py"
    command = ("& '" + sys.executable.replace("'", "''") + "'" if os.name == "nt" else shlex.quote(sys.executable)) + " measure.py"
    source.write_text(
        'schema_version="agentic-workspace/verification-manifest/v1"\n[protocols]\n[proof_routes]\n'
        '[assurance.requirements.latency]\nlevel="high"\nforce="required-before-closeout"\n'
        'applies_to_paths=["measure.*"]\nrequired_evidence=["cold_median"]\nreview_owner="maintainer"\n'
        'blocking_claims=["claim-work-complete"]\nrequirement_class="current-evidence"\n'
        'source_intent_ref="policy.md"\nsource_intent_revision="policy-r1"\n'
        'evidence_owner="verification:latency"\ndetail_route="measurement:latency"\n'
        '[assurance.requirements.latency.measurement]\nkind="agentic-workspace/measurement-requirement/v1"\n'
        'evidence_label="cold_median"\nmetric="read-latency"\nunit="seconds"\ncomparator="lte"\n'
        'threshold=2.0\naggregation="median"\nminimum_samples=3\nsubject="fixture"\n'
        'subject_revision="fixture-r1"\nenvironment="maintained-test"\nsource_revision="method-r1"\n'
        f"producer_command={json.dumps(command)}\n"
    )
    measurement = {
        "kind": "agentic-workspace/measurement-evidence/v1",
        "metric": "read-latency",
        "unit": "seconds",
        "comparator": "lte",
        "threshold": 2.0,
        "aggregation": "median",
        "observed_value": 1.5,
        "sample_count": 5,
        "subject": "fixture",
        "subject_revision": "fixture-r1",
        "environment": "maintained-test",
        "source_revision": "method-r1",
        "requirement_revision": "policy-r1",
        "status": "passed",
        "detail_ref": "private-fixture",
    }
    context = {"target": str(tmp_path), "task": "Check current measurement", "changed": [producer.name]}

    def call(value):
        return consume("native", shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    def write(observation):
        raw = json.dumps(
            {
                "kind": "agentic-workspace/assurance-evidence-records/v1",
                "records": [{"requirement_id": "latency", "evidence_label": "cold_median", "measurement": observation}],
            }
        )
        # The positive fixture measures five real reads in the selected native
        # child; controlled negatives replace its compact result deliberately.
        code = "import json, statistics, time\nfrom pathlib import Path\n"
        code += f"result = json.loads({raw!r})\n"
        if observation == measurement:
            code += "samples=[]\nfor _ in range(5):\n    start=time.perf_counter()\n    Path(__file__).read_bytes()\n    samples.append(time.perf_counter()-start)\n"
            code += "result['records'][0]['measurement']['observed_value']=statistics.median(samples)\n"
        producer.write_text(code + "print(json.dumps(result))\n")

    def run(*, manual=False):
        current = call(context)["verification"]
        requests = current["record_requests" if manual else "execution_requests"]
        request = next(r for r in requests if r["arguments"]["route_id"] == "measurement:latency")
        if manual:
            request["arguments"]["result"] = "passed"
        action = call({**context, "request": request})["decision_packet"]["primary_action"]
        effect = call({**context, "invocation": action})["value"]
        assert effect["process"]["status"] == "passed"
        assert call({**context, "invocation": action})["value"] == effect
        return effect["publication"]["reference"]

    def claim(reference):
        request = call(context)["verification"]["requests"][0]
        request["arguments"]["evidence_refs"] = [reference]
        result = call({**context, "request": request})
        assert any(b["code"] == "assurance:latency:applicable" for b in result["decision_packet"]["blockers"])
        return result["verification"]

    write(measurement)
    direct = call({**context, "changed": []})["verification"]
    assert direct["execution_requests"] == [] and direct["assurance_owner_gaps"] == []
    assert not (tmp_path / ".agentic-workspace/local/proof-receipts").exists()
    assert claim(run(manual=True))["assurance_owner_gaps"][0]["measurement_admission"]["status"] == "measurement-not-admitted"
    reference = run()
    admitted = claim(reference)
    gap = admitted["assurance_owner_gaps"][0]
    assert gap["measurement_admission"]["status"] == "current-measurement-satisfied"
    assert gap["missing_admissions"] == ["required-reviewer-result-not-admitted", "source-intent-reconciliation-not-admitted"]
    assert "measurement_observations" not in admitted["evidence"][0]
    for field, value, expected in [
        ("observed_value", 2.5, "threshold-not-met"),
        ("sample_count", 1, "minimum-samples-not-met"),
        ("subject_revision", "old", "subject_revision-mismatch"),
        ("environment", "other", "environment-mismatch"),
        ("source_revision", "old", "source_revision-mismatch"),
        ("requirement_revision", "old", "requirement-revision-mismatch"),
    ]:
        write({**measurement, field: value})
        negative = claim(run())["assurance_owner_gaps"][0]["measurement_admission"]
        assert negative["gap"] == f"measurement-{expected}"
    producer.write_text("print('no-measurement')\n")
    assert claim(run())["assurance_owner_gaps"][0]["measurement_admission"]["status"] == "measurement-not-admitted"
    write(measurement)
    reference = run()
    source.write_text(source.read_text().replace("method-r1", "method-r2"))
    assert claim(reference)["assurance_owner_gaps"][0]["measurement_admission"]["status"] == "measurement-not-admitted"
