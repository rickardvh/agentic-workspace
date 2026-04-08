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
- resolved on 2026-04-08 by explicit bundled-skill and repo-owned skill registries plus the `agentic-workspace skills` discovery surface.

## Over-routing entries

- Add a case only when routing repeatedly returns an unnecessary note.
- Each case should record task surface summary, files or surfaces, routed notes returned, unexpected notes, why they were unnecessary, and status.

## Synthesis

- Keep only concrete cases that materially improve routing.
- Do not restate durable routing guidance here once it has a better long-lived home.
- Prefer one live case per routing issue and prune resolved entries quickly so the note stays merge-friendly.
- Compress tuned or rejected cases into a short summary or remove them once the routing rule is stable.
- Current case is retained briefly as a just-landed regression example and can be removed after one ordinary maintenance cycle confirms the new registry-backed discovery path stays reliable.

## Last confirmed

2026-04-08 during roadmap autopilot follow-through
