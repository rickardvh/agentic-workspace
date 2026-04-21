# Routing and Entry Contract (Authoritative Routing Home)

This contract defines how to enter the repository, orient quickly, and pick the right execution lane.

## 1. Startup and First Contact

Use the following order for a fresh entry:

1. **High-Efficiency Entry**: Use the [Cold-Start Protocol](cold-start-protocol.md) for a <3 turn activation.
2. **Configured Startup File**: Check `agentic-workspace config --target ./repo --format json` for the entrypoint (default `AGENTS.md`).
3. **Compact State**: Read `agentic-workspace summary --format json` first to see the compact planning and ownership state.
4. **Active Queue**: Read `.agentic-workspace/planning/state.toml` only when the summary shows active work that still needs raw queue detail.
5. **Compact Queries**: Before reading broad prose, use:
   - `agentic-workspace defaults --section startup --format json`: For startup order and surface roles.
   - `agentic-workspace report --target ./repo --format json`: For combined workspace/module status.

### Tiny Safe Model

Ordinary work should begin from one small operating model:

- one startup entrypoint: `AGENTS.md` by default
- one compact query path: `agentic-workspace defaults --section startup --format json`, `agentic-workspace config --target ./repo --format json`, and `agentic-workspace summary --format json`
- one rule for deeper reads: load broader prose or module-specific surfaces only when the task crosses a real boundary

Use [minimum-operating-model.md](minimum-operating-model.md) for the compact module-boundary and escalation-cue contract.

### Surface Roles
- `AGENTS.md`: Canonical repo startup and operating rules.
- `.agentic-workspace/planning/state.toml` (`todo.active_items`): Repo-owned active task queue and smallest near-term follow-ons.
- `.agentic-workspace/planning/state.toml` (`roadmap`): Repo-owned inactive long-horizon candidate work and promotion signals.
- `.agentic-workspace/planning/execplans/`: Active, sequencing-heavy execution contracts.
- `llms.txt`: Agent entrypoint router for external handoff and first-contact.
- `agent-installation.md`: Detailed external install/adopt handoff instructions.

### External Install/Adopt Handoff
When an external agent is installing or adopting this repo:
- **Primary Command**: `agentic-workspace init --target ./repo --preset full`.
- **Guest-Mode Command**: `agentic-workspace install --target ./repo --preset full --local-only`.
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
