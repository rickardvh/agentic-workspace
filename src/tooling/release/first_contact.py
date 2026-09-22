"""One installed setup/startup journey reused by existing package consumers."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


def journey(command: list[str], target: Path, env: dict[str, str]) -> None:
    def run(*args: str) -> dict:
        result = subprocess.run([*command, *args], cwd=target, env=env, check=True, capture_output=True, text=True)
        return json.loads(result.stdout)

    proposal = run("setup", "--dry-run", "--format", "json")
    if proposal["status"] != "authorization-required" or (target / "AGENTS.md").exists():
        raise ValueError("Fresh installed setup did not provide a non-mutating proposal")
    applied = run("setup", "--yes", "--format", "json")
    if applied["effect_outcome"]["status"] != "committed":
        raise ValueError("Installed setup failed to commit")
    validate_pointer(target)
    if run("setup", "--format", "json")["status"] != "already-current":
        raise ValueError("Installed setup is not idempotent")
    # New process, ordinary task, installed procedure only; no adoption packet or
    # hidden source-checkout context is carried into the task.
    current = run("start", "--task", "Correct one documentation error", "--projection", "full", "--format", "json")
    if not current.get("semantic_routes"):
        raise ValueError("Fresh ordinary task cannot discover installed procedures")


def validate_pointer(target: Path) -> None:
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    begin = "<!-- agentic-workspace:workflow:start -->"
    end = "<!-- agentic-workspace:workflow:end -->"
    if agents.count(begin) != 1 or agents.count(end) != 1:
        raise ValueError("Installed startup fence is missing or ambiguous")
    fence = agents.split(begin)[1].split(end)[0]
    skill = ".agentic-workspace/skills/workspace-startup/SKILL.md"
    if skill not in fence or not (target / skill).is_file():
        raise ValueError("Installed startup pointer is missing or stale")
    provenance = json.loads((target / ".agentic-workspace/payload-provenance.json").read_text(encoding="utf-8"))
    if skill not in provenance["payload_files"]:
        raise ValueError("Installed startup skill is outside current payload identity")
    identity = json.loads((target / ".agentic-workspace/adoption.json").read_text(encoding="utf-8"))
    digest = "sha256:" + hashlib.sha256((target / skill).read_bytes()).hexdigest()
    if identity["package_files"].get(skill) != digest or identity["instruction_fence"] not in agents:
        raise ValueError("Installed startup body or fence differs from its adopted identity")
