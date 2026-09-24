"""Test-only transparent CLI transport with root-owned invocation receipts.

The server runs only the fixed admitted executable pair, as the unprivileged
consumer. Actors may request real calls, but cannot submit outputs or edit the
server, subject, socket directory or receipts. No product semantics live here.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path("/opt/aw-observer")
LIMIT = 262144


def receive(connection):
    data = bytearray()
    while chunk := connection.recv(65536):
        data.extend(chunk)
        if len(data) > 4 * LIMIT:
            raise ValueError("Product boundary frame exceeds bound")
    return json.loads(data)


def validate_request(value):
    if not isinstance(value, dict) or set(value) != {"argv", "stdin"}:
        raise ValueError("Only argv and stdin are accepted")
    if (
        not isinstance(value["argv"], list)
        or len(value["argv"]) > 64
        or any(not isinstance(arg, str) or len(arg) > 8192 or "\0" in arg for arg in value["argv"])
        or not isinstance(value["stdin"], str)
        or len(value["stdin"].encode()) > LIMIT
    ):
        raise ValueError("Invalid bounded product input")


def invoke(value, config):
    validate_request(value)
    # Fixed absolute executable, fixed cwd, no shell and no inherited credentials.
    # The root-owned pair cannot be replaced even temporarily by the actor.
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as errors:
        process = subprocess.run(
            [str(ROOT / "subject/agentic-workspace"), *value["argv"]],
            input=value["stdin"].encode(),
            stdout=out,
            stderr=errors,
            cwd="/home/consumer/repo",
            env={"PATH": "/usr/bin:/bin", "HOME": "/home/consumer", "TMPDIR": "/home/consumer/tmp"},
            user=10002,
            group=10002,
            extra_groups=[],
            timeout=60,
        )
        if out.tell() > LIMIT or errors.tell() > LIMIT:
            raise ValueError("Product output exceeds observation bound")
        out.seek(0)
        errors.seek(0)
        return {
            "kind": "agentic-workspace/observed-installed-call/v1",
            "subject": config["subject"],
            "argv": value["argv"],
            "stdin_sha256": hashlib.sha256(value["stdin"].encode()).hexdigest(),
            "stdout": out.read().decode(),
            "stderr": errors.read().decode(),
            "exit_code": process.returncode,
        }


def server():
    if os.getuid() != 0:
        raise ValueError("Observer requires trusted controller custody")
    config = json.loads((ROOT / "config.json").read_text())
    total = 0
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
        listener.bind(str(ROOT / "socket"))
        os.chmod(ROOT / "socket", 0o666)
        listener.listen(4)
        while True:
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(65)
                try:
                    if total >= 128:
                        raise ValueError("Product observation call budget exhausted")
                    receipt = invoke(receive(connection), config)
                    # Flush the exact result before returning it to the caller.
                    with (ROOT / "receipts.jsonl").open("a", encoding="utf-8") as stream:
                        stream.write(json.dumps(receipt) + "\n")
                    total += 1
                    reply = {key: receipt[key] for key in ("stdout", "stderr", "exit_code")}
                except (ValueError, OSError, subprocess.SubprocessError) as error:
                    reply = {"stdout": "", "stderr": f"Product observer: {error}\n", "exit_code": 75}
                try:
                    connection.sendall(json.dumps(reply).encode())
                except (BrokenPipeError, ConnectionResetError):
                    pass


def client():
    value = {"argv": sys.argv[2:], "stdin": sys.stdin.read(LIMIT + 1) if not sys.stdin.isatty() else ""}
    validate_request(value)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(70)
        connection.connect(str(ROOT / "socket"))
        connection.sendall(json.dumps(value).encode())
        connection.shutdown(socket.SHUT_WR)
        reply = receive(connection)
    sys.stdout.write(reply["stdout"])
    sys.stderr.write(reply["stderr"])
    raise SystemExit(reply["exit_code"])


if __name__ == "__main__":
    if sys.argv[1] == "server":
        server()
    elif sys.argv[1] == "client":
        client()
    else:
        raise SystemExit("Unknown product boundary mode")
