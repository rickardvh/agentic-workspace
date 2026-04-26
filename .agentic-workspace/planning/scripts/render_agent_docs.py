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
    lines.append("Generated, non-authoritative helper. It points to compact query surfaces and owns no workflow truth.")
    lines.append("")
    lines.append("## Route")
    lines.append("")
    lines.append("- Read `AGENTS.md` first.")
    lines.append("- Run `uv run agentic-workspace start --format json` for compact startup context.")
    lines.append("- Run `uv run agentic-workspace summary --format json` only when active planning or roadmap state matters.")
    lines.append("- Run `uv run agentic-workspace preflight --format json` only when you need bundled takeover or recovery context.")
    lines.append("- Run `uv run agentic-workspace report --target . --format json` when you need health, warnings, or section hints.")
    lines.append("")
    lines.append("## Constraints")
    lines.append("")
    lines.append("- This file is a generated static adapter, not a doctrine or state owner.")
    lines.append("- Do not bulk-read all planning surfaces; follow compact query results to the one needed file.")
    lines.append("- Keep changing operational truth in structured/queryable surfaces, not in this helper.")
    return "\n".join(lines) + "\n"


def render_routing(_manifest: dict) -> str:
    lines: list[str] = []
    lines.append("<!-- GENERATED FILE: do not edit manually. -->")
    lines.append("")
    lines.append("# Agent Routing")
    lines.append("")
    lines.append(GENERATED_DOC_NOTICE)
    lines.append("")
    lines.append("Generated, state-free routing helper. Use compact commands for current truth.")
    lines.append("")
    lines.append("## Precedence")
    lines.append("")
    lines.append("1. Explicit user request.")
    lines.append("2. Active execplan when `uv run agentic-workspace summary --format json` reports one.")
    lines.append("3. `AGENTS.md` and the nearest package-local `AGENTS.md` for the files being edited.")
    lines.append("4. Repo docs explicitly referenced by the active route.")
    lines.append("")
    lines.append("## Compact Queries")
    lines.append("")
    lines.append("- `uv run agentic-workspace start --format json` for ordinary compact startup context.")
    lines.append("- `uv run agentic-workspace preflight --format json` for bundled takeover or recovery context.")
    lines.append("- `uv run agentic-workspace summary --format json` for active planning, queue, proof, or continuation.")
    lines.append("- `uv run agentic-workspace config --target . --format json` for configured entrypoint, posture, or obligations.")
    lines.append("- `uv run agentic-workspace report --target . --format json` for health, warnings, and selectors to deeper detail.")
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
