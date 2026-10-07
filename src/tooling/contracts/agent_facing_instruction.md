---
paths:
  - AGENTS.md
  - '**/AGENTS.md'
  - .agentic-workspace/WORKFLOW.md
  - .agentic-workspace/instructions/*.md
  - .agentic-workspace/local/instructions/*.md
  - .agentic-workspace/skills/*.md
  - .agentic-workspace/skills/REGISTRY.json
  - .agentic-workspace/planning/skills/*.md
  - .agentic-workspace/planning/skills/REGISTRY.json
  - .agentic-workspace/memory/skills/*.md
  - .agentic-workspace/memory/skills/REGISTRY.json
  - .agentic-workspace/verification/skills/*.md
  - .agentic-workspace/verification/skills/REGISTRY.json
  - .agentic-workspace/fallback/*.md
  - tools/skills/*.md
  - tools/skills/REGISTRY.json
  - prompts/**
  - '**/prompts/**'
  - src/core/payload/**.md
  - src/core/payload/**/REGISTRY.json
  - src/core/src/native_adoption.rs
  - src/tooling/generate/generate_agent_interface.py
  - src/tooling/contracts/schemas/skill_spec.schema.json
---

<!-- GENERATED: edit src/tooling/contracts/agent_facing_writing.md or src/tooling/contracts/agent_facing_instruction.md and run the agent-interface generator. -->

{{writing_contract}}
## Application in this repository

This is the canonical writing guide for this repository's agent-facing material.
The path scope supplies it for the usual source locations. For agent-directed
text embedded elsewhere, follow the same guide when that text is the subject of
the change. It does not govern unrelated implementation code or require an AW
command merely to read or apply it. Human-facing documentation also follows the
[documentation style guide](../../docs/documentation-style-guide.md).
