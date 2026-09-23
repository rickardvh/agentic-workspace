"""Shared initial recipes and installed composition checks, with two actor paths."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path, PurePosixPath

HARNESS = Path(__file__).resolve().parents[1] / "model-cli-harness"
sys.path.insert(0, str(HARNESS))
from consumer_outcomes import MAX_BYTES, MAX_FILES, Expected, evaluate, snapshot  # noqa: E402
from run_model_cli_harness import PublicClient  # noqa: E402

TASK = "Change the service port to 8081 in settings.json and update the README example. Preserve repository policy and existing notes."
INITIAL = {
    "AGENTS.md": b"Repository-owned instructions: preserve policy.md and notes.txt.\n",
    "README.md": b"# Sample service\n\nConnect using port 8080.\n",
    "settings.json": b'{"port":8080,"host":"localhost"}\n',
    "policy.md": b"Keep host localhost. Preserve notes and repository policy.\n",
    "notes.txt": b"Repository-owned note: keep this file.\n",
}
FAMILIES = {
    "first-contact": "Install/setup then complete an ordinary change",
    "local-independence": "Separate exact-version repositories and local invocation",
    "upgrade": "Refresh a previous stable customised integration",
    "maintenance": "Assessment and disabled-workspace maintenance",
    "interruption": "Changed-source rejection and fresh recovery",
    "readoption": "Remove/re-adopt while preserving independent state",
    "continuation": "Finish a multi-step task from repository state in a fresh process",
}
OWNER_EVIDENCE = {
    "maintenance": [
        "tests/test_configuration_procedure.py::test_setup_assessment_routes_integrates_and_reuses_current_sources",
        "tests/test_native_repository_adoption.py::test_human_setup_authorisation_preservation_and_recovery",
    ],
    "interruption": ["tests/test_native_repository_adoption.py::test_human_setup_authorisation_preservation_and_recovery"],
    "readoption": ["tests/test_native_repository_adoption.py"],
}


def expected_task():
    return Expected(
        {"settings.json": {"port": 8081, "host": "localhost"}},
        {"README.md": ("8081",), "AGENTS.md": ("Repository-owned instructions: preserve policy.md and notes.txt.",)},
        ("README.md", "settings.json", "AGENTS.md", ".agentic-workspace/*", ".agents/*", "CONTINUE.md"),
        ("policy.md", "notes.txt"),
    )


class Workspace:
    def __init__(self, consumer):
        self.consumer = consumer
        self.client = PublicClient(consumer)

    def write(self, name: str, data: bytes):
        if PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts:
            raise ValueError("Fixture path escapes consumer")
        if hasattr(self.consumer, "repo"):
            path = self.consumer.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        else:
            self.consumer.exec(
                ["sh", "-c", 'mkdir -p "$(dirname "$1")"; printf %s "$2" | base64 -d > "$1"', "sh", name, base64.b64encode(data).decode()]
            )

    def remove(self, name: str):
        if name not in {".agentic-workspace/local/.gitignore"}:
            raise ValueError("Only the named recipe interruption surface may be removed")
        if hasattr(self.consumer, "repo"):
            (self.consumer.repo / name).unlink()
        else:
            self.consumer.exec(["rm", "--", name])

    def files(self):
        if hasattr(self.consumer, "repo"):
            return snapshot(self.consumer.repo)
        # Trusted container tar reads bytes only. No exported program is executed.
        command = [
            "docker",
            "exec",
            self.consumer.name,
            "tar",
            "-C",
            "/home/consumer/repo",
            "--exclude=./.git",
            "--exclude=./node_modules",
            "--exclude=./.venv",
            "--exclude=./.agents",
            "-cf",
            "-",
            ".",
        ]
        if hasattr(self.consumer, "archive_command"):
            command = self.consumer.archive_command()
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        files = {}
        size = 0
        try:
            with tarfile.open(fileobj=proc.stdout, mode="r|") as archive:
                for index, member in enumerate(archive):
                    name = PurePosixPath(member.name)
                    size += member.size
                    if (
                        index > MAX_FILES
                        or size > MAX_BYTES
                        or name.is_absolute()
                        or ".." in name.parts
                        or not (member.isfile() or member.isdir())
                    ):
                        raise ValueError("Unsafe or oversized exported file set")
                    if member.isfile():
                        files[str(name)] = archive.extractfile(member).read()
            if proc.wait(timeout=30):
                raise ValueError("Consumer export failed")
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
        return files

    def start(self, request=None):
        arguments = ["--task", TASK, "--projection", "full"]
        if request is not None:
            # Request data remains outside task files in both drivers.
            if hasattr(self.consumer, "repo"):
                path = self.consumer.root / "request.json"
                path.write_text(json.dumps(request), encoding="utf-8")
                arguments += ["--input", str(path)]
            else:
                data = base64.b64encode(json.dumps(request).encode()).decode()
                self.consumer.exec(["sh", "-c", 'printf %s "$1" | base64 -d > ../request.json', "sh", data])
                arguments += ["--input", "../request.json"]
        return self.client.call("start", *arguments)

    def invoke(self, action):
        if hasattr(self.consumer, "repo"):
            path = self.consumer.root / "action.json"
            path.write_text(json.dumps(action), encoding="utf-8")
            return self.client.call("invoke", "--task", TASK, "--input", str(path))
        data = base64.b64encode(json.dumps(action).encode()).decode()
        self.consumer.exec(["sh", "-c", 'printf %s "$1" | base64 -d > ../action.json', "sh", data])
        return self.client.call("invoke", "--task", TASK, "--input", "../action.json")


def recipe(work: Workspace, family: str):
    if family not in FAMILIES:
        raise ValueError("Unknown consumer family")
    for name, data in INITIAL.items():
        work.write(name, data)
    if family == "continuation":
        # Intentional retained state, not earlier chat or an evaluator answer.
        work.write(
            "CONTINUE.md",
            b"The port change is unfinished. Read settings.json, README.md and policy.md, then finish the requested change.\n",
        )
    return work.files()


def validate_pointer_files(files):
    agents = files["AGENTS.md"].decode()
    begin, end = "<!-- agentic-workspace:workflow:start -->", "<!-- agentic-workspace:workflow:end -->"
    if agents.count(begin) != 1 or agents.count(end) != 1:
        raise ValueError("Missing or ambiguous installed startup fence")
    skill = ".agentic-workspace/skills/workspace-startup/SKILL.md"
    adoption = json.loads(files[".agentic-workspace/adoption.json"])
    provenance = json.loads(files[".agentic-workspace/payload-provenance.json"])
    if (
        skill not in agents.split(begin)[1].split(end)[0]
        or skill not in provenance["payload_files"]
        or adoption["package_files"].get(skill) != "sha256:" + hashlib.sha256(files[skill]).hexdigest()
        or adoption["instruction_fence"] not in agents
    ):
        raise ValueError("Installed startup identity mismatch")


def setup(work):
    before = work.files()
    proposal = work.client.call("setup", "--dry-run")
    if proposal["status"] != "authorization-required" or work.files() != before:
        raise ValueError("Setup proposal mutated the consumer or omitted authorization")
    result = work.client.call("setup", "--yes")
    if result["effect_outcome"]["status"] != "committed":
        raise ValueError("Setup did not commit")
    validate_pointer_files(work.files())
    if work.client.call("setup")["status"] != "already-current":
        raise ValueError("Setup did not converge")
    return result


def ordinary_change(work):
    current = work.start()
    if not current.get("semantic_routes"):
        raise ValueError("Installed ordinary entry cannot discover its procedures")
    work.write("settings.json", b'{"port":8081,"host":"localhost"}\n')
    work.write("README.md", b"# Sample service\n\nConnect using port 8081.\n")


def adoption_action(work, mode):
    current = work.start()
    read = work.start(current["configuration_write"]["repository_adoption_request"])["configuration_write"]
    request = next(request for request in read["adoption_requests"] if request["arguments"]["mode"] == mode)
    proposal = work.start(request)
    answer = next(
        row["response_request"]
        for row in proposal["decision_packet"]["pending_consequences"]["decisions"]
        if row["id"] == "repository-adoption-authorization"
    )
    answer["arguments"]["answer"] = "authorize-write"
    return work.start(answer)["decision_packet"]["primary_action"]


def deterministic(work, family):
    setup(work)
    if family == "maintenance":
        current = work.start()
        assessment = work.start(current["configuration_write"]["setup_assessment"]["request"])["configuration_write"]["setup_assessment"]
        concerns = {row["concern"]: row["settlement"] for row in assessment.get("concerns", [])}
        if set(concerns) != {"instructions", "preferences", "diagnostics", "assignment", "modules", "invocation"}:
            raise ValueError("Setup assessment lacks the current six-concern contract (#3598)")
        ordinary_change(work)
        disabled = b"[workspace]\nenabled = false\n"
        work.write(".agentic-workspace/config.toml", disabled)
        work.remove(".agentic-workspace/local/.gitignore")
        result = work.client.call("setup", "--yes")
        if result["effect_outcome"]["status"] != "committed" or work.files()[".agentic-workspace/config.toml"] != disabled:
            raise ValueError("Disabled maintenance failed or changed policy (#3599)")
        if not any(row["code"] == "workspace-disabled" for row in work.start()["decision_packet"]["blockers"]):
            raise ValueError("Disabled maintenance enabled ordinary work (#3599)")
    elif family == "interruption":
        # Capture an actual owner proposal, then change its source before replay.
        action = adoption_action(work, "remove")
        original = work.files()["AGENTS.md"]
        work.write("AGENTS.md", original + b"\nConcurrent repository-owned instruction.\n")
        before = work.files()
        try:
            result = work.invoke(action)
        except subprocess.CalledProcessError:
            result = {"effect_outcome": {"status": "rejected-before-effect"}}
        if result.get("effect_outcome", {}).get("status") != "rejected-before-effect" or work.files() != before:
            raise ValueError("Changed-source action was not rejected without effects")
        # Fresh public entry, no blind retry of the stale action.
        ordinary_change(work)
    elif family == "readoption":
        work.write(".agentic-workspace/local/host-note.txt", b"independent local note\n")
        work.write(".agentic-workspace/memory/consumer-note.md", b"independent Memory note\n")
        work.write(".agentic-workspace/planning/consumer-note.md", b"independent Planning note\n")
        before = work.files()
        result = work.invoke(adoption_action(work, "remove"))
        removed = work.files()
        if result["effect_outcome"]["status"] != "committed" or ".agentic-workspace/skills/workspace-startup/SKILL.md" in removed:
            raise ValueError("Removal did not remove the package foothold")
        for name in (
            ".agentic-workspace/local/host-note.txt",
            ".agentic-workspace/memory/consumer-note.md",
            ".agentic-workspace/planning/consumer-note.md",
        ):
            if removed.get(name) != before[name]:
                raise ValueError("Removal lost independently owned data")
        setup(work)
        ordinary_change(work)
    elif family == "first-contact":
        ordinary_change(work)
    elif family == "continuation":
        work.start()
        work.write("settings.json", b'{"port":8081,"host":"localhost"}\n')
        work.write("CONTINUE.md", b"settings.json is updated. Finish the README example and check policy preservation.\n")
        # Only repository state crosses this process boundary.
        fresh = Workspace(work.consumer)
        if not fresh.start().get("semantic_routes"):
            raise ValueError("Fresh process could not reenter")
        fresh.write("README.md", b"# Sample service\n\nConnect using port 8081.\n")
    else:
        raise ValueError("This family requires an explicit previous published subject")


def execute(consumer, family, *, actor=None):
    started = time.monotonic()
    recipe_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    scorer_sha256 = hashlib.sha256((HARNESS / "consumer_outcomes.py").read_bytes()).hexdigest()
    work = Workspace(consumer)
    before = recipe(work, family)
    error = None
    claim = None
    exported = None
    try:
        if actor:
            claim = actor(work, family, TASK)
            if isinstance(claim, dict) and "exported" in claim:
                exported, claim = claim["exported"], claim["claim"]
        else:
            deterministic(work, family)
            claim = {"status": "complete"}
        after = exported if exported is not None else work.files()
        validate_pointer_files(after)
        if family == "maintenance":
            import tomllib

            config = tomllib.loads(after[".agentic-workspace/config.toml"].decode())
            if config.get("workspace", {}).get("enabled") is not False:
                raise ValueError("Maintenance outcome did not preserve requested disablement")
    except (Exception, KeyboardInterrupt) as failure:
        error = str(failure)[:2000]
    result = evaluate(
        before,
        exported if exported is not None else work.files(),
        expected_task(),
        claim=claim,
        executed=bool(actor.observations) if actor else True,
        subject_verified=bool(consumer.observation.get("installed")),
        execution_error=error,
    )
    result.update(
        family=family,
        driver="agent" if actor else "deterministic",
        elapsed_seconds=round(time.monotonic() - started, 3),
        environment=consumer.observation,
        recipe_sha256=recipe_sha256,
        scorer_sha256=scorer_sha256,
        reused_owner_evidence=OWNER_EVIDENCE.get(family, []),
    )
    if actor:
        result["actor_sha256"] = actor.source_sha256
        result["actor"] = actor.observations
        result["tokens"] = (
            sum(row["tokens"] for row in actor.observations)
            if actor.observations and all(row["tokens"] is not None for row in actor.observations)
            else None
        )
    return result


def execute_pair(current_factory, previous_factory, family, destination):
    """Exact previously published version, never a reserved tag or synthetic pin."""
    if family not in {"local-independence", "upgrade"}:
        raise ValueError("Not a paired-subject family")
    results = {"family": family, "status": "assigned", "executed": False, "cleanup": []}
    previous = previous_factory()
    current = current_factory() if family == "local-independence" else None
    try:
        with previous:
            if previous.subject.mode != "public" or previous.subject.inventory["version"] == destination.inventory["version"]:
                raise ValueError("Previous subject must be a different published stable")
            previous.install()
            prior_identity = previous.observation.copy()
            work = Workspace(previous)
            before = recipe(work, family)
            # Published pre-setup releases expose adoption through start/invoke.
            # This is the declared prior-state recipe, not a checkout fallback.
            adopted = work.invoke(adoption_action(work, "adopt"))
            if adopted.get("effect_outcome", {}).get("status") != "committed":
                raise ValueError("Previous stable public adoption did not commit")
            validate_pointer_files(work.files())
            work.write(".agentic-workspace/local/custom-note.txt", b"Preserve across refresh\n")
            preserved = work.files()
            results.update(executed=True, previous=prior_identity, requested=destination.identity())
            if current is not None:
                with current:
                    current.install()
                    result = execute(current, "first-contact")
                    if result["status"] != "passed":
                        raise ValueError("Current repository did not finish ordinary work")
                    if work.files() != preserved:
                        raise ValueError("Current install mutated the previous repository")
                    # Each command runs in its own installed repo after the sibling's setup.
                    read = work.start(work.start()["configuration_write"]["repository_adoption_request"])
                    if not read.get("configuration_write", {}).get("repository_adoption"):
                        raise ValueError("Repository-local version independence failed")
                    wrong_global_control(current)
                    wrong_global_control(previous)
                    results["global_control"] = "absent-and-wrong-global"
                    results["current"] = result
            else:
                previous.subject = destination
                previous.install()
                refreshed = work.client.call("setup", "--yes")
                if (
                    refreshed["status"] not in {"already-current", "applied"}
                    and refreshed.get("effect_outcome", {}).get("status") != "committed"
                ):
                    raise ValueError("Installed upgrade did not refresh")
                for name in ("notes.txt", "policy.md", ".agentic-workspace/local/custom-note.txt"):
                    if work.files().get(name) != preserved[name]:
                        raise ValueError("Upgrade changed independently owned content")
                ordinary_change(work)
                validate_pointer_files(work.files())
                if hasattr(previous, "repo") and previous.profile == "standalone":
                    linked_worktree_control(previous)
                    results["linked_worktree"] = "native-installed-setup-and-reentry"
                result = evaluate(before, work.files(), expected_task(), claim={"status": "complete"}, executed=True, subject_verified=True)
                if result["status"] != "passed":
                    raise ValueError("Upgrade task did not complete")
                results["current"] = result
            results["status"] = "passed"
    except (Exception, KeyboardInterrupt) as error:
        results.update(status="failed", execution_error=str(error)[:2000])
    finally:
        results["cleanup"] = [previous.cleanup, *([current.cleanup] if current else [])]
    return results


def wrong_global_control(consumer):
    """A deliberately failing global command must not rescue a local invocation."""
    if hasattr(consumer, "repo"):
        directory = consumer.root / "wrong-global"
        directory.mkdir()
        path = directory / ("agentic-workspace.cmd" if os.name == "nt" else "agentic-workspace")
        path.write_text("@exit /b 99\n" if os.name == "nt" else "#!/bin/sh\nexit 99\n")
        path.chmod(0o755)
        old = consumer.env["PATH"]
        try:
            consumer.env["PATH"] = str(directory) + os.pathsep + old
            if not shutil.which("agentic-workspace", path=consumer.env["PATH"]):
                raise ValueError("Wrong global control was not exposed")
            consumer.exec([*consumer.command, "--help"])
        finally:
            consumer.env["PATH"] = old
    else:
        consumer.exec(
            [
                "sh",
                "-c",
                "mkdir -p ../wrong-global; printf '#!/bin/sh\\nexit 99\\n' > ../wrong-global/agentic-workspace; chmod +x ../wrong-global/agentic-workspace",
            ]
        )
        consumer.exec(
            [
                "sh",
                "-c",
                'PATH="$PWD/../wrong-global:$PATH"; export PATH; command -v agentic-workspace; "$@"',
                "sh",
                *consumer.command,
                "--help",
            ]
        )


def linked_worktree_control(consumer):
    """Exercise native Git/path handling without exposing the maintainer checkout."""
    git = consumer.tools["git"]
    consumer.exec([git, "add", "README.md", "settings.json", "policy.md", "notes.txt"])
    consumer.exec([git, "-c", "user.name=Consumer", "-c", "user.email=consumer@example.invalid", "commit", "-qm", "fixture"])
    linked = consumer.root / "linked worktree"
    consumer.exec([git, "worktree", "add", "--detach", str(linked), "HEAD"])
    result = consumer.exec([*consumer.command, "setup", "--target", str(linked), "--yes", "--format", "json"])
    if json.loads(result.stdout)["effect_outcome"]["status"] != "committed":
        raise ValueError("Linked-worktree setup failed")
    validate_pointer_files(snapshot(linked))
    result = consumer.exec([*consumer.command, "start", "--target", str(linked), "--task", TASK, "--projection", "full"])
    if not json.loads(result.stdout).get("semantic_routes"):
        raise ValueError("Linked-worktree reentry failed")
