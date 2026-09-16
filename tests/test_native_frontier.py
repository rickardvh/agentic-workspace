"""Lazy construction is measured in Rust; this checks its public transport/currentness."""

import json
from time import perf_counter

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


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
