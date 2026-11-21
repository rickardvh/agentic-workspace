"""Lazy construction is measured in Rust; this checks its public transport/currentness."""

import hashlib
import json
import subprocess
from time import perf_counter

import pytest
import yaml
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


def test_configuration_detail_defers_only_healthy_payload_observations(tmp_path, native_cli):
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    subprocess.run([str(native_cli), "setup", "--target", str(tmp_path), "--yes"], capture_output=True, check=True)
    workspace = tmp_path / ".agentic-workspace"
    (workspace / "config.toml").write_text(
        '[workspace]\ncli_invoke="aw-local"\n[payload]\ntarget_release="source-current"\npolicy="required-before-work"\n'
    )
    context = {"target": str(tmp_path), "task": "Inspect policy and installed payload"}

    def run(data, *, format="json", verb="start", check=True):
        result = subprocess.run(
            [str(native_cli), verb, "--input", "-", "--format", format],
            input=json.dumps(data),
            text=True,
            encoding="utf-8",
            capture_output=True,
        )
        if not check:
            assert result.returncode == 2 and not result.stdout
            return json.loads(result.stderr)["error"]["message"]
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout) if format == "json" else yaml.safe_load(result.stdout)

    def details(entry):
        return entry["detail_refs"]["/configuration/effective"], entry["detail_refs"]["/configuration"]

    entry = run(context)
    effective, inventory = details(entry)
    pristine = run(context | {"reference": effective})["value"]["payload"]
    assert pristine["status"] == "satisfied"
    assert pristine["observations"] == [] and pristine["unchanged_observation_count"] > 2
    assert pristine["inventory_reference"] == inventory

    changed = ".agentic-workspace/skills/workspace-change-design/references/dependencies.md"
    missing = ".agentic-workspace/skills/workspace-startup/references/constraints.md"
    healthy = ".agentic-workspace/skills/workspace-startup/references/evidence.md"
    changed_bytes = (tmp_path / changed).read_bytes() + b"\nLocal drift.\n"
    (tmp_path / changed).write_bytes(changed_bytes)
    (tmp_path / missing).unlink()
    entry = run(context | {"projection": "carried"})
    effective, inventory = details(entry["view"])
    carried = {"request": entry["carriage"]}
    full = run(carried | {"reference": inventory})
    focus = run(carried | {"reference": effective})
    assert focus["selector"] == "/configuration/effective"
    exact = full["value"]
    projected = focus["value"]
    assert projected["cli_invoke"] == "aw-local"
    assert {k: v for k, v in projected.items() if k != "payload"} == {k: v for k, v in exact.items() if k != "payload"}
    payload = projected["payload"]
    for field in ("policy", "current_policy", "status", "revision", "gaps", "blockers"):
        assert payload[field] == exact["payload"][field]
    assert payload["status"] == "unresolved" and payload["blockers"][0]["affects"] == ["task"]
    assert {gap["path"] for gap in payload["gaps"]} == {changed, missing}
    assert {r["path"]: r for r in payload["observations"]} == {
        changed: {"path": changed, "revision": "sha256:" + hashlib.sha256(changed_bytes).hexdigest()},
        missing: {"path": missing, "status": "missing"},
    }
    assert payload["unchanged_observation_count"] == len(exact["payload"]["observations"]) - 2
    assert run(context | {"reference": payload["inventory_reference"]}) == full

    def lookup(path):
        return carried | {"reference": effective, "payload_path": path}

    selected = run(lookup(healthy))
    assert selected["selector"] == "/configuration/payload/observation"
    assert selected["authority"] == "detail-only"
    assert selected["value"] == {
        "payload_revision": payload["revision"],
        "observation": {
            "path": healthy,
            "revision": "sha256:" + hashlib.sha256((tmp_path / healthy).read_bytes()).hexdigest(),
        },
    }
    assert run(lookup(healthy), format="yaml") == selected
    assert run(lookup(missing))["value"]["observation"] == {"path": missing, "status": "missing"}
    assert "absent from" in run(lookup("../outside"), check=False)
    assert "read-only start" in run(lookup(healthy) | {"reference": inventory}, check=False)
    assert "read-only start" in run(context | lookup(healthy) | {"answer": {}}, check=False)
    rejected = run(
        context | {"invocation": entry["carriage"], "reference": effective, "payload_path": healthy, "changed": []},
        verb="invoke",
    )
    assert rejected["effect_outcome"]["status"] == "rejected-before-effect"
    assert rejected["effects"] == []
    assert "read-only start" in rejected["error"]["message"]
    old_carriage = entry["carriage"].copy()
    old_carriage["envelopes"] = [r for r in old_carriage["envelopes"] if r["reference"] != effective]
    assert run({"request": old_carriage, "reference": inventory}) == full

    # Any payload source change invalidates the earlier observation, including a
    # change to a different file than the one the caller selects.
    (tmp_path / changed).write_bytes(changed_bytes + b"More drift.\n")
    assert "stale" in run(lookup(healthy), check=False)
    assert "stale" in run(context | {"reference": effective}, check=False)
    refreshed, _ = details(run(context))
    assert run(context | {"reference": refreshed, "payload_path": healthy})["value"]["observation"] == selected["value"]["observation"]


def test_frontier_expansion_detail_currentness_and_disposable_carriage(tmp_path, shared_core_binary, native_cli):
    context = {"target": str(tmp_path), "task": "Check current bounded work", "changed": ["a.txt"]}
    (tmp_path / "a.txt").write_text("subject")

    def query(**extra):
        return consume("json", shared_core_binary, native_cli, context | extra)

    def size(value):
        return len(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode())

    measurements = []
    empty = query(projection="carried")
    source = tmp_path / ".agentic-workspace/verification/manifest.toml"
    source.parent.mkdir(parents=True)
    old_ref = empty["view"]["detail_refs"]["/verification"]
    for count in (1, 128):
        source.write_text(
            'schema_version="agentic-workspace/verification-manifest/v1"\n[proof_routes]\n'
            '[protocols.test]\napplies_to_paths=["a.txt"]\ncommands=' + json.dumps([f"echo check-{index}" for index in range(count)]) + "\n"
        )
        began = perf_counter()
        full = query(projection="full")
        full_ms = (perf_counter() - began) * 1000
        began = perf_counter()
        carried = query(projection="carried")
        frontier_ms = (perf_counter() - began) * 1000
        compact = query(projection="compact")
        for field in ("status", "blockers", "claim_boundary", "primary_action", "decision_request"):
            assert compact["decision_packet"][field] == full["decision_packet"][field]
        assert compact["decision_packet"]["blockers"]
        assert all(
            row["envelope"]["kind"] == "agentic-workspace/lazy-owner-detail/v1"
            for row in carried["carriage"]["envelopes"]
            if row["selector"].count("/") == 1
        )
        assert "echo check-0" not in json.dumps(carried["carriage"])
        with pytest.raises(AssertionError, match="stale operating reference"):
            query(reference=old_ref)
        ref = compact["detail_refs"]["/verification"]
        detail = query(reference=ref)
        assert detail["value"] == full["verification"]
        # A new process and an unrelated file preserve the same dependent ref.
        (tmp_path / "unrelated.txt").write_text("unrelated")
        assert query(reference=ref)["value"] == detail["value"]
        carried_detail = consume(
            "json",
            shared_core_binary,
            native_cli,
            {"request": carried["carriage"], "reference": ref},
        )
        assert carried_detail == detail
        assert query(projection="compact") == compact  # loss requires no session recovery
        measurements.append(
            {
                "commands": count,
                "full_bytes": size(full),
                "compact_bytes": size(compact),
                "carriage_bytes": size(carried["carriage"]),
                "full_ms": round(full_ms, 1),
                "frontier_ms": round(frontier_ms, 1),
            }
        )
        old_ref = ref
    assert measurements[1]["carriage_bytes"] == measurements[0]["carriage_bytes"]
    assert measurements[1]["compact_bytes"] == measurements[0]["compact_bytes"]
    assert measurements[1]["full_bytes"] > measurements[0]["full_bytes"] + 50000
    print({"frontier_measurements": measurements, "empty_carriage_bytes": size(empty["carriage"])})
    assert not (tmp_path / ".agentic-workspace/local").exists()


def test_review_planning_discloses_path_only_requirements_before_editing(tmp_path, shared_core_binary, native_cli):
    context = {"target": str(tmp_path), "task": "Update the connection timeout"}

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {"projection": "compact", **extra})

    assert "review_planning" not in call(**context)
    manifest = tmp_path / ".agentic-workspace/verification/manifest.toml"
    manifest.parent.mkdir(parents=True)
    policy = (
        'schema_version="agentic-workspace/verification-manifest/v1"\n'
        '[assurance.requirements.timeout]\nlevel="high"\nforce="required-before-closeout"\n'
        'review_owner="independent-maintainer"\napplies_to_paths=["src/settings.py"]\n'
        '[assurance.requirements.tests]\nlevel="high"\nforce="required-before-closeout"\n'
        'required_evidence=["test-result"]\napplies_to_paths=["src/settings.py"]\n'
        '[assurance.requirements.legacy]\nlevel="high"\nforce="required-before-closeout"\n'
        'review_owner="independent-agent"\napplies_to_task_markers=["legacy semantic scope"]\n'
        'applies_to_paths=["src/legacy.py"]\n'
    )
    manifest.write_text(policy, encoding="utf-8")
    initial = call(**context, projection="carried")
    cue = initial["view"]["review_planning"]
    path = "/verification/review_planning"
    assert cue["reference"] == initial["view"]["detail_refs"][path]
    assert not any(r["code"].startswith("assurance:timeout:") for r in initial["view"]["decision_packet"]["blockers"])
    assert any(r["code"] == "assurance:legacy:unresolved" for r in initial["view"]["decision_packet"]["blockers"])

    ref = {"reference": cue["reference"]}
    detail = call(request=initial["carriage"], **ref)
    assert detail == call(**context, **ref)
    assert detail["authority"] == "detail-only"
    assert detail["selector"] == path
    (requirement,) = detail["value"]["requirements"]
    assert requirement["id"] == "timeout"
    assert requirement["status"] == "not-applicable"
    assert requirement["source_requirement"]["review_owner"] == "independent-maintainer"
    assert requirement["source_requirement"]["applies_to_paths"] == ["src/settings.py"]

    outside = call(**context, changed=["docs/setup.md"])
    assert not any(r["code"].startswith("assurance:timeout:") for r in outside["decision_packet"]["blockers"])
    changed = call(**context, changed=["src/settings.py"])
    restriction = next(r for r in changed["decision_packet"]["blockers"] if r["code"] == "assurance:timeout:applicable")
    assert "claim:claim-work-complete" in restriction["affects"]
    observed = call(**context, changed=["src/settings.py"], reference=changed["detail_refs"][path])
    assert observed["value"]["requirements"][0]["status"] == "applicable"
    assert observed["value"]["requirements"][0]["matched_paths"] == ["src/settings.py"]

    manifest.write_text(policy.replace("independent-maintainer", "release-maintainer"), encoding="utf-8")
    with pytest.raises(AssertionError, match="stale"):
        call(request=initial["carriage"], **ref)
    fresh = call(**context)
    selection = call(**context, reference=fresh["review_planning"]["reference"])
    assert selection["value"]["requirements"][0]["source_requirement"]["review_owner"] == "release-maintainer"
