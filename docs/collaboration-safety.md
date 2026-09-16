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

Resolve this concern through the canonical startup skill and the current owner request returned by `start`. The [native CLI catalogue](/docs/reference/cli-catalogue.md) defines executable commands.

## Generated Surface Repair

Generated and derived surfaces are cheap to repair only when source authority is clear. Prefer this order:

- source schema, manifest, or package payload;
- package command that renders the managed or generated surface;
- generated output as inspection evidence only.

Resolve this concern through the canonical startup skill and the current owner request returned by `start`. The [native CLI catalogue](/docs/reference/cli-catalogue.md) defines executable commands.

Do not turn generated surfaces into a second handbook during conflict resolution. Repair the source, rerender, then review the resulting diff.

## Quick Boundary Checks

- Active-now sequencing or next step: planning.
- Durable invariant, rationale, or runbook: memory or canonical docs.
- Shared module workflow support under `.agentic-workspace/`: package-managed surface.
- Rendered `tools/` guidance: generated output, not source.

## Hot-File Pressure

Use compact diagnostics before closeout or push:

Resolve this concern through the canonical startup skill and the current owner request returned by `start`. The [native CLI catalogue](/docs/reference/cli-catalogue.md) defines executable commands.

These are pressure signals, not locks. They tell an agent or reviewer when ordinary git collaboration risk is high enough to review, split, close, archive, rerender, or route durable residue before continuing.
