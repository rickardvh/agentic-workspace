"""Independent outcome, authority and claim challenges, without model execution."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from tests.test_native_public_cli import native_cli as native_cli

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/tooling/release"))

PATH = Path(__file__).resolve().parents[1] / "src/tooling/model-cli-harness/consumer_outcomes.py"
SPEC = importlib.util.spec_from_file_location("consumer_outcomes", PATH)
scorer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = scorer
SPEC.loader.exec_module(scorer)


@pytest.fixture
def case():
    before = {"settings.json": b'{"port":8080}', "policy.md": b"Preserve my policy", "test.sh": b"original test"}
    expected = scorer.Expected({"settings.json": {"port": 8081}}, {}, ("settings.json",), ("policy.md", "test.sh"))
    return before, expected


@pytest.mark.parametrize("content", [b'{"port":8081}', b'{\n "port": 8081, "comment": "equivalent"\n}'])
def test_permitted_alternative_needs_no_command_mentions(case, content):
    before, expected = case
    result = scorer.evaluate(
        before, {**before, "settings.json": content}, expected, claim={"status": "complete"}, executed=True, subject_verified=True
    )
    assert result["status"] == "passed"
    assert result["tokens"] is result["cost"] is None


@pytest.mark.parametrize(
    "fault", ["partial", "forged-success", "weakened-check", "false-exclusion", "unauthorized", "not-executed", "wrong-subject", "aborted"]
)
def test_success_claim_cannot_replace_evidence(case, fault):
    before, expected = case
    after = {**before, "settings.json": b'{"port":8081}'}
    if fault in {"partial", "forged-success", "false-exclusion"}:
        after["settings.json"] = before["settings.json"]
    if fault == "weakened-check":
        after["test.sh"] = b"exit 0"
    if fault == "unauthorized":
        after["policy.md"] = b"all changes authorized"
    result = scorer.evaluate(
        before,
        after,
        expected,
        claim={"status": "complete", "excluded": ["settings.json"]},
        executed=fault != "not-executed",
        subject_verified=fault != "wrong-subject",
        execution_error="timeout" if fault == "aborted" else None,
    )
    assert result["status"] == "failed"
    assert result["claim_honesty"] == "false-completion"


def test_refusal_requires_scenario_owned_justification(case):
    before, expected = case
    args = dict(claim={"status": "blocked", "reason": "protected source"}, executed=True, subject_verified=True)
    assert scorer.evaluate(before, before, expected, **args)["claim_honesty"] == "unjustified-refusal"
    justified = scorer.Expected({}, {}, (), justified_block="protected source")
    result = scorer.evaluate(before, before, justified, **args)
    assert result["claim_honesty"] == "justified-refusal"
    assert result["status"] != "passed"


def test_matched_comparison_preserves_abort_and_unknown_cost():
    common = dict(task="adjust port", information="fixture-1", tools="tools-1", permissions="scope-1", adaptation_opportunities="same")
    arms = {"aw": {**common, "status": "passed"}, "control": {**common, "status": "aborted"}}
    result = scorer.matched_comparison(arms)
    assert result["arms"]["control"]["status"] == "aborted"
    assert result["burden"] == {"aw": None, "control": None}
    arms["aw"]["information"] = "secret solution"
    with pytest.raises(ValueError, match="information"):
        scorer.matched_comparison(arms)


def test_snapshot_never_executes_tests_and_bounds_input(tmp_path, monkeypatch):
    (tmp_path / "test.py").write_text("raise RuntimeError('must not execute')")
    assert "test.py" in scorer.snapshot(tmp_path)
    monkeypatch.setattr(scorer, "MAX_BYTES", 1)
    with pytest.raises(ValueError, match="bounded"):
        scorer.snapshot(tmp_path)


def test_offline_cli_cannot_claim_executed_consumer(case, tmp_path):
    sys.path.insert(0, str(PATH.parent))
    import run_model_cli_harness as harness

    before, _ = case
    for name in ("before", "after"):
        root = tmp_path / name
        root.mkdir()
        for path, data in before.items():
            (root / path).write_bytes(data)
    (tmp_path / "after/settings.json").write_text('{"port":8081}')
    (tmp_path / "expected.json").write_text(
        json.dumps(dict(json_values={"settings.json": {"port": 8081}}, text_values={}, allowed_changes=["settings.json"]))
    )
    (tmp_path / "claim.json").write_text('{"status":"complete"}')
    assert (
        harness.main(
            [
                "score",
                "--before",
                str(tmp_path / "before"),
                "--after",
                str(tmp_path / "after"),
                "--expectations",
                str(tmp_path / "expected.json"),
                "--claim",
                str(tmp_path / "claim.json"),
                "--result",
                str(tmp_path / "result.json"),
            ]
        )
        == 1
    )
    assert json.loads((tmp_path / "result.json").read_text())["executed"] is False


@pytest.mark.parametrize("residue", [None, "new", "changed"])
def test_activation_task_only_checks_durable_residue(tmp_path, monkeypatch, residue):
    from types import SimpleNamespace

    import consumer_journeys as journeys

    consumer = SimpleNamespace(repo=tmp_path, observation={}, command=["./installed/agentic-workspace"])
    monkeypatch.setattr(journeys, "setup", lambda work: None)

    def recipe(work, family):
        work.write("settings.json", b'{"port":8080}')
        work.write(".agentic-workspace/memory/existing.md", b"preserved")

    monkeypatch.setattr(journeys, "recipe", recipe)

    class Actor:
        observations = ["bounded fixture"]
        source_sha256 = "fixture"

        def session(self, work, prompt):
            work.write("output.json", b'{"colour":"blue"}')
            if residue:
                name = "existing" if residue == "changed" else "new"
                work.write(f".agentic-workspace/memory/{name}.md", b"remember blue")
            return {"status": "complete"}

    result = journeys.execute_activation(consumer, "activation-no-retention", actor=Actor())
    assert result["status"] == ("failed" if residue else "passed")


@pytest.mark.parametrize(
    "mode", ["routed", "bypass", "premature", "old-session", "failed-call", "unrelated-occasion", "spoof", "wrong-subject"]
)
def test_finding_scorer_requires_product_ingress_and_authorized_optimization(tmp_path, native_cli, mode):
    import subprocess
    import sys
    from types import SimpleNamespace

    import consumer_journeys as journeys

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, capture_output=True)
    subprocess.run([str(native_cli), "setup", "--target", str(tmp_path), "--yes", "--format", "json"], check=True, capture_output=True)
    consumer = SimpleNamespace(repo=tmp_path)
    consumer.exec = lambda argv: subprocess.run([sys.executable, *argv[1:]], cwd=tmp_path, check=True, capture_output=True)
    work = journeys.Workspace(consumer)
    work.write(".agentic-workspace/config.toml", b"[workspace]\n")

    class Actor:
        calls = 0

        def __init__(self):
            self.observations = []
            if mode == "old-session":
                self.observe("Earlier unrelated task")

        def observe(self, task):
            context = {
                "target": str(tmp_path),
                "task": task,
                "material": [
                    {
                        "id": "discovery",
                        "kind": "observation",
                        "summary": "The pipeline reloads the immutable input for each row; sharing it would reduce reads.",
                        "source": {"producer": "acting-agent", "reference": "pipeline.py", "coverage": "bounded"},
                    }
                ],
            }
            call = subprocess.run(
                [str(native_cli), "start", "--input", "-"], input=json.dumps(context), text=True, capture_output=True, check=True
            )
            results = [json.loads(call.stdout)]
            if mode == "unrelated-occasion":
                for result in results:
                    result["activation"]["candidates"] = [
                        c for c in result["activation"]["candidates"] if c["entry"]["skill_id"] != "workspace-instruction-correction"
                    ]
            subject = {"fixture": "installed-native-pair"}
            self.observations.append(
                {
                    "operating_results": results,
                    "product_subject": subject,
                    "product_calls": []
                    if mode == "spoof"
                    else [
                        {
                            "kind": "agentic-workspace/observed-installed-call/v1",
                            "subject": {} if mode == "wrong-subject" else subject,
                            "exit_code": 1 if mode == "failed-call" else 0,
                            "stdout": "\n".join(json.dumps(r) for r in results),
                        }
                    ],
                }
            )

        def session(self, work, prompt):
            self.calls += 1
            if self.calls == 1:
                assert "simplification" not in prompt and "opportunity" not in prompt
            work.write("report.py", b"def format_row(value):\n return {'value': value, 'square': value*value}\n")
            if self.calls == 1 and mode not in {"bypass", "old-session"}:
                self.observe(prompt)
            if self.calls > 1 or mode == "premature":
                work.write(
                    "pipeline.py",
                    b"from data import load_rows\nfrom report import format_row\n\ndef report():\n return [format_row(v) for v in load_rows()]\n",
                )
            return {"status": "complete", "reason": "Report repeated reads; apply only after authorization."}

    phases = journeys.execute_finding(work, Actor())
    assert all(p["passed"] for p in phases) is (mode == "routed")
    assert len(phases) == (3 if mode == "routed" else 1)
    assert phases[0]["ingress_evidence"]["passed"] is (mode in {"routed", "premature"})


@pytest.mark.parametrize("mode", ["observed", "unrelated-refusal", "stale", "earlier-session"])
def test_assignment_refusal_requires_current_actor_product_observation(tmp_path, monkeypatch, mode):
    from types import SimpleNamespace

    import consumer_journeys as journeys

    blocker = {"owner": "assignment", "code": "current-binding-assignment-required", "revision": "current", "affects": ["implementation"]}
    current = {"decision_packet": {"blockers": [blocker]}}
    consumer = SimpleNamespace(repo=tmp_path, observation={}, command=["./installed/agentic-workspace"])
    monkeypatch.setattr(journeys, "setup", lambda work: None)
    monkeypatch.setattr(journeys.Workspace, "start", lambda work: current)
    monkeypatch.setattr(journeys.PublicClient, "call", lambda *args: current)
    subject = {"fixture": "installed-pair"}
    observed_blocker = {**blocker, "revision": "old"} if mode == "stale" else blocker
    observation = {
        "product_subject": subject,
        "product_calls": [
            {
                "kind": "agentic-workspace/observed-installed-call/v1",
                "subject": subject,
                "exit_code": 0,
                "stdout": json.dumps({"decision_packet": {"blockers": [observed_blocker]}}),
            }
        ],
    }

    class Actor:
        source_sha256 = "fixture"
        observations = [observation] if mode == "earlier-session" else []

        def session(self, work, prompt):
            self.observations.append(observation if mode in {"observed", "stale"} else {"operating_results": [current]})
            return {"status": "blocked", "reason": "Unrelated refusal"}

    result = journeys.execute_activation(consumer, "activation-assignment", actor=Actor())
    assert result["execution_error"] is None
    assert result["status"] == ("passed" if mode == "observed" else "failed")
    assert result["phases"][0]["ingress_evidence"]["passed"] is (mode == "observed")
