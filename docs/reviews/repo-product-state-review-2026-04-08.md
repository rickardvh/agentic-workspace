# Review: Repo Product State

## Goal

- Review the current repo state as a whole after the latest planning, issue-intake, and workflow updates, with emphasis on the shipped product shape and the monorepo's dogfooding value.

## Scope

- Root product and maintainer contract surfaces
- Root planning and roadmap state
- GitHub issue intake and review workflow
- Current package-boundary and maintainer-surface signals

## Non-Goals

- Do not activate new work in `TODO.md` from this review alone.
- Do not perform package or docs edits during the review.
- Do not re-review every individual memory note or package test surface in depth.

## Review Method

- Commands inspected conceptually: `make maintainer-surfaces`, `make planning-surfaces`, and the root/package lifecycle refresh workflow as documented.
- Evidence sources: `README.md`, `AGENTS.md`, `TODO.md`, `ROADMAP.md`, `docs/reviews/README.md`, current GitHub issues, maintainer docs, and visible check wrappers.

## Findings

### Finding: The repo now has a real issue-intake and review-promotion layer

- Summary: The latest updates materially improved the repo's ability to dogfood an upstream-triage-to-planning workflow. The repo now has issue forms, a review-artifact promotion threshold, and a roadmap section that explicitly prioritizes issue-derived candidates.
- Evidence: GitHub issue forms now exist for bugs, planning intake, and workflow friction; `docs/reviews/README.md` now defines a concrete promotion threshold for review-derived findings; and `ROADMAP.md` contains a dedicated GitHub issue intake section that prioritizes specific current issues.
- Risk if unchanged: Low. This is a positive state change. The main risk is usage drift rather than missing infrastructure.
- Suggested action: Keep this intake layer, but make sure the next step is at least one clean end-to-end execution path from issue -> roadmap/TODO -> execplan -> implementation -> close.
- Confidence: high
- Source: friction-confirmed
- Promotion target: none
- Promotion trigger:

### Finding: Maintainer-surface hardening is still the clearest unresolved contract-integrity gap

- Summary: The repo's maintainer-facing contract is stronger than before, but one important chain is still visibly broken: root and package guidance point maintainers to `docs/source-payload-operational-install.md`, while that file is still missing on `master`, and the root maintainer-surface wrapper still does not visibly prove the broader boundary-aggregation claim made by maintainer docs.
- Evidence: `AGENTS.md` and package-local contracts still instruct maintainers to read `docs/source-payload-operational-install.md` for source/payload/root-install work; maintainer commands say `make maintainer-surfaces` covers source/payload/root-install boundary drift; but the root maintainer wrapper still only delegates to the planning checker path, and the referenced boundary doc is not present on `master`.
- Risk if unchanged: Future maintainers and agents may trust a workflow path that is only partially wired, which weakens confidence in the repo's self-description and can send work down the wrong proving path.
- Suggested action: Treat this as the next concrete maintainer-surface consistency hardening slice: restore the missing canonical doc, then either integrate the boundary checker into the maintainer-surface aggregator or narrow the documented claim until the integration is real.
- Confidence: high
- Source: mixed
- Promotion target: `ROADMAP.md`
- Promotion trigger: Promote immediately if another maintainer pass still finds the same missing-doc or overclaimed-check chain after the current roadmap candidate is revisited.

### Finding: GitHub issue intake is working, but issue hygiene is not yet disciplined enough to be a reliable triage layer

- Summary: The new issue intake workflow is clearly alive, but the current issue set already shows duplicate and malformed planning intake. That means the intake layer exists, but the repo does not yet have a clean operational discipline for deduplication and issue splitting.
- Evidence: The current open planning issues include two substantially duplicate recurring-failures issues, and one planning issue body contains content for more than one issue instead of a single bounded signal. The roadmap already recognizes part of this by grouping Issues #3 and #4 as duplicates in substance.
- Risk if unchanged: The issue layer may become noisy faster than it becomes useful, which would weaken its value as an upstream triage surface and make later issue -> planning promotion less trustworthy.
- Suggested action: Add and dogfood a small issue-hygiene rule set: dedupe on intake, split malformed compound issues, and keep one bounded planning signal per issue. Then clean the current issue set to match that discipline.
- Confidence: high
- Source: friction-confirmed
- Promotion target: `ROADMAP.md`
- Promotion trigger: Promote when another review or ordinary maintenance pass still finds duplicate or compound intake issues after one cleanup cycle.

## Recommendation

- Promote: None yet.
- Defer: The maintainer-surface hardening and issue-hygiene findings, both of which already have a natural home in roadmap-level follow-up.
- Dismiss: None.

## Validation / Inspection Commands

- `make maintainer-surfaces`
- `make planning-surfaces`
- `uv run agentic-planning-bootstrap upgrade --target .`
- `uv run agentic-memory-bootstrap upgrade --target .`

## Drift Log

- 2026-04-08: Review created after the latest issue-intake, roadmap, and planning updates to reassess the repo as both dogfooding surface and shipped-product monorepo.

## Status Footer

- Finding 1 (Repo now has a real issue-intake and review-promotion layer): no promotion needed; documents current good state.
- Finding 2 (Maintainer-surface hardening is still the clearest unresolved contract-integrity gap): deferred to existing roadmap candidate on maintainer-surface consistency hardening.
- Finding 3 (GitHub issue intake is working, but issue hygiene is not yet disciplined enough): deferred pending explicit issue-hygiene cleanup and one more pass to confirm whether the problem recurs.

Review ready for deletion once Findings 2 and 3 are either promoted into active work or demonstrably resolved.
