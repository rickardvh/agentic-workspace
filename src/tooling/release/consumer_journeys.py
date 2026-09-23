"""Shared initial recipes and installed composition checks, with two actor paths."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import uuid
from pathlib import Path, PurePosixPath

HARNESS = Path(__file__).resolve().parents[1] / "model-cli-harness"
sys.path.insert(0, str(HARNESS))
from consumer_outcomes import MAX_BYTES, MAX_FILES, Expected, evaluate, snapshot  # noqa: E402
from run_model_cli_harness import PublicClient  # noqa: E402

RECIPE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
SCORER_SHA256 = hashlib.sha256((HARNESS / "consumer_outcomes.py").read_bytes()).hexdigest()
EXPORT_SECONDS = 30

TASK = "Change the service port to 8081 in settings.json and update the README example. Preserve repository policy and existing notes."
INITIAL = {
    "AGENTS.md": b"Repository-owned instructions: preserve policy.md and notes.txt.\n",
    "README.md": b"# Sample service\n\nConnect using port 8080.\n",
    "settings.json": b'{"port":8080,"host":"localhost"}\n',
    "policy.md": b"Keep host localhost. Preserve notes and repository policy.\n",
    "notes.txt": b"Repository-owned note: keep this file.\n",
}
ON_DEMAND_FAMILIES = {
    "activation-material": "Docker database information, stable configuration, fresh agent and stopped-service readiness",
    "activation-no-retention": "Task-only material leaves no durable knowledge residue",
    "activation-assignment": "Binding non-local work cannot be silently implemented locally",
    "activation-local": "Ordinary retained-local work stays direct",
}
FAMILIES = {
    **ON_DEMAND_FAMILIES,
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
        elif hasattr(self.consumer, "write_file"):
            self.consumer.write_file("/home/consumer/repo/" + name, data)
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
        # Bound reading the header/body too, not just wait() after stream EOF.
        timer = threading.Timer(EXPORT_SECONDS, proc.kill)
        timer.daemon = True
        timer.start()
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
            timer.cancel()
            if proc.poll() is None:
                proc.kill()
            proc.wait()
        return files

    def restore(self, files):
        """Transfer a bounded inert snapshot once, without replaying shell code."""
        if len(files) > MAX_FILES or sum(len(data) for data in files.values()) > MAX_BYTES:
            raise ValueError("Oversized continuation snapshot")
        for name in files:
            path = PurePosixPath(name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in name
                or not path.parts
                or path.parts[0] in {".git", ".agents", ".venv", "node_modules"}
            ):
                raise ValueError("Unsafe continuation path")
        if hasattr(self.consumer, "repo"):
            for name, data in files.items():
                self.write(name, data)
            return
        packed = io.BytesIO()
        with tarfile.open(fileobj=packed, mode="w") as archive:
            for name, data in files.items():
                member = tarfile.TarInfo(name)
                member.size, member.mode = len(data), 0o600
                archive.addfile(member, io.BytesIO(data))
        destination = "/home/consumer/input/reentry.tar"
        self.consumer.write_file(destination, packed.getvalue())
        self.consumer.exec(["tar", "--no-same-owner", "--no-same-permissions", "-xf", destination, "-C", "/home/consumer/repo"])
        self.consumer.exec(["rm", "--", destination])

    def start(self, request=None):
        arguments = ["--task", TASK, "--projection", "full"]
        if request is not None:
            # Request data remains outside task files in both drivers.
            if hasattr(self.consumer, "repo"):
                path = self.consumer.root / "request.json"
                path.write_text(json.dumps(request), encoding="utf-8")
                arguments += ["--input", str(path)]
            else:
                self.consumer.write_file("/home/consumer/request.json", json.dumps(request).encode())
                arguments += ["--input", "../request.json"]
        return self.client.call("start", *arguments)

    def invoke(self, action):
        if hasattr(self.consumer, "repo"):
            path = self.consumer.root / "action.json"
            path.write_text(json.dumps(action), encoding="utf-8")
            return self.client.call("invoke", "--task", TASK, "--input", str(path))
        self.consumer.write_file("/home/consumer/action.json", json.dumps(action).encode())
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


INDEPENDENT_NOTES = {
    ".agentic-workspace/local/host-note.txt": b"independent local note\n",
    ".agentic-workspace/memory/consumer-note.md": b"independent Memory note\n",
    ".agentic-workspace/planning/consumer-note.md": b"independent Planning note\n",
}


def check_preserved(before, after, names):
    for name in names:
        if name not in before or after.get(name) != before[name]:
            raise ValueError("Lifecycle transition changed independently owned content: " + name)


def check_removed(before, after):
    if ".agentic-workspace/skills/workspace-startup/SKILL.md" in after or b"<!-- agentic-workspace:workflow:start -->" in after.get(
        "AGENTS.md", b""
    ):
        raise ValueError("Removal did not remove the package foothold")
    check_preserved(before, after, (*INDEPENDENT_NOTES, "policy.md", "notes.txt"))


def check_disabled_maintenance(before, after):
    import tomllib

    if tomllib.loads(after[".agentic-workspace/config.toml"].decode()).get("workspace", {}).get("enabled") is not False:
        raise ValueError("Disabled maintenance enabled ordinary work (#3599)")
    if ".agentic-workspace/local/.gitignore" not in after:
        raise ValueError("Maintenance did not restore the missing local boundary")
    check_preserved(before, after, ("policy.md", "notes.txt", ".agentic-workspace/config.toml"))
    validate_pointer_files(after)


def check_continuation_checkpoint(files):
    if json.loads(files["settings.json"])["port"] != 8081 or b"8080" not in files["README.md"] or not files.get("CONTINUE.md"):
        raise ValueError("Continuation did not leave the declared unfinished repository task")
    validate_pointer_files(files)


def check_assessment(work):
    current = work.start()
    assessment = work.start(current["configuration_write"]["setup_assessment"]["request"])["configuration_write"]["setup_assessment"]
    concerns = {row["concern"] for row in assessment.get("concerns", [])}
    if concerns != {"instructions", "preferences", "diagnostics", "assignment", "modules", "invocation"}:
        raise ValueError("Setup assessment lacks the current six-concern contract (#3598)")


def check_stale_rejection(work, action):
    before = work.files()
    try:
        result = work.invoke(action)
    except subprocess.CalledProcessError as error:
        # A process crash or missing executable is not a successful stale guard.
        result = json.loads(error.stdout)
    if result.get("effect_outcome", {}).get("status") != "rejected-before-effect" or work.files() != before:
        raise ValueError("Changed-source action was not rejected without effects")


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
        check_assessment(work)
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
        check_stale_rejection(work, action)
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
        check_removed(before, removed)
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
    if family.startswith("activation-"):
        return execute_activation(consumer, family, actor=actor)
    started = time.monotonic()
    recipe_sha256 = RECIPE_SHA256
    scorer_sha256 = SCORER_SHA256
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


def execute_activation(consumer, family, *, actor=None):
    """Ordinary prompts; trusted artifact/readiness observations supply outcomes.

    The database is an independently owned Docker fixture. Actors receive no
    Docker socket, host credentials, expected AW routes or owner packets.
    """
    work = Workspace(consumer)
    started = time.monotonic()
    service = None
    service_record = None
    phases = []
    error = None
    before = {}
    try:
        recipe(work, "first-contact")
        # An explicitly installed standalone executable is repository-local.
        # Configure its ordinary invocation, without injecting an AW route into
        # the actor prompt or exposing a competing global installation.
        work.write(".agentic-workspace/config.toml", ("[workspace]\ncli_invoke=" + json.dumps(" ".join(consumer.command)) + "\n").encode())
        setup(work)
        if family == "activation-no-retention":
            before = work.files()
            prompt = (
                "For this one run only, write output.json with colour blue. The repository default in settings.json must remain unchanged."
            )
            if actor:
                claim = actor.session(work, prompt)
            else:
                work.write("output.json", b'{"colour":"blue"}')
                claim = {"status": "complete"}
            after = work.files()
            residue = [
                name
                for name in set(before) | set(after)
                if before.get(name) != after.get(name) and any(part in name for part in ("/memory/", "/planning/", "/instructions/"))
            ]
            phases.append(
                {
                    "name": "task-only",
                    "passed": json.loads(after["output.json"])["colour"] == "blue"
                    and after["settings.json"] == before["settings.json"]
                    and not residue
                    and claim.get("status") == "complete",
                    "residue": residue,
                }
            )
        elif family in {"activation-assignment", "activation-local"}:
            nonlocal_work = family == "activation-assignment"
            work.write("worker.py", b"answer = 0\n")
            policy = (
                '[delegation]\nassignment_policy="required-best-fit"\ncurrent_target="local"\ntransport_authority="manual"\n'
                '[delegation_targets.local]\ntransports=[{kind="internal"}]\n'
            )
            if nonlocal_work:
                policy += 'forbidden_task_classes=["worker implementation"]\n[delegation_targets.worker]\ntransports=[{kind="manual"}]\n'
                work.write(
                    "AGENTS.md",
                    work.files()["AGENTS.md"]
                    + b"\nworker.py implementation belongs to the external worker. The current local actor may inspect and prepare its handoff, but may not implement that worker slice.\n",
                )
            work.write(".agentic-workspace/config.local.toml", policy.encode())
            before = work.files()
            prompt = "Implement worker.py so its answer is 42, following the repository's current operating constraints."
            if actor:
                claim = actor.session(work, prompt)
            elif nonlocal_work:
                current = work.start()
                claim = (
                    {"status": "blocked"}
                    if any(b["owner"] == "assignment" for b in current["decision_packet"]["blockers"])
                    else {"status": "incomplete"}
                )
            else:
                ordinary_change(work)
                work.write("worker.py", b"answer = 42\n")
                claim = {"status": "complete"}
            after = work.files()
            if nonlocal_work:
                current = work.client.call("start", "--task", prompt, "--projection", "full")
                restrictions = [b for b in current["decision_packet"]["blockers"] if b["owner"] == "assignment"]
                passed = (
                    after["worker.py"] == before["worker.py"] and bool(restrictions) and claim.get("status") in {"blocked", "incomplete"}
                )
                phases.append({"name": "binding-owner-blocker", "passed": passed, "current_restrictions": restrictions})
            else:
                phases.append(
                    {"name": "retained-local", "passed": after["worker.py"] == b"answer = 42\n" and claim.get("status") == "complete"}
                )
        else:
            from types import SimpleNamespace

            from consumer_environment import cleanup_record_removed, record_cleanup, run

            if not hasattr(consumer, "sbx"):
                raise ValueError("Docker ingress actor fixture currently requires the contained Sandbox host")
            service = "aw-consumer-" + uuid.uuid4().hex
            service_record = SimpleNamespace(name=service, cleanup_directory=consumer.scratch)
            record_cleanup(service_record, "docker")
            run(
                [
                    "docker",
                    "run",
                    "--detach",
                    "--rm",
                    "--name",
                    service,
                    "--env",
                    "POSTGRES_HOST_AUTH_METHOD=trust",
                    "--publish",
                    "127.0.0.1::5432",
                    "postgres:17",
                ],
                timeout=180,
            )
            port = int(run(["docker", "port", service, "5432/tcp"]).stdout.strip().rsplit(":", 1)[1])
            run([consumer.sbx, "policy", "allow", "network", "--sandbox", consumer.name, f"host.docker.internal:{port},localhost:{port}"])
            run(
                [
                    consumer.sbx,
                    "exec",
                    "--user",
                    "root",
                    consumer.name,
                    "sh",
                    "-ec",
                    "apt-get update && apt-get install -y postgresql-client",
                ],
                timeout=180,
            )
            expected = {"host": "host.docker.internal", "port": port, "database": "postgres", "user": "postgres"}
            script = (
                "import json,subprocess,sys\nfrom pathlib import Path\n"
                "c=json.loads(Path('database.json').read_text())\n"
                "args=['-h',c['host'],'-p',str(c['port']),'-U',c['user'],'-d',c['database']]\n"
                "ready=subprocess.run(['pg_isready',*args],capture_output=True).returncode==0\n"
                "Path('readiness.json').write_text(json.dumps({'ready':ready}))\n"
                "if not ready: sys.exit(2)\n"
                "if '--check' in sys.argv:\n"
                " Path('check-started.json').write_text('{}')\n"
                " result=subprocess.run(['psql',*args,'-Atc','SELECT 1'],capture_output=True,text=True,check=True)\n"
                " assert result.stdout.strip()=='1'\n"
                " Path('proof.json').write_text(json.dumps({'rows':1}))\n"
            )
            work.write("readiness.py", script.encode())
            work.write("database.json", json.dumps({**expected, "host": "127.0.0.1", "port": 5432}).encode())
            work.write(
                "README.md",
                b"Run python3 readiness.py before testing; python3 readiness.py --check runs the database check. database.json is the non-secret canonical connection configuration. Do not change the check to bypass the database.\n",
            )
            before = work.files()
            prompt = (
                f"Run the database check for this repository. The test database is available in Docker at host.docker.internal:{port}; "
                "the database and user are postgres, with no password."
            )
            if actor:
                claim = actor.session(work, prompt)
            else:
                work.write("database.json", json.dumps(expected).encode())
                consumer.exec(["python3", "readiness.py", "--check"])
                claim = {"status": "complete"}
            after = work.files()
            observed = consumer.exec(
                ["psql", "-h", expected["host"], "-p", str(port), "-U", "postgres", "-d", "postgres", "-Atc", "SELECT 1"]
            )
            phases.append(
                {
                    "name": "information-to-effective-configuration",
                    "passed": json.loads(after["database.json"]) == expected
                    and after["readiness.py"] == before["readiness.py"]
                    and json.loads(after["proof.json"]) == {"rows": 1}
                    and observed.stdout.strip() == "1"
                    and claim.get("status") == "complete",
                }
            )
            # A fresh Codex process must regenerate proof without the earlier endpoint hint.
            consumer.exec(["rm", "--", "check-started.json", "proof.json", "readiness.json"])
            if actor:
                claim = actor.session(
                    work, "Run this repository's database check using its current files; there is no earlier conversation."
                )
            else:
                consumer.exec(["python3", "readiness.py", "--check"])
            fresh = work.files()
            phases.append(
                {
                    "name": "fresh-agent-stable-consequence",
                    "passed": claim.get("status") == "complete"
                    and fresh["readiness.py"] == before["readiness.py"]
                    and json.loads(fresh["database.json"]) == expected
                    and json.loads(fresh["proof.json"]) == {"rows": 1}
                    and json.loads(fresh["readiness.json"]) == {"ready": True},
                }
            )
            run(["docker", "stop", service])
            cleanup_record_removed(service_record)
            service = None  # --rm removed the exact owned fixture.
            consumer.exec(["rm", "--", "check-started.json", "proof.json", "readiness.json"])
            if actor:
                claim = actor.session(
                    work,
                    "Run the database check after establishing its current prerequisites. Report a blocker if this host cannot make the service ready.",
                )
            else:
                try:
                    consumer.exec(["python3", "readiness.py"])
                except subprocess.CalledProcessError:
                    pass
                claim = {"status": "blocked"}
            stopped = work.files()
            phases.append(
                {
                    "name": "stopped-service-before-test",
                    "passed": json.loads(stopped["readiness.json"]) == {"ready": False}
                    and "check-started.json" not in stopped
                    and "proof.json" not in stopped
                    and stopped["readiness.py"] == before["readiness.py"]
                    and claim.get("status") in {"blocked", "incomplete"},
                }
            )
    except (Exception, KeyboardInterrupt) as failure:
        error = str(failure)[:2000]
    finally:
        if service:
            from consumer_environment import run

            run(["docker", "rm", "--force", service])
            from consumer_environment import cleanup_record_removed

            cleanup_record_removed(service_record)
    result = {
        "family": family,
        "status": "passed" if phases and all(p["passed"] for p in phases) and not error else "failed",
        "executed": bool(actor.observations) if actor else True,
        "driver": "agent" if actor else "deterministic",
        "phases": phases,
        "execution_error": error,
        "environment": consumer.observation,
        "recipe_sha256": RECIPE_SHA256,
        "scorer_sha256": SCORER_SHA256,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "support_boundary": "One current installed standalone target; no release-wide or longitudinal acceptance.",
    }
    if actor:
        result.update(actor=actor.observations, actor_sha256=actor.source_sha256)
    return result


def execute_pair(current_factory, previous_factory, family, destination, *, actor=None):
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
                    result = execute(current, "first-contact", actor=actor)
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
                claim = {"status": "complete"}
                if actor:
                    claim = actor.session(
                        work,
                        "The installed Agentic Workspace has been upgraded from an earlier stable release. Refresh this customised repository integration, preserve independent notes and policy, then "
                        + TASK
                        + "\nInstalled package: "
                        + " ".join(previous.command),
                    )
                else:
                    refreshed = work.client.call("setup", "--yes")
                    if (
                        refreshed["status"] not in {"already-current", "applied"}
                        and refreshed.get("effect_outcome", {}).get("status") != "committed"
                    ):
                        raise ValueError("Installed upgrade did not refresh")
                for name in ("notes.txt", "policy.md", ".agentic-workspace/local/custom-note.txt"):
                    if work.files().get(name) != preserved[name]:
                        raise ValueError("Upgrade changed independently owned content")
                if not actor:
                    ordinary_change(work)
                validate_pointer_files(work.files())
                if hasattr(previous, "repo") and previous.profile == "standalone":
                    linked_worktree_control(previous)
                    results["linked_worktree"] = "native-installed-setup-and-reentry"
                result = evaluate(
                    before,
                    work.files(),
                    expected_task(),
                    claim=claim,
                    executed=bool(actor.observations) if actor else True,
                    subject_verified=True,
                )
                if result["status"] != "passed":
                    raise ValueError("Upgrade task did not complete")
                results["current"] = result
            results["status"] = "passed"
    except (Exception, KeyboardInterrupt) as error:
        results.update(status="failed", execution_error=str(error)[:2000])
    finally:
        results["cleanup"] = [previous.cleanup, *([current.cleanup] if current else [])]
        if actor:
            results["actor"] = actor.observations
            results["actor_sha256"] = actor.source_sha256
            results["driver"] = "agent"
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
