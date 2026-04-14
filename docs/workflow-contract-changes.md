# Workflow Contract Changes

Use this page as a compact maintainer-facing record of recent workflow-surface changes.

Keep this page short and decision-shaped; it is not the full changelog, release notes, or command index.

## 2026-04-14

- Added a canonical `planning_record` to `agentic-planning-bootstrap summary --format json`, then tightened the intent and resumable contract docs and human summary views so they read as projections over that record instead of competing sources of truth.
- Added a compact `Product improvement signal` field to execplan execution summaries so completed slices can carry one dogfood reflection forward instead of leaving it only in chat.

## 2026-04-08

- Restored the missing canonical source/payload/root-install boundary guide at `docs/source-payload-operational-install.md`.
- Hardened `scripts/check/check_maintainer_surfaces.py` so the direct wrapper now aggregates planning-surface checks with the boundary checker when that checker exists in the repo.

## 2026-04-07

- Added an explicit source/payload/root-install boundary guide and a standalone advisory checker.
- Wired `make maintainer-surfaces` to include the new boundary check alongside the existing liveness path.
- Taught the root and package AGENTS docs, contributor playbook, and maintainer command index to point at the new boundary guide.

## 2026-04-06

- Added `make maintainer-surfaces` as the single repo-maintainer check path for generated maintainer docs, startup-policy consistency, and packaged planning payload freshness.
- Added an explicit integration contract and a dogfooding-feedback classification convention.
- Tightened package README first-screen framing around selective adoption and working alongside the other module.
- Added an installed-contract design checklist so package authors can review new shipped surfaces against collaboration-safe criteria.
- Clarified the root docs map with page-specific roles and added a maintainer-surface check for docs-role drift across the maintainer docs set.
- Added a generated-surface trust doc so maintainer guidance can point at one canonical source/freshness policy for generated mirrors.

## 2026-04-05

- Slimmed the root README toward an adopter-first entrypoint and added the chooser, maturity model, and policy docs.
- Marked generated routing docs visibly as generated and added startup-policy plus generated-doc drift checks.
- Centralized maintainer commands and collaboration-safety guidance.
