# Routing and Entry Contract (Authoritative Routing Home)

This contract defines how to enter the repository, orient quickly, and pick the right execution lane.

## 1. Startup and First Contact

Use the Startup Router for a fresh entry:

1. **High-Efficiency Entry**: Use the [Cold-Start Protocol](cold-start-protocol.md) for a <3 turn activation.
2. **Configured Startup File**: Start from the configured repo startup file (default `AGENTS.md`).
3. **Startup Router**: Run `agentic-workspace start --task "<task>" --format json`, or `agentic-workspace implement --changed <paths> --task "<task>" --format json` when changed paths are already known.
4. **Routed Detail**: Use `summary`, `config`, `defaults`, `report`, or raw Planning files only when the router packet or explicit user request names that need.

### Tiny Safe Model

Ordinary work should begin from one small operating model:

- one startup entrypoint: `AGENTS.md` by default
- one Startup Router query: `agentic-workspace start --task "<task>" --format json`
- one rule for deeper reads: load broader prose or module-specific surfaces only when the router packet shows the task crosses a real boundary

Use [minimum-operating-model.md](minimum-operating-model.md) for the compact module-boundary and escalation-cue contract.

### Surface Roles
- `AGENTS.md`: Canonical repo startup and operating rules.
- `.agentic-workspace/planning/state.toml` (`todo.active_items`): Repo-owned active task queue and smallest near-term follow-ons.
- `.agentic-workspace/planning/state.toml` (`roadmap`): Repo-owned inactive long-horizon candidate work and promotion signals.
- `.agentic-workspace/planning/execplans/`: Active, sequencing-heavy execution contracts.
- `AGENTS.md`: Agent entrypoint router for external handoff and first-contact after bootstrap.
- `docs/agentic-workspace-install.md`: Detailed external install/adopt handoff instructions.

### External Install/Adopt Handoff
When an external agent is installing or adopting this repo:
- **Start Here**: Read `docs/agentic-workspace-install.md`.
- **Primary Command**: `agentic-workspace init --target ./repo --modules memory`.
- **Module Selection**: Choose the smallest explicit `--modules` set that fits, such as `memory`, `planning`, `verification`, or `planning,memory`.
- **Fallback Only**: Use `uvx` or `pipx run` only as an explicit temporary/debug fallback when the target repo has no installed CLI yet.
- **Handoff Artifacts**: Check for `.agentic-workspace/bootstrap-handoff.md` after bootstrap.
- **Orientation**: Return to the configured startup file (default `AGENTS.md`) after bootstrap is complete.

---

## 2. Routine Recovery Path

When restarting work or recovering state, prefer the compact path:

1. **Machine-Readable State**: Query `agentic-workspace summary` for the current milestone, next action, and drift log.
2. **Compact Prose**: Use `routing-contract.md` (this file) for stable route guidance and framing.
3. **Raw Detail**: Open `.agentic-workspace/planning/state.toml` or execplan prose only when the compact summary is insufficient.

---

## 3. Post-Bootstrap Jumpstart

After initial installation or when adopting an existing repository:

- **Setup Query**: Run `agentic-workspace setup --target ./repo --format json`.
- **Findings**: Setup findings are advisory. Promote them to `todo.active_items` only when they represent clear, actionable work.
- **Durable Residue**: Record setup results in memory or canonical docs, not as a permanent "findings" file.

---

## 4. Advanced Routing Rules

### Boundary-Triggered Discovery
- Escalate into workspace surfaces when startup order, lifecycle behavior, config, ownership, or combined workspace state is the real question.
- Escalate into planning when the task needs active sequencing, blockers, proof expectations, queue updates, or explicit continuation semantics.
- Escalate into memory when repo understanding should persist beyond the current slice instead of being rediscovered.

### Standing Intent
- **Precedence**: Intent from `agentic-workspace summary` or `config` supersedes broad prose.
- **Supersession**: Newer checked-in intent (e.g. in a plan) supersedes older roadmap candidates.

### Promotion and Escalation
- **Promotion**: Move work from `roadmap` to `todo.active_items` in `.agentic-workspace/planning/state.toml` when scope and dependencies are clear.
- **Escalation**: If the task exceeds local latitude or the current model's capability, use `.agentic-workspace/docs/capability-aware-execution.md` to select a stronger lane.

---

## 5. Query Mapping

| Question | Tool Command |
| --- | --- |
| What is the ordinary startup path? | `agentic-workspace defaults --section startup` |
| What is active right now? | `agentic-workspace summary --format json` |
| What is the combined workspace state? | `agentic-workspace report --target ./repo` |
| What are the candidate epics? | `agentic-workspace summary` (roadmap list) |
| What is the effective repo posture? | `agentic-workspace config --target ./repo` |
