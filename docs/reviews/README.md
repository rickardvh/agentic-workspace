# Review Artifacts

Checked-in review artifacts for bounded future-work discovery live in this directory.

Use this lane when an agent or maintainer is doing deliberate analysis of a repo area to surface concrete risks, opportunities, or weaknesses that may deserve future work, but should not automatically become active execution.

This review lane exists to keep analysis-derived findings explicit, bounded, and separate from friction-confirmed planning input.

## Purpose

- Capture evidence-backed findings from a scoped review pass.
- Keep capture separate from promotion into `ROADMAP.md` or `TODO.md`.
- Preserve the higher trust of friction-derived improvement signals.
- Avoid speculative queue churn from unconfirmed analysis.

## Ownership

- `docs/reviews/` owns bounded review artifacts.
- `ROADMAP.md` owns inactive future candidates once a finding is promoted.
- `TODO.md` plus `docs/execplans/` own active planned work once promotion becomes immediate execution.
- Memory owns durable technical knowledge that remains valuable after the review artifact has done its job.

Do not use review artifacts as a substitute for execplans, memory notes, or canonical docs.

## When To Use A Review Artifact

Use a review artifact when:

- the task is a bounded review pass rather than implementation work
- findings need evidence, confidence, and promotion guidance recorded
- the work may surface future candidates but should not activate them automatically
- the result should stay compact enough for later promotion or dismissal

Do not use this lane for:

- ordinary implementation status
- static-analysis dumps with no triage
- broad speculative cleanup inventories
- durable subsystem guidance that belongs in canonical docs or memory

## Capture Contract

Each review artifact should stay compact and include:

- review goal and scope
- explicit non-goals
- evidence-backed findings only
- source classification for each finding
- confidence and risk if unchanged
- suggested action
- promotion target and trigger
- validation or inspection commands used

Use the template in this directory and prefer one bounded review question per file.

## Source Classes

Every finding should declare one source class:

- `static-analysis`: derived from code inspection, lint output, or other analysis without direct friction confirmation
- `friction-confirmed`: supported by repeated real workflow friction, failure, or maintainer confirmation
- `mixed`: analysis-derived finding with some supporting real-world confirmation

Treat `friction-confirmed` findings as higher trust than pure analysis findings.

## Promotion Rules

Use staged promotion:

1. keep the finding in the review artifact only
2. promote it to `ROADMAP.md` when the work is plausible future value but not active now
3. promote it to `TODO.md` plus an execplan only when explicit maintainer choice, repeated friction, or clear urgency justifies activation
4. move durable stable guidance into canonical docs or memory when the value is long-lived knowledge rather than future work tracking

Do not promote every finding. Dismiss weak, duplicate, or low-value findings instead of turning the queue into an analysis backlog.

## Maintenance

- Keep review artifacts feature- or scope-scoped.
- Prefer archiving or deleting stale review artifacts once findings are promoted, dismissed, or superseded.
- Do not leave top-level `docs/reviews/` full of old speculative notes.
- If a review repeatedly produces the same finding, prefer fixing the underlying docs, tests, validation, or structure.
- Add a **Status Footer** at the end of each review document that tracks which findings have been promoted, deferred, or dismissed. Format: list by finding name/number and target (`promoted to ROADMAP.md`, `deferred pending X`, `dismissed as Y`). When all findings are accounted for, delete the review artifact.
