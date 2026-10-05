"""The existing installed smoke must finish ordinary work, not only launch AW."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from tests.test_native_public_cli import native_cli as native_cli

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/tooling/release"))
import pytest
from consumer_journeys import INDEPENDENT_NOTES, Workspace, check_removed, check_stale_rejection, clean_context_snapshot  # noqa: E402
from first_contact import journey  # noqa: E402


def prepared_affordance(target, native_cli, task=None):
    import consumer_journeys as journeys
    from tests.test_native_planning_create import material

    root = Path(target)
    root.mkdir(parents=True, exist_ok=True)
    for name, data in journeys.INITIAL.items():
        if not (root / name).exists():
            (root / name).write_bytes(data)
    context = {"target": str(root), "task": task or journeys.AFFORDANCE_TASK, "changed": []}

    def call(extra=None, command="start"):
        result = subprocess.run(
            [str(native_cli), command, "--input", "-"],
            input=json.dumps(context | (extra or {})),
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(result.stdout)

    request = call({"projection": "full"})["planning"]["creation_requests"][0]
    intent = material()
    intent.update(title="Approved service migration", next_action="Read release.json; finish and retire scratch")
    request["arguments"] = {"material": intent}
    action = call({"request": request, "projection": "full"})["decision_packet"]["primary_action"]
    created = call({"invocation": action}, "invoke")
    assert created["effect_outcome"]["status"] == "committed"
    proposal = call({"request": {"operation": "scratch-create"}}, "resources")
    result = subprocess.run(
        [str(native_cli), "resources", "--input", "-"], input=json.dumps(proposal["action"]), text=True, capture_output=True, check=True
    )
    scratch = json.loads(result.stdout)
    assert scratch["effect_outcome"] == "committed"
    container = json.loads((Path(scratch["path"]) / ".aw-scratch.json").read_bytes())["path"]
    (root / container / "migration-draft.json").write_bytes(
        json.dumps(
            {
                "kind": "service-port-migration-draft/v1",
                "from_port": 8080,
                "target_port": None,
                "approval_source": "release.json",
                "files": ["settings.json", "README.md"],
                "note": "Wait for approval, then update both port examples and retire storage.",
            }
        ).encode()
    )
    current = call({"task": journeys.AFFORDANCE_TASK, "projection": "full"})
    files = Workspace(SimpleNamespace(repo=root, command=[str(native_cli)])).files()
    return files, container, current


@pytest.mark.parametrize(
    "mutation,gap",
    [
        ("missing", "draft-missing"),
        ("empty", "draft-empty"),
        ("misplaced", "draft-misplaced"),
        ("nested", "draft-misplaced"),
        ("invalid-json", "draft-invalid"),
        ("marker-as-draft", "draft-invalid"),
        ("wrong-port", "draft-invalid"),
        ("blank-note", "draft-invalid"),
        ("oversize", "draft-invalid"),
        ("foreign-custody", "managed-scratch-missing-or-invalid"),
        ("oversize-marker", "managed-scratch-missing-or-invalid"),
        ("no-plan", "retained-plan-missing-or-invalid"),
        ("fake-plan", "retained-plan-missing-or-invalid"),
        ("foreign-scratch-task", "managed-scratch-missing-or-invalid"),
        ("premature-port", "pending-source-or-preservation-changed"),
        ("lost-notes", "pending-source-or-preservation-changed"),
    ],
)
def test_preparation_requires_actual_draft_bytes(tmp_path, native_cli, mutation, gap):
    import consumer_journeys as journeys

    prepared, container, current = prepared_affordance(str(tmp_path), native_cli)
    name = container + "/migration-draft.json"
    if mutation == "missing":
        del prepared[name]
    elif mutation in {"misplaced", "nested"}:
        prepared[("migration-draft.json" if mutation == "misplaced" else container + "/nested/migration-draft.json")] = prepared.pop(name)
    elif mutation == "empty":
        prepared[name] = b" \n"
    elif mutation == "invalid-json":
        prepared[name] = b"\xffnot JSON"
    elif mutation == "marker-as-draft":
        prepared[name] = prepared[container + "/.aw-scratch.json"]
    elif mutation in {"wrong-port", "blank-note"}:
        draft = json.loads(prepared[name])
        draft.update({"target_port": 8081} if mutation == "wrong-port" else {"note": " "})
        prepared[name] = json.dumps(draft).encode()
    elif mutation == "oversize":
        prepared[name] += b" " * 16384
    elif mutation == "foreign-custody":
        marker = json.loads(prepared[container + "/.aw-scratch.json"])
        marker["target"] = str(tmp_path / "other")
        prepared[container + "/.aw-scratch.json"] = json.dumps(marker).encode()
    elif mutation == "oversize-marker":
        prepared[container + "/.aw-scratch.json"] += b" " * 16384
    elif mutation == "no-plan":
        del prepared[current["planning"]["selected_owner"]["ref"]]
    elif mutation == "fake-plan":
        prepared[current["planning"]["selected_owner"]["ref"]] = b'{"kind":"planning-execplan/v1","next_action":"anything"}'
    elif mutation == "foreign-scratch-task":
        marker = json.loads(prepared[container + "/.aw-scratch.json"])
        marker["task"] = "Unrelated bounded work"
        prepared[container + "/.aw-scratch.json"] = json.dumps(marker).encode()
    elif mutation == "premature-port":
        prepared["settings.json"] = b'{"port":8081}'
    elif mutation == "lost-notes":
        del prepared["notes.txt"]
    with pytest.raises(journeys.PreparationGap) as failure:
        journeys.check_affordance_preparation(journeys.INITIAL, prepared, str(tmp_path), current)
    assert failure.value.gap == gap


def test_preparation_rejects_unrelated_but_valid_scratch(tmp_path, native_cli):
    import consumer_journeys as journeys

    prepared, original, current = prepared_affordance(str(tmp_path), native_cli)
    context = {"target": str(tmp_path), "task": "Unrelated bounded work", "request": {"operation": "scratch-create"}}
    proposed = subprocess.run(
        [str(native_cli), "resources", "--input", "-"], input=json.dumps(context), text=True, capture_output=True, check=True
    )
    committed = subprocess.run(
        [str(native_cli), "resources", "--input", "-"],
        input=json.dumps(json.loads(proposed.stdout)["action"]),
        text=True,
        capture_output=True,
        check=True,
    )
    path = Path(json.loads(committed.stdout)["path"])
    marker = json.loads((path / ".aw-scratch.json").read_bytes())
    foreign = marker["path"]
    prepared[foreign + "/.aw-scratch.json"] = (path / ".aw-scratch.json").read_bytes()
    prepared[foreign + "/migration-draft.json"] = prepared.pop(original + "/migration-draft.json")
    # Both resources were really created. The current selected Plan is correct,
    # but the only draft belongs to the other task's genuine custody.
    with pytest.raises(journeys.PreparationGap) as failure:
        journeys.check_affordance_preparation(journeys.INITIAL, prepared, str(tmp_path), current)
    assert failure.value.gap == "managed-scratch-missing-or-invalid"


@pytest.mark.parametrize("preparation", ["no-draft", "valid", "unrelated-work"])
def test_affordance_phase_boundary_and_outer_cleanup(tmp_path, native_cli, monkeypatch, preparation):
    import consumer_agent
    import consumer_journeys as journeys
    import run_model_cli_harness as harness

    class Consumer:
        profile = "standalone"
        command = [str(native_cli)]
        repo = tmp_path / "consumer"
        observation = {"installed": True}
        cleanup = "not-started"

        def __init__(self, *args):
            self.repo.mkdir()

        def __enter__(self):
            return self

        def install(self):
            pass

        def exec(self, command):
            return subprocess.run(command, cwd=self.repo, text=True, capture_output=True, check=True)

        def __exit__(self, *args):
            # Exercise the actual outer driver's context cleanup on both paths.
            self.cleanup = "removed"

    class Actor:
        source_sha256 = "fixture"
        sessions_started = 0

        def __init__(self, **kwargs):
            self.observations = []

        def session(self, work, prompt):
            self.sessions_started += 1
            self.observations.append({"session": self.sessions_started})
            if self.sessions_started == 1:
                prepared, container, _ = prepared_affordance(
                    str(work.consumer.repo.resolve()), native_cli, "Unrelated bounded work" if preparation == "unrelated-work" else None
                )
                if preparation == "no-draft":
                    (work.consumer.repo / container / "migration-draft.json").unlink()
                return {"status": "complete", "message": "Draft complete"}
            assert work.files()["release.json"] == b'{"port":8081,"approved":true}\n'
            work.write("settings.json", b'{"port":8081,"host":"localhost"}\n')
            work.write("README.md", b"Connect using port 8081.\n")
            for name in list(work.files()):
                if "/local/scratch/" in name:
                    (work.consumer.repo / name).unlink()
            return {"status": "complete"}

    monkeypatch.setattr(consumer_agent, "SandboxConsumer", Consumer)
    monkeypatch.setattr(consumer_agent, "CodexActor", Actor)
    monkeypatch.setattr(journeys, "setup", lambda work: None)
    monkeypatch.setattr(journeys, "validate_pointer_files", lambda files: None)
    # This inert regression tests the byte/phase contract; it grants no model interaction evidence.
    monkeypatch.setattr(
        journeys,
        "affordance_observations",
        lambda *args: {
            "disposition": "observed",
            "coverage": {"fixture": True},
            "findings": [],
        },
    )
    output = tmp_path / "result.json"
    args = SimpleNamespace(
        family="operational-affordance",
        driver="agent",
        backend="sandbox",
        model="fixture",
        reasoning="medium",
        seconds=1,
        token_ceiling=None,
        billing="subscription",
        scratch=tmp_path,
        profile="standalone",
        target="fixture",
        template=None,
        sbx="fixture",
        result=output,
    )
    subject = SimpleNamespace(identity=lambda: {"fixture": True})
    code = harness.run_case(args, frozen_subject=subject)
    result = json.loads(output.read_text())
    assert result["cleanup"] == "removed"
    with_draft = preparation == "valid"
    assert result["sessions_started"] == (2 if with_draft else 1)
    assert (Consumer.repo / "release.json").exists() == with_draft
    for name in ("policy.md", "notes.txt"):
        assert (Consumer.repo / name).read_bytes() == journeys.INITIAL[name]
    if with_draft:
        assert code == 0 and result["status"] == "passed"
        assert result["preparation"]["draft"]["bytes"] > 0
        assert len(result["preparation"]["draft"]["sha256"]) == 64
    else:
        assert code == 1 and result["failure_class"] == "preparation-boundary"
        assert result["failure_phase"] == "preparation"
        assert result["preparation"]["gap"] == ("draft-missing" if preparation == "no-draft" else "retained-plan-missing-or-invalid")
        assert (Consumer.repo / "settings.json").read_bytes() == journeys.INITIAL["settings.json"]


def test_public_first_contact_finishes_task_and_preserves_repository(tmp_path, native_cli):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, capture_output=True)
    journey([str(native_cli)], tmp_path, dict(os.environ))
    assert '"port":8081' in (tmp_path / "settings.json").read_text()
    assert "8081" in (tmp_path / "README.md").read_text()
    assert (tmp_path / "notes.txt").read_text() == "Repository-owned note: keep this file.\n"
    assert (tmp_path / "AGENTS.md").read_text().startswith("Repository-owned instructions:")


def test_removal_cannot_pass_from_final_re_adopted_state():
    before = {**INDEPENDENT_NOTES, "policy.md": b"policy", "notes.txt": b"notes"}
    after = {**before, ".agentic-workspace/skills/workspace-startup/SKILL.md": b"still installed"}
    with pytest.raises(ValueError, match="package foothold"):
        check_removed(before, after)
    after.pop(".agentic-workspace/skills/workspace-startup/SKILL.md")
    check_removed(before, after)
    after["notes.txt"] = b"lost"
    with pytest.raises(ValueError, match="independently owned"):
        check_removed(before, after)


def test_stale_guard_crash_is_not_a_successful_rejection():
    class Broken:
        def files(self):
            return {"policy.md": b"unchanged"}

        def invoke(self, action):
            raise subprocess.CalledProcessError(1, ["missing"], output="")

    with pytest.raises(ValueError):
        check_stale_rejection(Broken(), {})


@pytest.mark.parametrize("name", ["../outside", "/absolute", "nested/../../outside", "..\\outside", "node_modules/tool", ".git/config"])
def test_continuation_rejects_unsafe_transfer_before_writing(name):
    class Consumer:
        def write_file(self, *args):
            pytest.fail("Unsafe snapshot transferred")

    with pytest.raises(ValueError, match="Unsafe continuation"):
        Workspace(Consumer()).restore({name: b"untrusted"})


def test_stalled_export_is_bounded_before_archive_header(monkeypatch):
    import tarfile

    import consumer_journeys

    class Consumer:
        name = "fixture"

        def archive_command(self):
            return [sys.executable, "-c", "import time; time.sleep(60)"]

    monkeypatch.setattr(consumer_journeys, "EXPORT_SECONDS", 0.1)
    started = time.monotonic()
    with pytest.raises((ValueError, tarfile.ReadError)):
        Workspace(Consumer()).files()
    assert time.monotonic() - started < 5


def test_export_failure_keeps_bounded_diagnostic_tail():
    class Consumer:
        name = "fixture"

        def archive_command(self):
            return [
                sys.executable,
                "-c",
                "import sys; sys.stderr.write('x'*65536+'EXPORT_CAUSE'); sys.stdout.buffer.write(bytes(10240)); sys.exit(2)",
            ]

    with pytest.raises(ValueError, match="EXPORT_CAUSE") as failure:
        Workspace(Consumer()).files()
    assert len(str(failure.value)) < 4200


@pytest.mark.parametrize("trailer", ["bytes(262144)", "b'x'*262144", "bytes(consumer_limit+65536)"])
def test_export_drains_only_bounded_tar_padding(monkeypatch, trailer):
    import consumer_journeys

    class Consumer:
        name = "fixture"

        def archive_command(self):
            return [
                sys.executable,
                "-c",
                f"import sys; consumer_limit=32768; sys.stdout.buffer.write(bytes(10240)+{trailer}); sys.stdout.buffer.flush()",
            ]

    monkeypatch.setattr(consumer_journeys, "EXPORT_SECONDS", 3)
    if trailer == "bytes(262144)":
        assert Workspace(Consumer()).files() == {}
    else:
        if trailer.startswith("bytes"):
            monkeypatch.setattr(consumer_journeys, "MAX_BYTES", 32768)
        with pytest.raises(ValueError, match="export padding"):
            Workspace(Consumer()).files()


def test_clean_context_preserves_selected_meaning_without_disposable_transport():
    plan = ".agentic-workspace/planning/execplans/maintenance.plan.json"
    selection = ".agentic-workspace/local/planning/owner-selection.json"
    before = {"AGENTS.md": b"source", "settings.json": b"8080", ".agentic-workspace/local/.gitignore": b"*"}
    receipt = ".agentic-workspace/local/effects/" + "a" * 64 + ".result.json"
    retained = {
        plan: json.dumps(
            {"next_action": "Create delayed client with retry 7", "creation_provenance": {"custody": {"committed": {"path": receipt}}}}
        ).encode()
    }
    disposable = {
        ".agentic-workspace/local/scratch/task/carrier.json": b'{"kind":"agentic-workspace/operating-carriage/v1"}',
        "arbitrary-name.json": b'{"carriage":{"kind":"agentic-workspace/operating-carriage/v1"}}',
        "delivery.json": b'{"available_sources":["policy.md"]}',
        "helper.py": b"prior transport script",
        ".agentic-workspace/local/planning/request.json": b"prior request",
        ".agentic-workspace/local/effects/" + "b" * 64 + ".result.json": b"unrelated receipt",
    }
    intact = {
        **before,
        **retained,
        **disposable,
        "settings.json": b"8081",
        selection: json.dumps({"selected_owner": {"ref": plan}}).encode(),
        receipt: b'{"status":"committed"}',
    }
    transferred = clean_context_snapshot(before, intact, retained)
    assert transferred == {**before, "settings.json": b"8081", **retained, selection: intact[selection], receipt: intact[receipt]}
    assert not set(disposable) & transferred.keys()


def test_clean_context_keeps_native_selected_owner_resolvable(tmp_path, native_cli):
    from tests.test_native_planning_create import material

    context = {"target": str(tmp_path), "task": "Prepare the gated rollout", "changed": [], "material": [], "projection": "full"}

    def call(extra=None, command="start"):
        result = subprocess.run(
            [str(native_cli), command, "--input", "-"],
            input=json.dumps({**context, **(extra or {})}),
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(result.stdout)

    request = call()["planning"]["creation_requests"][0]
    request["arguments"]["material"] = material()
    action = call({"request": request})["decision_packet"]["primary_action"]
    result = call({"invocation": action}, "invoke")
    created = result["value"]
    context.update(result["continuation"]["context"])
    plan = created["owner_path"]
    intact = {p.relative_to(tmp_path).as_posix(): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    clean = clean_context_snapshot({}, intact, {plan: intact[plan]})
    assert any(name.startswith(".agentic-workspace/local/effects/") for name in clean)
    for name in intact.keys() - clean.keys():
        (tmp_path / name).unlink()
    current = call({"task": "Finish the approved rollout"})
    assert current["planning"]["incumbent_owner"] is None
    relation = current["planning"]["selection_requests"][0]
    resumed = call({"task": "Finish the approved rollout", "request": relation})
    assert resumed["planning"]["selected_owner"]["ref"] == plan
