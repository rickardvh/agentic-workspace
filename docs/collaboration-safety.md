# Collaboration Safety

Agentic Workspace is git-native and collaboration-aware, but not concurrency-proof.

It does not hide agent state in a service, lock manager, database, or CRDT. The package makes agent operating state participate in ordinary git review and merge workflows. That gives visibility and portability, but shared active-state files still need to stay small, bounded, and quickly closed or distilled.

Use these rules when multiple agents or contributors are working through git. Use `docs/maintainer/maintainer-commands.md` for command lookup; this page is only for concurrent-edit and merge-safety rules.

## Collaboration Model

What is robust:

- Checked-in state uses normal branch, diff, review, and merge semantics.
- Active work can be isolated in feature-scoped execplan files.
- Durable repo knowledge can live in Memory notes or canonical docs instead of chat history.
- Generated and managed surfaces should be repairable from canonical sources when the source authority is clear.
- `agentic-workspace start`, `preflight`, `summary`, `report`, and `doctor` expose compact collaboration and recovery signals before broad file reads.

What is still fragile:

- `.agentic-workspace/planning/state.toml` is a shared hot file because it selects live future work.
- Two branches editing the same active execplan will conflict like any same-file collaboration.
- Durable Memory notes can conflict when several branches update one broad note.
- Config and ownership conflicts need human or strong-review judgment because they change policy.
- JSON and TOML are reviewable, but manual merge resolution can still be awkward.

The practical rule is:

```text
Agentic Workspace is git-native and collaboration-aware, not multi-writer safe.
```

- Keep `.agentic-workspace/memory/repo/current/` out of ordinary active-state flow. Use it only for optional routing calibration or migration review; durable facts move into memory/docs and active state stays in planning/status.
- Archive execplans aggressively once they stop affecting future execution.
- Prefer feature-scoped execplan files over growing shared hot files.
- Edit canonical docs directly; edit module-managed `.agentic-workspace/` planning or memory surfaces only through their owning package or managed source.
- Do not edit generated routing docs under `tools/` by hand; update the manifest source and rerender.
- Keep the package-managed memory install authoritative for monorepo operation, and keep planning state authoritative in `.agentic-workspace/planning/state.toml` through the planning package.
- Let local pre-commit hooks handle formatting and lint, and let master-bound commits run tests in the hook as well; keep broader test execution in CI or explicit validation runs.
- When pre-commit rewrites files, restage them and rerun the commit instead of fighting the formatter.
- Record meaningful follow-up work in planning or memory instead of leaving it in chat-only residue.

## Merge Recovery

When a merge touches Agentic Workspace surfaces:

1. Run `agentic-workspace doctor --target . --format json`.
2. If `repair_plan.status` is `safe-action-available`, inspect the primary action before applying it.
3. If conflict markers appear in `.agentic-workspace/config.toml`, `.agentic-workspace/OWNERSHIP.toml`, or `config.local.toml.example`, treat the conflict as policy review. Do not blindly regenerate these files.
4. If conflict markers appear in `.agentic-workspace/planning/state.toml`, preserve the intentional active/queued future work from both sides. Do not delete `state.toml` as the first move.
5. If conflict markers appear in an active execplan, preserve the bounded implementation contract before continuing. Do not replace it with a freehand plan unless the conflicting intent has been retained.
6. If conflict markers appear in Memory notes, preserve reusable durable knowledge and split the note when the same broad surface keeps colliding.
7. If a generated or derived surface is stale, identify the canonical source and rerender command before editing generated output by hand.

## Generated Surface Repair

Generated and derived surfaces are cheap to repair only when source authority is clear. Prefer this order:

- source schema, manifest, or package payload;
- package command that renders the managed or generated surface;
- generated output as inspection evidence only.

Use `agentic-workspace doctor --target . --format json` to find `repair_actions`, `manual_review_actions`, `stale_generated_surfaces`, and `repair_plan.primary_next_action`. Safe rerender actions should name the command and proof-after command. Manual-review actions mean the package cannot prove which side of a merge is authoritative.

Do not turn generated surfaces into a second handbook during conflict resolution. Repair the source, rerender, then review the resulting diff.

## Quick Boundary Checks

- Active-now sequencing or next step: planning.
- Durable invariant, rationale, or runbook: memory or canonical docs.
- Shared module workflow support under `.agentic-workspace/`: package-managed surface.
- Rendered `tools/` guidance: generated output, not source.

## Hot-File Pressure

Use compact diagnostics before closeout or push:

- `agentic-workspace summary --target . --profile compact --format json` exposes `planning_surface_health.collaboration_pressure`.
- `agentic-workspace report --target . --format json` exposes `branch_workflow_posture.shared_state_mutation_risk`.
- `agentic-memory report --target . --format json` exposes `merge_safety` when Memory is installed.

These are pressure signals, not locks. They tell an agent or reviewer when ordinary git collaboration risk is high enough to review, split, close, archive, rerender, or route durable residue before continuing.
