from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("agent manifest must be a JSON object")
    return payload


def render_quickstart(manifest: dict[str, Any]) -> str:
    bootstrap = manifest.get("bootstrap", {})
    routing = manifest.get("routing", {})
    skills = manifest.get("skills", {})

    lines: list[str] = []
    lines.append("# Agent Quickstart")
    lines.append("")
    lines.append("Fast path for autonomous agents working on this repo.")
    lines.append("")
    lines.append("## First reads")
    lines.append("")
    for path in bootstrap.get("first_reads", []):
        lines.append(f"- `{path}`")
    lines.append("")

    first_queries = bootstrap.get("first_queries", [])
    if isinstance(first_queries, list) and first_queries:
        lines.append("## First queries")
        lines.append("")
        for item in first_queries:
            lines.append(f"- {item}")
        lines.append("")

    surface_roles = bootstrap.get("surface_roles", [])
    if isinstance(surface_roles, list) and surface_roles:
        lines.append("## Surface roles")
        lines.append("")
        for item in surface_roles:
            lines.append(f"- {item}")
        lines.append("")

    conditional_reads = bootstrap.get("conditional_reads", [])
    if isinstance(conditional_reads, list) and conditional_reads:
        lines.append("## Conditional reads")
        lines.append("")
        for item in conditional_reads:
            lines.append(f"- {item}")
        lines.append("")

    small_task_mode = bootstrap.get("small_task_mode", [])
    if isinstance(small_task_mode, list) and small_task_mode:
        lines.append("## Small-task mode")
        lines.append("")
        for item in small_task_mode:
            lines.append(f"- {item}")
        lines.append("")

    plan_threshold = bootstrap.get("plan_threshold", [])
    if isinstance(plan_threshold, list) and plan_threshold:
        lines.append("## When to create a plan")
        lines.append("")
        for item in plan_threshold:
            lines.append(f"- {item}")
        lines.append("")

    lines.append("## Source of truth")
    lines.append("")
    lines.append("- Active planning state: `.agentic-workspace/planning/state.toml`")
    lines.append("- Active feature plans: `docs/execplans/`")
    lines.append("- Archived plans: `docs/execplans/archive/`")
    lines.append("- Compact summary: `agentic-workspace summary --format json`")
    lines.append("- Machine-readable routing: `.agentic-workspace/planning/agent-manifest.json`")
    lines.append("")

    validation_flow = bootstrap.get("validation_flow", [])
    if isinstance(validation_flow, list) and validation_flow:
        lines.append("## Validation flow")
        lines.append("")
        for item in validation_flow:
            lines.append(f"- {item}")
        lines.append("")

    completion_reminders = bootstrap.get("completion_reminders", [])
    if isinstance(completion_reminders, list) and completion_reminders:
        lines.append("## Completion reminders")
        lines.append("")
        for item in completion_reminders:
            lines.append(f"- {item}")
        lines.append("")

    generated_surfaces = bootstrap.get("generated_surfaces", [])
    if isinstance(generated_surfaces, list) and generated_surfaces:
        lines.append("## Generated surfaces")
        lines.append("")
        for item in generated_surfaces:
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


def render_routing(manifest: dict[str, Any]) -> str:
    bootstrap = manifest.get("bootstrap", {})
    routing = manifest.get("routing", {})

    lines: list[str] = []
    lines.append("# Agent Routing")
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
