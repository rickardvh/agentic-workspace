# Execution and Milestone Flow Contract

This contract defines how active work moves from intent to completion, including milestone sequencing, resumability, and follow-through.

## Core Flow

1. **Intent Continuity**: Every active slice must belong to a larger intended outcome.
2. **Active Milestone**: Work happens in bounded, ready-to-execute milestones.
3. **Immediate Next Action**: The next safe step is always explicit and small.
4. **Validation and Proof**: Success is defined by narrow, verifiable criteria.
5. **Closure and Continuity**: Finished work must capture any required continuation and an explicit closure decision before archive.

---

## 1. Intent and Resumability

### Intent Continuity
Every execution slice must record:
- **Larger intended outcome**: The broad goal this work contributes to.
- **Slice completion of larger outcome**: Whether this specific slice finishes the parent goal.
- **Continuation surface**: Where the next slice or follow-on work belongs.

### System Intent
- **Authority**: The larger intended outcome stays above the bounded slice.
- **Bounded reinterpretation**: Agents may narrow means and first-slice scope, but not silently replace the confirmed outcome.
- **Recoverability**: Compact report/summary paths should answer whether the larger outcome is closed and where continuation lives now.

### Resumable Execution
Execution is resumable by default. If a task is interrupted, the checked-in state should be sufficient to restart:
- **Environment and State Recovery**: Use `agentic-workspace report` and `summary` to recover current context.
- **Intent Recovery**: Use the `Intent Continuity` section of the active plan.
- **Milestone Progress**: Use the `Active Milestone` and `Drift Log` to see what was tried and what remains.

---

## 2. Milestone Management

### Active Milestone
The active milestone must be:
- **Status**: `in-progress`, `ready`, or `blocked`.
- **Scope**: A bounded set of changes that can be completed in one or two sessions.
- **Ready**: Explicit signal that work can begin.

### Immediate Next Action
- Must be a single, concrete, and verifiable next step.
- Should avoid vague verbs like "continue" or "fix".
- Updated after every turn to ensure the handoff is always fresh.

---

## 3. Delegated Judgment and Workflow

### Delegated Judgment
Agents have bounded initiative to:
- Choose the best local means (tools, paths, narrow tests).
- Tighten validation.
- Select skills or registry-backed workflows.

**Escalation is required** when:
- The requested solution changes the intended outcome.
- The path is blocked or violates a stable contract.
- Confidence drops below the point where silent continuation is defensible.

### Orchestrator-Worker Handoff
When a stronger planner delegates work to a smaller or separate executor:
- **Contract Source**: Derive the handoff from `agentic-planning-bootstrap handoff --format json`.
- **Agent-Agnostic**: The handoff should not prescribe a specific executor model or brand.
- **Write Scope**: The worker's assigned scope must be explicit and narrow.
- **Execution Bounds**: Keep allowed paths, max-changed-file guidance, required validation, and ask-before-refactor thresholds close to the active plan rather than in chat-only instructions.
- **Stop Conditions**: Make "stop and escalate" explicit enough that a weaker or external executor can stop cheaply when scope, proof, or interpretation boundaries are reached.
- **Return-With Residue**: The handoff should name the minimum execution-run and finished-run-review residue the executor must return so later review does not have to reconstruct the run from scratch.

### Intent Interpretation Review
When a plan narrows a literal request into a more concrete bounded slice:
- keep the literal request visible
- record the inferred intended outcome
- record the chosen concrete "what"
- keep the interpretation distance explicit
- add one short review cue for when that interpretation should be corrected

This is a compact review surface, not a reasoning trace.

### Execution-Run Residue
Delegated execution should leave one compact per-run residue inside the active plan:
- run status
- executor
- handoff source
- what happened
- scope touched
- changed surfaces
- validations run
- result for continuation
- next step

This residue should be enough for pause/resume, returned-run review, and cheap correction without becoming a full trace system.
Use `scope touched` for the bounded intended scope and `changed surfaces` for the compact actual-change answer the reviewer should not have to reconstruct from broad diff reading.

### Finished-Run Review
When delegated work returns:
- review scope respected?
- review proof status
- review whether the intended outcome was served
- record the misinterpretation risk
- record the follow-on decision

Keep this review compact and decision-supporting. It complements proof and intent-satisfaction review; it does not replace them.

---

## 4. Closure and Follow-Through

### Iterative Follow-Through
Active work often leaves "residue" (follow-up tasks, cleanup, minor drift).
- **Follow-Through Section**: Record minor, same-thread tasks that should be finished before the plan is archived.
- **Convergence Rule**: If a task remains after the main milestone is complete, it belongs in follow-through or must be promoted to a new milestone/plan.

### Required Continuation
Before archiving a completed slice that belongs to an unfinished larger outcome:
- **Required Follow-on**: Explicitly state "yes" if more work is needed for the larger goal.
- **Next Owner**: Name the surface (e.g. `roadmap` in `.agentic-workspace/planning/state.toml` or a new plan) that owns the continuation.
- **Activation Trigger**: State what signal (e.g. "human review", "CI success") triggers the next slice.

### Closure Check
Before archiving a completed slice:
- **Slice Status**: Record that the bounded slice itself is complete.
- **Larger-Intent Status**: Record whether the broader goal is closed, partial, or still open.
- **Closure Decision**: Use `archive-and-close` only when the larger intent is actually satisfied; use `archive-but-keep-lane-open` when the slice is complete but the larger intent remains open.
- **Evidence and Reopen Trigger**: Record why the decision is honest, what evidence carries forward, and what should trigger reopening or follow-on.

### Execution Summary
The final state before archive must include:
- **Captured Outcome**: What was actually accomplished.
- **Unfinished Detail**: What was deferred or moved to a different owner.
- **Stable References**: Links to key decisions or artifacts.

---

## 5. Relationship to Tooling

- `agentic-workspace summary --format json`: Compact machine-readable state recovery.
- `agentic-planning-bootstrap handoff --format json`: Derived worker contract.
- `agentic-workspace report --target ./repo --format json`: Combined workspace status.
- `agentic-workspace doctor --target ./repo`: Run deep diagnostics and planning hygiene checks.
