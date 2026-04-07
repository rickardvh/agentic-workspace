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

## Over-routing entries

- Add a case only when routing repeatedly returns an unnecessary note.
- Each case should record task surface summary, files or surfaces, routed notes returned, unexpected notes, why they were unnecessary, and status.

## Synthesis

- Keep only concrete cases that materially improve routing.
- Do not restate durable routing guidance here once it has a better long-lived home.
- Prefer one live case per routing issue and prune resolved entries quickly so the note stays merge-friendly.
- Compress tuned or rejected cases into a short summary or remove them once the routing rule is stable.

## Last confirmed

2026-04-05 during bootstrap adoption
