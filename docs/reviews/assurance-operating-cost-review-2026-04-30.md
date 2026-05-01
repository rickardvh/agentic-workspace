# Assurance Operating-Cost Review

## Report Header

- Host repo: `agentic-workspace` source checkout used as package dogfood
- Report date: `2026-04-30`
- Reporter / agent runtime: Codex in the local source checkout
- Package source: source checkout, invoked through `uv run agentic-workspace`
- Installed preset/modules: `full`; workspace, planning, and memory installed
- Run goal: implement adaptive-assurance trust evidence, public docs readiness, and final host-feedback lane closeout
- Slice type: active execplans with issue closeout and final dogfooding review
- Assurance level: medium by repo config, with high/critical fields exercised through proof and summary fixtures

## Run Summary

- Requested outcome: keep promoting and implementing lanes until `.agentic-workspace/planning/state.toml` is empty.
- What landed: assurance onboarding, proof trust-state evidence, external install handoff docs, public documentation status, runtime shim docs, and this host-repo dogfooding template/review.
- What did not land: real external host execution for #595; that remains intentionally outside this source-checkout lane.
- Closure decision: close #599 and #600 after this review and template land; keep #595 outside this lane.
- Residue destination: reusable template in `docs/host-repo-dogfooding-report-template.md`; evidence review in this file; non-actionable large-file hotspot remains issue #627 only.

## Assurance And Proof

- Required refs: GitHub #596, #597, #598, #599, #600 and the active execplan for this lane.
- Control gates or blockers: no blocking gates; #595 excluded by planning state because it needs another repo.
- Proof profiles selected: docs/planning checks and workspace CLI tests.
- Proof commands selected: focused docs/proof commands first, then maintainer surfaces, planning doctor, summary, and closeout reports before archiving.
- Proof commands executed so far in the parent run: full test suite, ruff, root CLI authority, planning doctor, maintainer surfaces, and package planning tests for earlier lane surfaces.
- Waivers, skips, or unavailable proof: no real-host #595 run in this lane; this review uses source-checkout dogfooding evidence only.
- Missing evidence: independent host-repo report filled from a different repository.
- Trust state after proof: usable for #599/#600 local acceptance; partial for future #595 real-host calibration.

## Touched Surfaces

| Surface | Owner | Why it changed | Host-private? |
| --- | --- | --- | --- |
| `docs/host-repo-dogfooding-report-template.md` | repo docs | Reusable host feedback shape for #600. | No |
| `docs/reviews/assurance-operating-cost-review-2026-04-30.md` | repo reviews | Filled review and operating-cost decisions for #599. | No |
| `docs/maintainer/dogfooding-feedback.md` | repo docs | Routes host reports to the new template. | No |
| `.agentic-workspace/planning/execplans/host-feedback-and-operating-cost.plan.json` | planning | Active lane proof and closeout state. | No |

## Friction Items

| Observation | Evidence | Likely owner | Product should absorb? | Recommendation | Follow-up target |
| --- | --- | --- | --- | --- | --- |
| Host feedback had no reusable report shape before this lane. | GitHub #600 and this new template. | product-general | yes | fix now | `docs/host-repo-dogfooding-report-template.md` |
| Adaptive assurance could become visible ceremony if every field appears in default startup paths. | GitHub #599 plus assurance fields added to defaults/config/proof. | product-general | maybe | keep compact defaults, keep detailed trust state selector-owned | no new issue |
| Large generated docs can become collaboration hotspots. | Existing issue #627 from earlier dogfooding. | product-general | maybe | report-only issue; do not ingest into planning without repeated evidence | #627 |
| Real-host adaptive assurance calibration is still missing. | #595 explicitly excluded from this lane. | product-general | yes | keep as external-host work, not source-checkout closeout blocker | #595 |

## Operating-Cost Review

| Work shape | Required fields | Inferred or optional fields | Default output impact | Decision |
| --- | --- | --- | --- | --- |
| Low-risk direct task | Startup/config route and normal proof command only. | Assurance can remain absent or defaulted from config. | No new required active-plan fields for direct work. | Keep; no demotion needed. |
| Medium-risk planned task | Active execplan, bounded touched paths, validation commands, and config assurance default. | Onboarding status and missing assurance config are inferable through `defaults`/`config`. | Compact summaries show assurance only when planning state carries it; config details stay selector-owned. | Keep selector-owned; do not add another dashboard. |
| High/critical task | Required refs, gates, proof profiles, execution evidence, waiver reasons, and trust state. | Missing evidence and lower-trust counts can be derived from declared proof and command evidence. | Detailed trust classification belongs in `proof`, not default startup. | Keep; high-risk work earns the added fields. |

## Concrete Decisions

- Keep `assurance_onboarding` in `defaults` and config output because it answers adoption readiness without forcing raw config reads.
- Keep proof execution evidence in `agentic-workspace proof` selection output, where high-risk reviewers already look.
- Do not add a new host-feedback command yet; the template is cheaper and matches #600's stated preference.
- Do not ingest #627 into planning now; it is a plausible hotspot signal, not a blocking bug or repeated failure.
- Do not close or absorb #595 from this lane; the source checkout cannot honestly prove another host repo's adaptive-assurance behavior.

## Privacy And Sensitivity

- Omitted host details: none; this report uses the public source checkout.
- Redactions or anonymization: none.
- Evidence that should stay in the host repo: future #595 host-specific files, logs, and private planning state.

## Conversion To Focused Issues

No new issue is needed from this review. The missing report shape is fixed here, the assurance operating-cost decisions are recorded here, #627 already carries the large-file hotspot as report-only evidence, and #595 remains the external-host calibration lane.
