"""Codex Sandbox actor transport; shared consumer preparation and inert scoring.

The provider template's additional tools are observed and disclosed. It cannot
establish a minimal-profile absence claim. Unsupported native backends fail closed.
"""

from __future__ import annotations

import hashlib
import json
import queue
import re
import subprocess
import threading
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

from consumer_environment import PROFILES, DockerConsumer, cleanup_record_removed, record_cleanup, run
from run_sbx_codex_adapter import _codex_exec_command

SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def portable_continuation(files):
    """Machine-local custody is reconstructed, never transported to a new host."""
    return {
        name: data
        for name, data in files.items()
        if name != ".agentic-workspace/local" and not name.startswith(".agentic-workspace/local/")
    }


class SandboxConsumer(DockerConsumer):
    """Both drivers may select this same provider-bearing environment explicitly."""

    def __init__(self, subject, profile, target, template, scratch, sbx="sbx"):
        if not re.fullmatch(r"docker\.io/docker/sandbox-templates:codex@sha256:[a-f0-9]{64}", template):
            raise ValueError("Require an immutable non-Docker Codex template reference")
        super().__init__(subject, profile, target, "sha256:" + template.rsplit(":", 1)[1])
        self.template, self.scratch, self.sbx = template, scratch, sbx
        self.cleanup_directory = scratch
        self.observation.update(
            backend="codex-sandbox",
            template=template,
            isolation="microvm-disposable-workspace",
            minimal_profile_absence="not-claimed-provider-tools-present",
        )

    def __enter__(self):
        record_cleanup(self, "sandbox")
        try:
            run(
                [
                    self.sbx,
                    "create",
                    "--name",
                    self.name,
                    "--template",
                    self.template,
                    "--cpus",
                    "2",
                    "--memory",
                    "2g",
                    "--skills",
                    "off",
                    "codex",
                ],
                timeout=180,
            )
            run(
                [
                    self.sbx,
                    "exec",
                    "--user",
                    "root",
                    self.name,
                    "sh",
                    "-c",
                    "set -eu; useradd -u 10002 -m -d /home/consumer -s /bin/sh consumer; "
                    "mkdir -p /home/consumer/repo /home/consumer/input /home/consumer/tmp /home/consumer/.codex; "
                    "chown -R consumer:consumer /home/consumer; chmod 700 /home/agent; "
                    "test ! -S /run/ssh-agent.sock || chmod 000 /run/ssh-agent.sock; "
                    'if command -v sudo >/dev/null; then chmod 000 "$(command -v sudo)"; fi',
                ]
            )
            # Subscription OAuth uses Docker's proxy provider, not the API billing
            # endpoint. Do not copy the template's MCP gateway or other settings.
            config = (
                'forced_login_method = "api"\nmodel_provider = "sandboxd"\n'
                '[model_providers.sandboxd]\nname = "Sandbox Proxy"\n'
                'base_url = "https://chatgpt.com/backend-api/codex"\n'
                'experimental_bearer_token = "oai-oat01-proxy-managed"\nrequires_openai_auth = false\n'
            )
            self.exec(["sh", "-c", 'printf %s "$1" > "$HOME/.codex/config.toml"', "sh", config])
            self.exec(["git", "init", "-q"])
            self.prepare_tools()
            self.observe_tools()
            return self
        except BaseException:
            try:
                self.close()
            except Exception as cleanup_error:
                self.observation["cleanup_error"] = str(cleanup_error)[:500]
            raise

    def exec(self, argv, *, timeout=120):
        return run(self.exec_command(argv), timeout=timeout)

    def exec_command(self, argv):
        # A different uid cannot read the provider template's process environments
        # or home. Carry only model transport and certificate configuration.
        clean = (
            'exec env -i PATH="/home/consumer/.cargo/bin:$PATH" HOME=/home/consumer CODEX_HOME=/home/consumer/.codex '
            'TMPDIR=/home/consumer/tmp HTTPS_PROXY="$HTTPS_PROXY" HTTP_PROXY="$HTTP_PROXY" '
            'SSL_CERT_FILE="$SSL_CERT_FILE" NODE_EXTRA_CA_CERTS="$NODE_EXTRA_CA_CERTS" '
            'REQUESTS_CA_BUNDLE="$REQUESTS_CA_BUNDLE" NODE_USE_ENV_PROXY=1 "$@"'
        )
        return [self.sbx, "exec", "--user", "10002:10002", "--workdir", "/home/consumer/repo", self.name, "sh", "-c", clean, "sh", *argv]

    def prepare_tools(self):
        """Declared profile dependencies, installed before either driver starts."""
        commands = {
            "node": "npm install --global --prefix /usr/local pnpm@10.30.3",
            "python": "apt-get update && apt-get install -y python3-venv && python3 -m venv /opt/consumer-uv && /opt/consumer-uv/bin/pip install uv==0.8.22 && ln -sf /opt/consumer-uv/bin/uv /usr/local/bin/uv",
            "cargo": "apt-get update && apt-get install -y build-essential pkg-config libssl-dev curl",
        }
        if self.profile in commands:
            run([self.sbx, "exec", "--user", "root", self.name, "sh", "-ec", commands[self.profile]], timeout=300)
        if self.profile == "cargo":
            import tomllib

            version = tomllib.loads((Path(__file__).resolve().parents[3] / "rust-toolchain.toml").read_text())["toolchain"]["channel"]
            self.exec(
                [
                    "sh",
                    "-ec",
                    'curl --proto "=https" --tlsv1.2 -sSf https://sh.rustup.rs -o ../tmp/rustup.sh; sh ../tmp/rustup.sh -y --profile minimal --default-toolchain "$1"',
                    "sh",
                    version,
                ],
                timeout=300,
            )

    def copy_in(self, source, destination):
        incoming = "/tmp/input-" + uuid.uuid4().hex
        run([self.sbx, "cp", str(source.resolve()), f"{self.name}:{incoming}"])
        self.exec(["cp", "-R", incoming, destination])

    def installation_digest(self):
        # Read with the trusted root-owned checker, outside actor PATH resolution.
        return run(
            [
                self.sbx,
                "exec",
                "--user",
                "root",
                "--workdir",
                "/home/consumer/repo",
                self.name,
                "/usr/bin/sha256sum",
                *self.installed_paths,
            ]
        ).stdout

    def install(self, **kwargs):
        command = super().install(**kwargs)
        self.installed_digest = self.installation_digest()
        if self.profile == "standalone":
            self.observe_product_boundary()
            command = self.command
        return command

    def root_exec(self, argv):
        return run([self.sbx, "exec", "--user", "root", "--workdir", "/home/consumer/repo", self.name, *argv])

    def observe_product_boundary(self):
        boundary = Path(__file__).with_name("consumer_product_boundary.py")
        incoming = "/tmp/product-boundary-" + uuid.uuid4().hex
        run([self.sbx, "cp", str(boundary), f"{self.name}:{incoming}"])
        self.product_subject = {
            **self.subject.identity(),
            "cli_sha256": self.observation["installed"]["cli_sha256"],
            "core_sha256": self.observation["installed"]["sha256"],
        }
        config = json.dumps({"subject": self.product_subject})
        wrapper = '#!/bin/sh\nexec /usr/bin/python3 -I /opt/aw-observer/boundary.py client "$@"\n'
        self.root_exec(
            [
                "sh",
                "-ec",
                "mkdir -p /opt/aw-observer/subject; chmod 755 /opt/aw-observer /opt/aw-observer/subject; "
                'cp "$1" /opt/aw-observer/boundary.py; cp "$2" /opt/aw-observer/subject/agentic-workspace; '
                'cp "$3" /opt/aw-observer/subject/agentic-workspace-core; '
                'printf %s "$4" > /opt/aw-observer/config.json; printf %s "$5" > /opt/aw-observer/agentic-workspace; '
                "touch /opt/aw-observer/receipts.jsonl; chmod 600 /opt/aw-observer/receipts.jsonl; "
                "chmod 555 /opt/aw-observer/subject/* /opt/aw-observer/boundary.py /opt/aw-observer/agentic-workspace; "
                "nohup /usr/bin/python3 -I /opt/aw-observer/boundary.py server >/opt/aw-observer/server.log 2>&1 </dev/null &",
                "sh",
                incoming,
                *self.installed_paths[:2],
                config,
                wrapper,
            ]
        )
        self.root_exec(
            [
                "sh",
                "-ec",
                "for n in 1 2 3 4 5; do test ! -S /opt/aw-observer/socket || exit 0; sleep 1; done; cat /opt/aw-observer/server.log; exit 1",
            ]
        )
        self.command = ["/opt/aw-observer/agentic-workspace"]
        self.installed_paths += [
            "/opt/aw-observer/subject/agentic-workspace",
            "/opt/aw-observer/subject/agentic-workspace-core",
            "/opt/aw-observer/boundary.py",
            "/opt/aw-observer/agentic-workspace",
            "/opt/aw-observer/config.json",
        ]
        self.installed_digest = self.installation_digest()
        # The tested actor cannot alter the fixed subject or manufacture receipts.
        self.exec(
            [
                "sh",
                "-ec",
                "test ! -w /opt/aw-observer; test ! -r /opt/aw-observer/receipts.jsonl; test ! -w /opt/aw-observer/subject/agentic-workspace; test ! -w /opt/aw-observer/config.json",
            ]
        )
        before = self.product_receipts()
        self.exec(["/usr/bin/python3", "-c", 'import json; print(json.dumps({"activation":{"kind":"agentic-workspace/activation/v1"}}))'])
        if self.product_receipts() != before:
            raise ValueError("Non-product stdout acquired a product receipt")
        self.exec([*self.command, "--help"])
        receipts = self.product_receipts()[len(before) :]
        if len(receipts) != 1 or receipts[0]["argv"] != ["--help"] or receipts[0]["exit_code"] != 0:
            raise ValueError("Product boundary did not observe the fixed subject")
        self.observation["product_boundary"] = {
            "kind": "root-owned-fixed-subject/v1",
            "subject": self.product_subject,
            "observer_sha256": hashlib.sha256(boundary.read_bytes()).hexdigest(),
            "controls": "non-product-output-unobserved; receipt-and-subject-writes-denied; actual-help-observed",
        }

    def product_receipts(self):
        if not hasattr(self, "product_subject"):
            return []
        receipt_path = "/opt/aw-observer/receipts.jsonl"
        raw = self.root_exec(["cat", receipt_path]).stdout
        if len(raw) > 40 * 1024 * 1024:
            raise ValueError("Product receipt export exceeds bound")
        receipts = [json.loads(line) for line in raw.splitlines()]
        if any(
            r.get("subject") != self.product_subject or r.get("kind") != "agentic-workspace/observed-installed-call/v1" for r in receipts
        ):
            raise ValueError("Product receipt subject differs from the admitted installation")
        return receipts

    def verify_installation_unchanged(self):
        if self.installation_digest() != self.installed_digest:
            raise ValueError("Actor changed the installed subject or Node binding")
        self.observation["post_actor_installation"] = "unchanged"
        self.observation["post_actor_verified_paths"] = self.installed_paths

    def observe_tools(self):
        required, forbidden = PROFILES[self.profile]
        inventory = {}
        for tool in (*required, *forbidden):
            value = self.exec(["sh", "-c", 'command -v "$1" || true', "sh", tool]).stdout.strip()
            inventory[tool] = value or None
            if tool in required and not value:
                raise ValueError(f"Sandbox lacks required consumer tool: {tool}")
        if inventory["agentic-workspace"]:
            raise ValueError("Sandbox template contains a global AW installation")
        self.observation["tools"] = inventory
        self.observation["forbidden_visible"] = [tool for tool in forbidden if inventory[tool]]
        self.observation["versions"] = {tool: self.exec([tool, "--version"]).stdout[:500] for tool in required}
        expected = "aarch64" if self.subject.row(self.target)["node_arch"] == "arm64" else "x86_64"
        if self.exec(["uname", "-m"]).stdout.strip() != expected:
            raise ValueError("Sandbox architecture does not match target")
        self.observation["provider_cli"] = self.exec(["codex", "--version"]).stdout.strip()

    def restrict_actor(self):
        # Provider proxy auth is allowed; publishing, repository write and SSH
        # credentials must not be reachable by the tested actor.
        run([self.sbx, "exec", "--user", "root", self.name, "sh", "-ec", "test ! -S /run/ssh-agent.sock || chmod 000 /run/ssh-agent.sock"])
        run(
            [
                self.sbx,
                "policy",
                "deny",
                "network",
                "--sandbox",
                self.name,
                "github.com,*.github.com,*.githubusercontent.com,registry.npmjs.org,upload.pypi.org,crates.io",
            ]
        )
        try:
            check = self.exec(
                [
                    "sh",
                    "-c",
                    'test "$(id -u)" != 0 || { echo root-user >&2; exit 1; }; '
                    'test ! -e "$CODEX_HOME/auth.json" || { echo actor-auth-file >&2; exit 1; }; '
                    "test ! -r /home/agent/.codex/auth.json && test ! -r /proc/1/environ || { echo template-state-readable >&2; exit 1; }; "
                    "test ! -w /run/ssh-agent.sock || { echo ssh-socket-accessible >&2; exit 1; }; "
                    'for socket in /var/run/docker.sock /run/docker.sock; do test ! -S "$socket" || { echo docker-socket >&2; exit 1; }; done; '
                    "! command -v agentic-workspace || { echo global-aw >&2; exit 1; }; "
                    '! env | cut -d= -f1 | grep -E "^(OPENAI_API_KEY|CODEX_API_KEY|GH_TOKEN|GITHUB_TOKEN|NPM_TOKEN|CARGO_REGISTRY_TOKEN|SSH_AUTH_SOCK)$" || '
                    "{ echo credential-environment >&2; exit 1; }; "
                    "(! command -v sudo >/dev/null || ! sudo -n true 2>/dev/null) || { echo sudo-enabled >&2; exit 1; }",
                ]
            )
        except subprocess.CalledProcessError as error:
            reasons = {
                "root-user",
                "actor-auth-file",
                "template-state-readable",
                "ssh-socket-accessible",
                "docker-socket",
                "global-aw",
                "credential-environment",
                "sudo-enabled",
            }
            observed = [line for line in (error.stderr or "").splitlines() if line in reasons]
            raise ValueError("Actor containment preflight failed: " + ", ".join(observed or ["unknown"])) from None
        if check.returncode:
            raise ValueError("Actor containment preflight failed")
        self.observation["actor_containment"] = "non-root-no-sudo-no-docker-socket-no-publish-transport"

    def stop_actor(self):
        # Kill all actor-owned processes, including detached children, before
        # trusted export. No actor-controlled checker runs in the controller.
        run([self.sbx, "exec", "--user", "root", self.name, "sh", "-c", "pkill -KILL -u 10002 || test $? = 1"])

    def archive_command(self):
        return [
            self.sbx,
            "exec",
            "--user",
            "root",
            self.name,
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

    def close(self):
        try:
            run([self.sbx, "rm", "--force", self.name])
            self.cleanup = "removed"
            cleanup_record_removed(self)
        except subprocess.CalledProcessError:
            self.cleanup = "failed"
            raise


def bounded_codex(command, *, seconds, token_ceiling=None, stop):
    """Bound wall time/output and stop on observed usage; no cost is fabricated.

    Token telemetry arrives after requests, so this is an observed stop threshold,
    not a provider-side hard spend cap. The run record preserves that distinction.
    """
    if not 1 <= seconds <= 900 or (token_ceiling is not None and token_ceiling <= 0):
        raise ValueError("A bounded session and, when supplied, positive token threshold are required")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    events = queue.Queue(maxsize=256)
    finished = threading.Event()

    def enqueue(value):
        while not finished.is_set():
            try:
                events.put(value, timeout=0.1)
                return
            except queue.Full:
                continue

    def read():
        try:
            for line in iter(lambda: process.stdout.readline(65537), ""):
                enqueue(line)
                if finished.is_set():
                    break
        finally:
            enqueue(None)

    threading.Thread(target=read, daemon=True).start()
    deadline = time.monotonic() + seconds
    size, tokens, calls = 0, None, 0
    status = "running"
    message = None
    diagnostics = []
    operating_calls = []
    try:
        while time.monotonic() < deadline:
            try:
                line = events.get(timeout=min(1, max(0.01, deadline - time.monotonic())))
            except queue.Empty:
                continue
            if line is None:
                status = "completed" if process.wait(timeout=5) == 0 else "provider-or-agent-failure"
                break
            size += len(line.encode())
            if size > 2 * 1024 * 1024:
                status = "output-budget-exhausted"
                break
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("type") in {"error", "turn.failed"}:
                detail = str(event.get("message") or event.get("error", {}))[:1000]
                detail = re.sub(r"https?://\S+", "[endpoint]", detail)
                detail = re.sub(r"(?i)(bearer\s+|sk-|ghp_|gho_)[A-Za-z0-9_.-]+", "[redacted]", detail)
                diagnostics = (diagnostics + [detail])[-3:]
            if event.get("type") == "turn.completed":
                calls += 1
                usage = event.get("usage", {})
                observed = sum(usage.get(key, 0) for key in ("input_tokens", "output_tokens"))
                if usage:
                    tokens = (tokens or 0) + observed
                if token_ceiling is not None and tokens is not None and tokens >= token_ceiling:
                    status = "observed-token-budget-exhausted"
                    break
            item = event.get("item", {})
            if event.get("type") == "item.completed" and item.get("type") == "command_execution":
                command_text = item.get("command", "")
                if "agentic-workspace" in command_text and "start" in command_text and len(operating_calls) < 16:
                    operating_calls.append(
                        {
                            "command": command_text[:8192],
                            "exit_code": item.get("exit_code"),
                            "output": item.get("aggregated_output", "")[:16384],
                        }
                    )
            if event.get("type") == "item.completed" and item.get("type") == "agent_message":
                message = item.get("text")
        else:
            status = "timeout"
    finally:
        finished.set()
        # Stop the sandbox actor even when the host sbx process has already exited.
        try:
            stop()
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=10)
    claim = None
    if message:
        try:
            claim = json.loads(message)
        except ValueError:
            pass
    return {
        "status": status,
        "claim": claim,
        "tokens": tokens,
        "cost": None,
        "calls": calls,
        "diagnostics": diagnostics,
        "operating_calls": operating_calls,
        "token_ceiling": token_ceiling,
        "budget_enforcement": "wall-time-output" + ("-and-observed-token-stop" if token_ceiling is not None else ""),
    }


class CodexActor:
    def __init__(self, *, model, reasoning, seconds, token_ceiling=None, billing="subscription", session_limit=3):
        if billing not in {"subscription", "metered"} or (billing == "metered" and not token_ceiling):
            raise ValueError("Metered execution requires an explicit observed token threshold")
        if not 1 <= session_limit <= 3 or not 1 <= seconds <= 900:
            raise ValueError("At most three sessions of at most fifteen minutes are allowed")
        self.model, self.reasoning = model, reasoning
        self.seconds, self.token_ceiling = seconds, token_ceiling
        self.billing, self.session_limit, self.sessions_started = billing, session_limit, 0
        self.observations = []
        self.source_sha256 = SOURCE_SHA256

    def session(self, work, prompt):
        if self.sessions_started >= self.session_limit:
            raise ValueError("Session budget exhausted; no implicit retry")
        if self.billing != "subscription":
            raise ValueError("This Sandbox transport is configured for subscription OAuth only")
        consumer = work.consumer
        if not isinstance(consumer, SandboxConsumer):
            raise ValueError("Requested Codex Sandbox actor cannot execute on this native/Docker backend")
        consumer.restrict_actor()
        args = SimpleNamespace(sbx=consumer.sbx, sandbox_name=consumer.name, model=self.model, reasoning_effort=self.reasoning, exec_env=[])
        prompt += "\nReturn a JSON final answer with status (complete, incomplete or blocked) and reason. Report what actually happened."
        command = _codex_exec_command(
            args=args, prompt=prompt, sandbox_repo="/home/consumer/repo", sandbox_share_path="/home/consumer/final.json"
        )
        command = consumer.exec_command(command[3:])
        self.sessions_started += 1
        observation_start = len(consumer.product_receipts())
        result = bounded_codex(command, seconds=self.seconds, token_ceiling=self.token_ceiling, stop=consumer.stop_actor)
        receipts = consumer.product_receipts()[observation_start:]
        self.observations.append(
            {
                **result,
                "product_calls": receipts,
                "product_subject": getattr(consumer, "product_subject", None),
                "billing": self.billing,
                "model": self.model,
                "reasoning": self.reasoning,
                "provider_cli": consumer.observation["provider_cli"],
            }
        )
        consumer.verify_installation_unchanged()
        if result["status"] != "completed":
            raise RuntimeError("Codex execution " + result["status"])
        return result["claim"]

    def __call__(self, work, family, task):
        from consumer_journeys import (
            INDEPENDENT_NOTES,
            adoption_action,
            check_assessment,
            check_continuation_checkpoint,
            check_disabled_maintenance,
            check_preserved,
            check_removed,
            check_stale_rejection,
            validate_pointer_files,
        )

        if family not in {"first-contact", "continuation", "readoption", "maintenance", "interruption"}:
            raise ValueError("This family requires the paired-subject recipe")
        goals = {
            "first-contact": "Set up this repository using its installed Agentic Workspace, then ",
            "continuation": "Read the retained repository continuation and finish the task. Set up the installed Agentic Workspace as needed, then ",
        }
        # Package invocation is ordinary install guidance, never hidden setup
        # procedure, expected commands, owner requests or a pre-solved task.
        invocation = " ".join(work.consumer.command)
        prompt = goals.get(family, "") + task + "\nThe installed package is available through: " + invocation
        if family == "first-contact":
            return self.session(work, prompt)
        if family in {"readoption", "maintenance", "interruption"}:
            self.session(
                work,
                "Set up this repository using its installed Agentic Workspace. Preserve policy and notes. "
                + (task if family == "maintenance" else "Leave the port change unfinished for now.")
                + "\nInstalled package: "
                + invocation,
            )
            validate_pointer_files(work.files())
            if family == "readoption":
                for name, data in INDEPENDENT_NOTES.items():
                    work.write(name, data)
                before = work.files()
                self.session(
                    work,
                    "Remove the Agentic Workspace package integration using its supported public procedure. Preserve independently owned local, Memory and Planning notes, policy.md and notes.txt. Do not re-adopt it yet.\nInstalled package: "
                    + invocation,
                )
                check_removed(before, work.files())
                claim = self.session(
                    work,
                    "Re-adopt the installed Agentic Workspace, preserving independent state, then "
                    + task
                    + "\nInstalled package: "
                    + invocation,
                )
                check_preserved(before, work.files(), INDEPENDENT_NOTES)
                return claim
            if family == "maintenance":
                check_assessment(work)
                work.write(".agentic-workspace/config.toml", b"[workspace]\nenabled = false\n")
                work.remove(".agentic-workspace/local/.gitignore")
                before = work.files()
                claim = self.session(
                    work,
                    "The workspace is deliberately disabled, and its local ignore boundary is missing. Perform supported setup maintenance to repair that boundary while preserving disabled policy and the completed port change. Assess setup concerns through the public package without claiming unobserved capabilities.\nInstalled package: "
                    + invocation,
                )
                check_disabled_maintenance(before, work.files())
                return claim
            action = adoption_action(work, "remove")
            original = work.files()["AGENTS.md"]
            work.write("AGENTS.md", original + b"\nConcurrent repository-owned instruction.\n")
            # Exercise the stale source guard through the same public negative as
            # the deterministic driver. The agent gets only the resulting repo.
            check_stale_rejection(work, action)
            claim = self.session(
                work,
                "An interrupted integration removal was rejected because repository instructions changed concurrently. Recover from the current repository state and "
                + task
                + "\nInstalled package: "
                + invocation,
            )
            if b"Concurrent repository-owned instruction." not in work.files()["AGENTS.md"]:
                raise ValueError("Recovery discarded concurrent repository instructions")
            return claim
        self.session(
            work,
            "Begin this two-step task: set up the installed Agentic Workspace and change settings.json to port 8081. "
            "Leave the README update for a replacement agent and record what remains in CONTINUE.md. Preserve repository policy and notes. "
            "The installed package is available through: " + invocation,
        )
        retained = work.files()
        check_continuation_checkpoint(retained)
        retained = portable_continuation(retained)
        source = work.consumer
        replacement = SandboxConsumer(source.subject, source.profile, source.target, source.template, source.scratch, source.sbx)
        from consumer_journeys import Workspace

        with replacement:
            replacement.install()
            fresh = Workspace(replacement)
            fresh.restore(retained)
            if fresh.files() != retained:
                raise ValueError("Fresh continuation transfer differs from portable repository state")
            source.observation["continuation_transfer"] = "repository-only-no-machine-local-state"
            claim = self.session(
                fresh,
                "Continue the repository task from its retained files; there is no earlier conversation. "
                + task
                + "\nThe installed package is available through: "
                + " ".join(replacement.command),
            )
            exported = fresh.files()
        return {"claim": claim, "exported": exported}
