from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MANAGED_ROOT = REPO_ROOT / ".agentic-workspace" / "planning"
MANIFEST_PATH = MANAGED_ROOT / "agent-manifest.json"
GENERATED_DOC_NOTICE = (
    "> GENERATED FILE. Do not edit manually. Update `.agentic-workspace/planning/agent-manifest.json` "
    "and rerender with `python scripts/render_agent_docs.py`."
)


def load_manifest(path: Path = MANIFEST_PATH) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("agent manifest must be a JSON object")
    return payload


def render_quickstart(manifest: dict) -> str:
    bootstrap = manifest.get("bootstrap", {})
    routing = manifest.get("routing", {})
    skills = manifest.get("skills", {})

    lines: list[str] = []
    lines.append("<!-- GENERATED FILE: do not edit manually. -->")
    lines.append("")
    lines.append("# Agent Quickstart")
    lines.append("")
    lines.append(GENERATED_DOC_NOTICE)
    lines.append("")
    lines.append("Fast path for autonomous agents working on this repo.")
    lines.append("")
    lines.append("## First reads")
    lines.append("")
    for path in bootstrap.get("first_reads", []):
        lines.append(f"- `{path}`")
    lines.append("")

    for title, key in (
        ("Conditional reads", "conditional_reads"),
        ("Small-task mode", "small_task_mode"),
        ("When to create a plan", "plan_threshold"),
        ("Source of truth", None),
        ("Validation flow", "validation_flow"),
        ("Completion reminders", "completion_reminders"),
        ("Generated surfaces", "generated_surfaces"),
    ):
        if key is None:
            lines.append("## Source of truth")
            lines.append("")
            lines.append(f"- Active queue and lightweight direct tasks: `{bootstrap.get('task_source_of_truth', 'TODO.md')}`")
            lines.append(f"- Active feature plans: `{bootstrap.get('active_plan_dir', 'docs/execplans/')}`")
            lines.append(f"- Archived plans: `{bootstrap.get('archived_plan_dir', 'docs/execplans/archive/')}`")
            lines.append(f"- Long-horizon planning: `{bootstrap.get('roadmap_source_of_truth', 'ROADMAP.md')}`")
            lines.append("- Machine-readable routing: `.agentic-workspace/planning/agent-manifest.json`")
            lines.append("")
            continue

        items = bootstrap.get(key, [])
        if isinstance(items, list) and items:
            lines.append(f"## {title}")
            lines.append("")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")

    lines.append("## Common task classes")
    lines.append("")
    if not routing:
        lines.append("- No task classes declared.")
    for task_name, payload in routing.items():
        if not isinstance(payload, dict):
            continue
        lines.append(f"- `{task_name}`")
        when = payload.get("when")
        prefer_when = payload.get("prefer_when")
        touches = payload.get("touches", [])
        commands = payload.get("commands", [])
        if isinstance(when, str) and when.strip():
            lines.append(f"  Use when: {when}")
        if isinstance(prefer_when, str) and prefer_when.strip():
            lines.append(f"  Prefer this route when: {prefer_when}")
        if isinstance(touches, list) and touches:
            lines.append("  Touches: " + ", ".join(f"`{path}`" for path in touches))
        if isinstance(commands, list) and commands:
            lines.append("  Validate: " + "; ".join(f"`{command}`" for command in commands))
    lines.append("")

    lines.append("## Skills")
    lines.append("")
    lines.append(f"- Repo development skills: `{skills.get('repo_dev_source_dir', 'tools/skills')}`")
    lines.append(f"- Shared memory workflow skills: `{skills.get('memory_source_dir', '.agentic-workspace/memory/skills')}`")
    repo_memory_source_dir = skills.get("repo_memory_source_dir")
    if isinstance(repo_memory_source_dir, str) and repo_memory_source_dir.strip():
        lines.append(f"- Repo-specific memory skills: `{repo_memory_source_dir}`")
    lines.append("")

    lines.append("## Core invariants")
    lines.append("")
    for invariant in manifest.get("invariants", []):
        lines.append(f"- {invariant}")
    return "\n".join(lines) + "\n"


def render_routing(manifest: dict) -> str:
    bootstrap = manifest.get("bootstrap", {})
    routing = manifest.get("routing", {})

    lines: list[str] = []
    lines.append("<!-- GENERATED FILE: do not edit manually. -->")
    lines.append("")
    lines.append("# Agent Routing")
    lines.append("")
    lines.append(GENERATED_DOC_NOTICE)
    lines.append("")
    lines.append("Focused routing reference derived from `.agentic-workspace/planning/agent-manifest.json`.")
    lines.append("")

    doc_precedence = bootstrap.get("doc_precedence", [])
    if isinstance(doc_precedence, list) and doc_precedence:
        lines.append("## Precedence")
        lines.append("")
        for item in doc_precedence:
            lines.append(f"- {item}")
        lines.append("")

    lines.append("## Task Routes")
    lines.append("")
    if not routing:
        lines.append("- No task routes declared.")
        return "\n".join(lines) + "\n"

    for task_name, payload in routing.items():
        if not isinstance(payload, dict):
            continue
        lines.append(f"### `{task_name}`")
        lines.append("")
        when = payload.get("when")
        prefer_when = payload.get("prefer_when")
        touches = payload.get("touches", [])
        commands = payload.get("commands", [])
        if isinstance(when, str) and when.strip():
            lines.append(f"- Use when: {when}")
        if isinstance(prefer_when, str) and prefer_when.strip():
            lines.append(f"- Prefer when: {prefer_when}")
        if isinstance(touches, list) and touches:
            lines.append("- Touches:")
            for path in touches:
                lines.append(f"  - `{path}`")
        if isinstance(commands, list) and commands:
            lines.append("- Validation:")
            for command in commands:
                lines.append(f"  - `{command}`")
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    manifest = load_manifest()
    outputs = {
        REPO_ROOT / "tools" / "agent-manifest.json": json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        REPO_ROOT / "tools" / "AGENT_QUICKSTART.md": render_quickstart(manifest),
        REPO_ROOT / "tools" / "AGENT_ROUTING.md": render_routing(manifest),
    }
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
