from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MANAGED_ROOT = REPO_ROOT / ".agentic-workspace" / "planning"
MANIFEST_PATH = MANAGED_ROOT / "agent-manifest.json"
GENERATED_DOC_NOTICE = (
    "> GENERATED STATIC ROUTING ADAPTER. Do not edit manually. Rerender with "
    "`python scripts/render_agent_docs.py`."
)


def load_manifest(path: Path = MANIFEST_PATH) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("agent manifest must be a JSON object")
    return payload


def render_quickstart(_manifest: dict) -> str:
    lines: list[str] = []
    lines.append("<!-- GENERATED FILE: do not edit manually. -->")
    lines.append("")
    lines.append("# Agent Quickstart")
    lines.append("")
    lines.append(GENERATED_DOC_NOTICE)
    lines.append("")
    lines.append("Static, non-authoritative entry table for agents that need one obvious next surface.")
    lines.append("")
    lines.append("## Start Here")
    lines.append("")
    lines.append("- Read `AGENTS.md` first.")
    lines.append("- Run `uv run agentic-workspace preflight --format json` for startup guidance plus active state.")
    lines.append("- Run `uv run agentic-workspace summary --format json` when active planning recovery is the question.")
    lines.append("- Run `uv run agentic-workspace defaults --section startup --format json` when startup order is the question.")
    lines.append("")
    lines.append("## Authority Table")
    lines.append("")
    lines.append("| Need | Use |")
    lines.append("| --- | --- |")
    lines.append("| ordinary repo startup | `AGENTS.md` |")
    lines.append("| compact startup/config state | `uv run agentic-workspace preflight --format json` |")
    lines.append("| active planning and continuation | `uv run agentic-workspace summary --format json` |")
    lines.append("| configured entrypoint/posture | `uv run agentic-workspace config --target . --format json` |")
    lines.append("| machine-readable routing mirror | `.agentic-workspace/planning/agent-manifest.json` |")
    lines.append("")
    lines.append("## Constraints")
    lines.append("")
    lines.append("- This file is a generated static adapter, not a doctrine or state owner.")
    lines.append("- Do not bulk-read all planning surfaces; follow compact query results to the one needed file.")
    lines.append("- Keep changing operational truth in structured/queryable surfaces, not in this helper.")
    lines.append("")
    lines.append("## Escalation Table")
    lines.append("")
    lines.append("| Boundary | First move |")
    lines.append("| --- | --- |")
    lines.append("| workspace startup, lifecycle, ownership, or config | `uv run agentic-workspace defaults --section startup --format json` |")
    lines.append("| planning sequence, blockers, proof, or continuation | `uv run agentic-workspace summary --format json` |")
    lines.append("| durable repo knowledge or repeated rediscovery | read `.agentic-workspace/memory/WORKFLOW.md` |")
    return "\n".join(lines) + "\n"


def render_routing(_manifest: dict) -> str:
    lines: list[str] = []
    lines.append("<!-- GENERATED FILE: do not edit manually. -->")
    lines.append("")
    lines.append("# Agent Routing")
    lines.append("")
    lines.append(GENERATED_DOC_NOTICE)
    lines.append("")
    lines.append("Static routing table for weak-agent discovery. It does not mirror active state.")
    lines.append("")
    lines.append("## Precedence")
    lines.append("")
    lines.append("1. Explicit user request.")
    lines.append("2. Active execplan when `uv run agentic-workspace summary --format json` reports one.")
    lines.append("3. `AGENTS.md` and the nearest package-local `AGENTS.md` for the files being edited.")
    lines.append("4. Repo docs explicitly referenced by the active route.")
    lines.append("")
    lines.append("## Routing Table")
    lines.append("")
    lines.append("| Situation | Route |")
    lines.append("| --- | --- |")
    lines.append("| startup order or first-contact routing | `uv run agentic-workspace defaults --section startup --format json` |")
    lines.append("| active work, queue, proof, or continuation | `uv run agentic-workspace summary --format json` |")
    lines.append("| startup guidance plus resolved config and active state | `uv run agentic-workspace preflight --format json` |")
    lines.append("| configured entrypoint, posture, or obligations | `uv run agentic-workspace config --target . --format json` |")
    lines.append("| combined workspace/module state | `uv run agentic-workspace report --target . --format json` |")
    lines.append("| task-specific package rules | nearest package-local `AGENTS.md` |")
    lines.append("")
    lines.append("## Boundaries")
    lines.append("")
    lines.append("- Keep mutable execution state in `.agentic-workspace/planning/state.toml` and active execplans.")
    lines.append("- Keep durable repo knowledge in memory or canonical docs, not in these generated adapters.")
    lines.append("- Keep this file state-free; rerendering should not expand it into a manifest mirror.")
    lines.append("")

    return "\n".join(lines) + "\n"


render_readme_entrypoints = render_quickstart


def main() -> int:
    manifest = load_manifest()
    outputs = {
        REPO_ROOT / "tools" / "agent-manifest.json": json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        REPO_ROOT / "tools" / "AGENT_QUICKSTART.md": render_quickstart(manifest),
        REPO_ROOT / "tools" / "AGENT_ROUTING.md": render_routing(manifest),
    }
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
