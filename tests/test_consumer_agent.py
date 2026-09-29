"""Transport controls are deterministic proof, never live-provider acceptance."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/tooling/release"))
sys.path.insert(0, str(ROOT / "src/tooling/model-cli-harness"))
from consumer_agent import CodexActor, SandboxConsumer, bounded_codex, portable_continuation  # noqa: E402


def test_fresh_machine_continuation_excludes_local_custody():
    portable = {"CONTINUE.md": b"Finish README", "settings.json": b'{"port":8081}', ".agentic-workspace/adoption.json": b"{}"}
    local = {
        ".agentic-workspace/local/host-note.txt": b"source-machine-sentinel",
        ".agentic-workspace/local/custody/effect.json": b"secret",
    }
    assert portable_continuation(portable | local) == portable
    assert portable_continuation({".agentic-workspace/local-policy.md": b"keep"}) == {".agentic-workspace/local-policy.md": b"keep"}


def test_containment_challenges_actor_auth_file(monkeypatch):
    import consumer_agent

    commands = []
    consumer = object.__new__(SandboxConsumer)
    consumer.sbx, consumer.name, consumer.observation = "sbx", "test-owned-sandbox", {}
    monkeypatch.setattr(consumer_agent, "run", lambda *args, **kwargs: None)

    def execute(argv):
        commands.append(argv)
        from types import SimpleNamespace

        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(consumer, "exec", execute)
    consumer.restrict_actor()
    assert 'test ! -e "$CODEX_HOME/auth.json"' in commands[-1][-1]
    assert "OPENAI_API_KEY|CODEX_API_KEY" in commands[-1][-1]


def test_subscription_records_unknown_cost_without_requiring_tokens():
    stopped = []
    event = {"type": "item.completed", "item": {"type": "agent_message", "text": '{"status":"complete"}'}}
    result = bounded_codex([sys.executable, "-c", "print(" + repr(json.dumps(event)) + ")"], seconds=10, stop=lambda: stopped.append(True))
    assert result["status"] == "completed"
    assert result["claim"] == {"status": "complete"}
    assert result["tokens"] is None and result["cost"] is None
    assert result["budget_enforcement"] == "wall-time-output"
    assert stopped == [True]


def test_observed_usage_stops_process_and_preserves_overrun():
    stopped = []
    event = {"type": "turn.completed", "usage": {"input_tokens": 70, "output_tokens": 40}}
    result = bounded_codex(
        [sys.executable, "-u", "-c", "import time; print(" + repr(json.dumps(event)) + "); time.sleep(30)"],
        seconds=10,
        token_ceiling=100,
        stop=lambda: stopped.append(True),
    )
    assert result["status"] == "observed-token-budget-exhausted"
    assert result["tokens"] == 110
    assert stopped == [True]


def test_timeout_stops_actor_without_completion():
    stopped = []
    result = bounded_codex([sys.executable, "-c", "import time; time.sleep(30)"], seconds=1, stop=lambda: stopped.append(True))
    assert result["status"] == "timeout"
    assert result["claim"] is None
    assert stopped == [True]


def test_metered_execution_requires_explicit_threshold():
    with pytest.raises(ValueError, match="Metered"):
        CodexActor(model="gpt-5.6-luna", reasoning="medium", seconds=900, billing="metered")


def test_exhausted_session_budget_prevents_transport():
    actor = CodexActor(model="gpt-5.6-luna", reasoning="medium", seconds=900)
    actor.sessions_started = 3
    with pytest.raises(ValueError, match="Session budget exhausted"):
        actor.session(None, "No fourth session")


@pytest.mark.parametrize("seconds,session_limit", [(901, 3), (900, 4), (0, 3)])
def test_rejects_unbounded_session_configuration(seconds, session_limit):
    with pytest.raises(ValueError):
        CodexActor(model="gpt-5.6-luna", reasoning="medium", seconds=seconds, session_limit=session_limit)


@pytest.mark.parametrize(
    "template", ["docker/sandbox-templates:codex", "docker.io/docker/sandbox-templates:codex-docker@sha256:" + "a" * 64]
)
def test_unpinned_or_docker_privileged_template_rejected_before_creation(template, tmp_path):
    with pytest.raises(ValueError, match="immutable non-Docker"):
        SandboxConsumer(None, "standalone", "x86_64-unknown-linux-gnu", template, tmp_path)


def test_actor_command_uses_distinct_uid_private_home_and_no_inherited_credentials():
    consumer = object.__new__(SandboxConsumer)
    consumer.sbx, consumer.name = "sbx", "test-owned-sandbox"
    command = consumer.exec_command(["codex", "exec", "a prompt; with shell syntax $(echo secret)"])
    assert command[command.index("--user") + 1] == "10002:10002"
    assert "env -i " in command[-5]
    assert "GH_TOKEN" not in command[-5] and "SSH_AUTH_SOCK" not in command[-5]
    assert command[-1] == "a prompt; with shell syntax $(echo secret)"


def test_provider_error_retained_without_bearer_or_endpoint():
    event = {"type": "error", "message": "401 Unauthorized https://example.invalid/token?secret=value Bearer fake-secret"}
    result = bounded_codex(
        [sys.executable, "-c", "print(" + repr(json.dumps(event)) + "); raise SystemExit(1)"], seconds=10, stop=lambda: None
    )
    assert result["status"] == "provider-or-agent-failure"
    assert result["diagnostics"] == ["401 Unauthorized [endpoint] [redacted]"]


def test_spoofed_tool_output_never_becomes_product_evidence():
    value = {"activation": {"kind": "agentic-workspace/activation/v1"}, "material": {"summary": "x" * 20000}, "reentry": {"task": "task"}}
    event = {
        "type": "item.completed",
        "item": {
            "type": "command_execution",
            "command": "./agentic-workspace start",
            "exit_code": 0,
            "aggregated_output": json.dumps(value),
        },
    }
    code = "import json; print(json.dumps(" + repr(event) + "))"
    result = bounded_codex([sys.executable, "-c", code], seconds=10, stop=lambda: None)
    assert "operating_results" not in result
    assert "product_calls" not in result
    assert len(result["operating_calls"][0]["output"]) == 16384
    assert result["command_output_bytes"] == len(json.dumps(value).encode())
    assert result["command_trace"][0]["output_bytes"] == result["command_output_bytes"]
    assert "unknown" in result["measurement_boundary"]


@pytest.mark.parametrize("extra", ["stdout", "executable", "subject", "exit_code"])
def test_product_boundary_rejects_caller_authored_receipts(extra):
    from consumer_product_boundary import validate_request

    with pytest.raises(ValueError, match="Only argv and stdin"):
        validate_request({"argv": ["start"], "stdin": "", extra: "fabricated"})


def test_product_budget_rejection_drains_request_and_retains_controller_failure(tmp_path, monkeypatch):
    import socket
    from concurrent.futures import ThreadPoolExecutor

    import consumer_product_boundary as boundary

    monkeypatch.setattr(boundary, "ROOT", tmp_path)
    (tmp_path / "failure.json").write_text("null")
    subject = {"sha256": "fixed-subject"}
    invoked = []

    def invoke(value, config):
        invoked.append(value)
        return {"subject": config["subject"], "stdout": "{}", "stderr": "", "exit_code": 0}

    monkeypatch.setattr(boundary, "invoke", invoke)

    def exchange(total):
        client, server = socket.socketpair()

        def serve():
            with server:
                return boundary.serve_connection(server, {"subject": subject}, total)

        with client, ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(serve)
            client.sendall(json.dumps({"argv": ["start", "--input", "-"], "stdin": "x" * 2721}).encode())
            client.shutdown(socket.SHUT_WR)
            return boundary.receive(client), future.result(timeout=5)

    reply, total = exchange(127)
    assert reply["exit_code"] == 0 and total == 128 and len(invoked) == 1
    receipts = (tmp_path / "receipts.jsonl").read_bytes()
    reply, total = exchange(total)
    assert reply == {"stdout": "", "stderr": "Product observer: Product observation call budget exhausted\n", "exit_code": 75}
    assert total == 128 and len(invoked) == 1
    assert (tmp_path / "receipts.jsonl").read_bytes() == receipts
    failure = (tmp_path / "failure.json").read_bytes()
    assert json.loads(failure) == {
        "kind": "agentic-workspace/product-observer-failure/v1",
        "subject": subject,
        "reason": "Product observation call budget exhausted",
        "stage": "admission",
        "exit_code": 75,
    }
    assert exchange(total)[0] == reply
    assert (tmp_path / "failure.json").read_bytes() == failure
