# Planning Live-State Collaboration Design

This note records the current design choice for #804. It is a design boundary, not an implemented migration.

## Current Model

Planning uses `.agentic-workspace/planning/state.toml` as the compact live selector for active and queued work. Execplan files hold the richer execution contract. Completed work should be closed, distilled, and removed from live planning state; durable residue goes to Memory, docs, checks, contracts, or issues.

This model is simple and reviewable, but `state.toml` is a shared hot file. Ordinary git merges still apply.

## Alternatives Considered

### Keep Compact `state.toml`

Benefits:

- one obvious live-state entrypoint;
- cheap startup and summary reads;
- easy human review;
- no migration cost.

Costs:

- concurrent active-work registration can conflict;
- large queued/candidate sets make the file harder to merge;
- agents may treat storage bucket location as maturity unless diagnostics stay clear.

### Per-Work-Item Records

Benefits:

- unrelated lanes can mutate separate files;
- same-branch handoff can point directly at one item;
- merge conflicts become more localized.

Costs:

- startup must project a compact index;
- migration and garbage collection become package behavior;
- many tiny files can increase repo noise and read overhead;
- users may confuse per-item records with an archive.

### Append-Only Event Records

Benefits:

- independent mutations can append separate events;
- audit trails can explain how live state changed.

Costs:

- event logs grow forever unless compacted;
- agents must understand projection, compaction, and conflict recovery;
- closeout becomes harder because planning owns future work, not history;
- replay bugs would be worse than ordinary TOML conflicts.

## Chosen Direction

Do not migrate yet. Strengthen the compact model first:

- keep `state.toml` live-only and small;
- expose `planning_surface_health.collaboration_pressure`;
- warn when shared Planning surfaces changed in git status;
- keep completed execution chronology out of live Planning;
- distill reusable residue to Memory, docs, checks, contracts, or issues at closeout;
- document the merge model honestly.

## Future Trigger

Revisit per-work-item live state only if real collaboration evidence shows that compact-state pressure remains a recurring blocker after diagnostics and live-only closeout discipline are in place.

Any future migration must preserve:

- a compact startup projection;
- backward-compatible reading of existing `state.toml`;
- no hidden database or service;
- no ever-growing planning archive;
- clear closeout distillation into Memory/docs/issues/checks instead of retained execution history.
