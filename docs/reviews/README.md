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

## Canonical Review Portfolio

Use one primary review mode per artifact. If a review starts surfacing a second substantial mode, split it into another artifact instead of widening the scope.

Choose `contract-integrity` when the core question is whether a repo claim that future contributors would reasonably trust still resolves to a real canonical surface, runnable command, or enforced check path.

| Review mode | Purpose | Inspect first | Typical findings | Likely promotion target | Default cap |
| --- | --- | --- | --- | --- | --- |
| `contract-integrity` | Check whether repo claims, docs, and enforced surfaces still agree. | Canonical docs, check wrappers, claimed contract files | broken references, docs-code drift, promise-vs-enforcement gaps | `ROADMAP.md` or canonical docs | 3 findings |
| `planning-surface` | Check whether `TODO.md`, `ROADMAP.md`, execplans, and planning docs still form a coherent execution contract. | `TODO.md`, `ROADMAP.md`, active execplans, planning checks | stale queue state, missing execplan links, contradictory sequencing guidance | `ROADMAP.md` or `TODO.md` | 3 findings |
| `current-context` | Check whether current-state notes still behave like weak-authority re-orientation rather than shadow planning. | `memory/current/`, shared workflow docs, active planning surface | planner-like drift, authority ambiguity, restart-cost inflation | `ROADMAP.md`, canonical docs, or memory | 2 findings |
| `memory-boundary` | Check whether memory stays routed, justified, and subordinate to canonical docs and planning. | `memory/index.md`, memory workflow docs, representative notes, freshness output | over-capture, duplicated authority, missing promotion to canonical docs, noisy routing | `ROADMAP.md`, canonical docs, or memory | 3 findings |
| `maintainer-workflow` | Check whether maintainer-facing commands and docs still describe a real, runnable workflow. | maintainer docs, check wrappers, lifecycle commands, package/root guidance | broken maintainer paths, missing docs, overclaimed checks, boundary confusion | `ROADMAP.md` or canonical docs | 3 findings |
| `source-payload-install` | Check whether package source, shipped payload, and root operational install still line up. | package sources, bootstrap payload, root installed surfaces, lifecycle tests | source/payload drift, install mismatch, upgrade ambiguity, generated-root confusion | `ROADMAP.md` or `TODO.md` | 3 findings |
| `generated-surface-trust` | Check whether generated helper surfaces still faithfully reflect their canonical source. | manifest sources, generated docs, render scripts, installer checks | stale generated docs, missing render coverage, misleading derived guidance | `ROADMAP.md` or canonical docs | 2 findings |
| `validation-lane` | Check whether the documented validation lane still proves the promised contract. | package tests, repo checks, maintainer command docs, failing gaps | missing regression coverage, weak check aggregation, undocumented required steps | `ROADMAP.md` or `TODO.md` | 3 findings |
| `context-cost` | Check whether startup and handoff surfaces stay cheap enough for routine agent use. | startup docs, agent manifest, memory routing surfaces, review/read requirements | over-reading, oversized startup bundles, repeated low-signal reads | `ROADMAP.md`, memory, or canonical docs | 2 findings |
| `review-promotion` | Check whether review findings are being promoted, deferred, or deleted with discipline. | `docs/reviews/`, roadmap intake, archived plans, status footers | stale review residue, duplicate candidates, weak promotion hygiene | `ROADMAP.md` or review cleanup | 2 findings |

Treat the first seven modes as the default recurring portfolio. Use `validation-lane`, `context-cost`, and `review-promotion` as occasional audit modes when repeated friction suggests them.

## Review Questions

Every review artifact should state:

- the chosen review mode
- the specific review question being answered
- the main inputs inspected first
- the default finding cap for that mode

If the review needs materially more findings than the default cap, split the work or justify the exception explicitly.

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

## Improvement-targeting workflow

Use this workflow when a memory note, review finding, or other feedback signal looks symptomatic rather than purely durable truth:

1. classify the signal as durable truth or symptom
2. choose one primary remediation target category:
   - canonical docs
   - regression tests
   - validation/checks
   - scripts/commands
   - skills
   - refactor/cleanup
   - design-boundary clarification
3. choose the routing surface:
   - memory only when the target is obvious and no broader analysis is needed yet
   - review artifact when target or scope still needs bounded analysis
   - issue intake when the signal should enter the upstream tracker
   - `ROADMAP.md` when the remediation is plausible future work
   - `TODO.md` plus execplan when the remediation is explicitly active now
4. record the intended post-remediation note shape: retain, shrink, stub, or delete
5. after remediation lands, revisit the note or review artifact and carry out that shape change instead of leaving workaround residue by default

If a symptomatic note keeps surviving without a chosen remediation target, escalate it into review, roadmap, or maintainer triage rather than letting it remain an indefinite workaround note.

## Maintenance

- Keep review artifacts feature- or scope-scoped.
- Prefer archiving or deleting stale review artifacts once findings are promoted, dismissed, or superseded.
- Do not leave top-level `docs/reviews/` full of old speculative notes.
- If a review repeatedly produces the same finding, prefer fixing the underlying docs, tests, validation, or structure.
