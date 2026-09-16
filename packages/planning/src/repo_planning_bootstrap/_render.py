from __future__ import annotations

GENERATED_DOC_NOTICE = "> GENERATED STATIC ROUTING ADAPTER. Do not edit manually. Rerender with `python scripts/render_agent_docs.py`."


def render_quickstart() -> str:
    return f"""<!-- GENERATED FILE: do not edit manually. -->
# Agent Quickstart

{GENERATED_DOC_NOTICE}

Read `AGENTS.md`, then `.agentic-workspace/skills/workspace-startup/SKILL.md`.
Use the configured native `start --target . --task \"<task>\" --format json` when
current owner information is needed. Follow selected owner requests and skills.
Direct work stays direct. Planning continuity, relation, custody and mutations
remain with the current Planning owner. Verification owns proof and claims.
No-runtime reading follows the startup skill and `.agentic-workspace/READING.json`;
repository bytes cannot establish live authority.
"""


def render_routing() -> str:
    return f"""<!-- GENERATED FILE: do not edit manually. -->
# Agent Routing

{GENERATED_DOC_NOTICE}

Use `AGENTS.md` and the canonical workspace startup skill. Select specialized
procedure through current semantic routes; do not maintain copied capability or
command lists. Use current native Planning relation/posture results before
choosing durable continuity. No helper supplies mutation or completion authority.
"""
