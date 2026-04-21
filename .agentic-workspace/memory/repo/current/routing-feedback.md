# Routing Feedback

## Status

Active

## Scope

- Optional routing calibration note for concrete missed-note or over-routing cases.

## Load when

- Re-checking whether a known routing miss is now covered.
- Reviewing whether a known over-routing example is still noisy after index or manifest changes.

## Review when

- A recorded case is tuned, rejected, or no longer useful.
- The note starts behaving like an archive instead of a compact calibration surface.

## Missed-note entries

- Add a case only when routing materially missed a note worth fixing.
- Each case should record task surface summary, files or surfaces, routed notes returned, expected missing note, why it mattered, expected routing signal, and status.

### Case: repo-skill-discovery-missed-installed-autopilot

Task surface summary
- User explicitly instructed the agent to use the autopilot skill for roadmap execution.

Files
- `AGENTS.md`
- `.agentic-workspace/planning/skills/planning-autopilot/SKILL.md`
- `packages/planning/skills/planning-autopilot/SKILL.md`

Surfaces
- planning-skill discovery
- repo-local installed workflow support

Routed notes returned
- Session-global skill registry only; no repo/package skill lookup was performed.

Expected missing note
- `.agentic-workspace/planning/skills/planning-autopilot/SKILL.md`

Why it was needed
- The agent incorrectly concluded that no autopilot skill was available, even though the repo carried both installed and package-local copies.

Expected routing signal
- When the user explicitly names a repo/package skill, search checked-in and installed `SKILL.md` surfaces before declaring it unavailable.

Status
- externalized on 2026-04-17 via `agentic-workspace skills`; this is no longer a Memory routing miss.

### Case: review-skill-routing-missed-review-shaped-requests

Task surface summary
- User asked the agent to perform reviews and later pointed out that the review skill should have been used automatically.

Files
- `AGENTS.md`
- `.agentic-workspace/planning/reviews/README.md`
- `.agentic-workspace/planning/skills/planning-review-pass/SKILL.md`
- `packages/planning/skills/planning-review-pass/SKILL.md`

Surfaces
- planning-skill discovery
- task-to-skill recommendation
- review workflow routing

Routed notes returned
- General repo reasoning only; no review skill lookup or routing decision was made.

Expected missing note
- `.agentic-workspace/planning/skills/planning-review-pass/SKILL.md`

Why it was needed
- Review-shaped requests should route to the bundled review workflow without requiring the user to know that a review skill exists or to mention it explicitly.

Expected routing signal
- When the task asks for a review or clearly describes a bounded review pass, search the bundled planning review skill and prefer it over generic repo reasoning.

Status
- externalized on 2026-04-17 via `agentic-workspace skills`; generic review-skill recommendation belongs to workspace skill discovery, not Memory routing.

## Over-routing entries

- Add a case only when routing repeatedly returns an unnecessary note.
- Each case should record task surface summary, files or surfaces, routed notes returned, unexpected notes, why they were unnecessary, and status.

## Synthesis

- Keep only concrete cases that materially improve routing.
- Do not restate durable routing guidance here once it has a better long-lived home.
- Prefer one live case per routing issue and prune resolved entries quickly so the note stays merge-friendly.
- Compress tuned or rejected cases into a short summary or remove them once the routing rule is stable.
- Externalized skill-discovery cases are retained only long enough to document why they no longer belong in Memory routing review.

## Last confirmed

2026-04-17 during memory cheap-path follow-through
