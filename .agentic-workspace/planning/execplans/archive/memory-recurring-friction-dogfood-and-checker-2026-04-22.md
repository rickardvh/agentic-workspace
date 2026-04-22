# Memory Recurring Friction Dogfood And Checker

Compact inactive-plan residue generated at archive time.
Use git history for superseded active-step detail; keep only the closure, continuation, proof, and cheap-resume residue here.

## Origin

- Source: roadmap lane `memory-recurring-friction-improvement-pressure`
- Prior slice: `.agentic-workspace/planning/execplans/archive/memory-recurring-friction-evidence-first-slice-2026-04-22.md`

## Intake Source

- System: GitHub
- ID: `#263`
- Title: [Memory]: Turn unlogged recurring friction into durable improvement pressure so agents do not silently notice the same package failures without collecting evidence or pushing them toward product improvement

## Intent Continuity

- Larger Intended Outcome: preserve lightweight recurring-friction evidence in Memory or adjacent durable surfaces so repeated package failures accumulate visible improvement pressure without turning every annoyance into backlog.
- This Slice Completes The Larger Intended Outcome: no
- Continuation Surface: .agentic-workspace/planning/state.toml
- Parent Lane: `memory-recurring-friction-improvement-pressure`

## Required Continuation

- Required Follow-On For The Larger Intended Outcome: yes
- Owner Surface: .agentic-workspace/planning/state.toml
- Activation Trigger: activate the next slice when another real recurring-friction example appears or when the repo keeps needing the checker/report path strongly enough that it should graduate into a shipped validation/reporting surface.

## Iterative Follow-Through

- What this slice enabled: one real recurring-friction entry now exists in the dogfooded ledger, and the repo has a cheap dedicated checker instead of relying on full Memory doctor just to see recurring-friction pressure.
- Intentionally deferred: promoting the repeated warning into a planning-owned fix, shipping the checker as package payload, and broader report/CLI integration.
- Discovered implications: the generic note-structure audit originally misclassified dated recurrence bullets as task-log drift, so the recurring-friction audit now explicitly exempts that false positive.
- Proof achieved now: recurring-friction evidence is no longer purely hypothetical in this repo, and the checker surfaces promotion pressure without failing on valid dated recurrence evidence.
- Validation still needed: one more real recurring-friction example or stronger evidence that the checker belongs in shipped validation rather than repo-local dogfooding support.
- Next likely slice: decide whether repeated recurring-friction follow-through should promote a planning fix directly or graduate the checker/report path into broader shipped validation.

## Delegated Judgment

- Requested Outcome: dogfood the recurring-friction path on a real repeated signal and tighten the path only where the first real use still leaked or stayed awkward.
- Hard Constraints: keep the slice compact; avoid turning the ledger into a second backlog; preserve Memory as the durable weak-signal owner; avoid widening into the planning fix for the repeated warning itself.
- Agent May Decide Locally: the repeated signal used for dogfooding, the smallest checker shape, and the narrowest package-side audit tweak needed to make the live entry valid.
- Escalate When: the slice would require a broader planning-residue redesign, a shipped validation lane, or automatic backlog creation.

## Intent Interpretation

- Literal Request: implement the next lane and commit
- Inferred Intended Outcome: keep advancing the now-top recurring-friction lane through the next bounded step, using the new ledger for a real repeated signal instead of leaving the first slice as unused infrastructure.
- Chosen Concrete What: add one real recurring-friction entry for the repeated archived-partial-intent warning, add a cheap repo checker for the recurring-friction ledger, and tighten the package audit so entry-level config treatment is required while valid dated recurrence bullets no longer trip generic task-log drift.
- Interpretation Distance: low
- Review Guidance: reject the slice if it turns the ledger into issue mirroring, if the checker becomes a second Memory doctor, or if the work silently widens into fixing the planning warning instead of preserving the signal.

## Execution Bounds

- Allowed Paths: `.agentic-workspace/memory/repo/runbooks/`, `.agentic-workspace/planning/`, `packages/memory/`, `scripts/check/`
- Max Changed Files: 12
- Required Validation Commands: `uv run pytest packages/memory/tests/test_installer.py -k "recurring_friction or improvement_pressure" -q`; `uv run python scripts/check/check_recurring_friction_ledger.py`; `uv run agentic-memory-bootstrap doctor --target . --format json`; `uv run agentic-memory-bootstrap promotion-report --target . --mode remediation --format json`; `uv run python scripts/check/check_source_payload_operational_install.py`; `uv run agentic-workspace summary --format json`
- Ask-Before-Refactor Threshold: stop before broader planning-warning repair, package-wide validation redesign, or issue auto-promotion.
- Stop Before Touching: unrelated roadmap lanes or broader Memory routing/reporting redesign.

## Stop Conditions

- Stop When: proving ordinary use would require fixing the repeated planning warning itself rather than preserving the signal.
- Escalate When Boundary Reached: repo-local checker proof still is not enough to make recurring-friction follow-through cheap and visible.
- Escalate On Scope Drift: the work starts implying a shipped validation/reporting tranche rather than a narrow dogfood slice.
- Escalate On Proof Failure: the live recurring-friction entry still triggers invalid structure drift or the checker cannot separate structural problems from promotion pressure.

## Context Budget

- Live Working Set: issue `#263`, the recurring-friction ledger runbook, the recurring-friction parser/audit, the new repo check path, and the repeated archived partial-intent continuation-owner warnings already visible in planning summary.
- Recoverable Later: whether the repeated warning itself should become active planning work, and whether the checker should graduate into a shipped validation/reporting surface.
- Externalize Before Shift: the concrete repeated signal captured, the checker command, the false-positive exemption for dated recurrence bullets, and the reason the lane stays open.
- Tiny Resumability Note: the lane now has both infrastructure and one real dogfooded signal; the remaining question is how much of this should graduate from repo-local proof into stronger shipped follow-through.
- Context-Shift Triggers: shift after validation proves the checker and ledger entry behave cleanly.

## Execution Run

- Run Status: completed
- Executor: Codex
- Handoff Source: roadmap lane plus live issue `#263`
- What Happened: added a real recurring-friction entry for the repeated archived partial-intent continuation-owner warnings, added `scripts/check/check_recurring_friction_ledger.py` so recurring-friction pressure is visible without a full doctor pass, and tightened the package audit so recurring-friction entries require `Config treatment` while exempting the ledger from the generic false-positive task-log warning that valid dated recurrence bullets would otherwise trigger.
- Scope Touched: root recurring-friction ledger/runbook, repo check scripts, memory package recurring-friction parser/audit logic, targeted memory tests, and roadmap/archive residue.
- Validations Run: `uv run pytest packages/memory/tests/test_installer.py -k "recurring_friction or improvement_pressure" -q`; `uv run python scripts/check/check_recurring_friction_ledger.py`; `uv run agentic-memory-bootstrap doctor --target . --format json`; `uv run agentic-memory-bootstrap promotion-report --target . --mode remediation --format json`; `uv run python scripts/check/check_source_payload_operational_install.py`; `uv run agentic-workspace summary --format json`
- Result For Continuation: recurring-friction evidence is now being used on a real repeated repo signal, and the next question is whether the checker/report path should remain repo-local or graduate into stronger shipped follow-through.
- Next Step: archive this slice, keep the lane open, and revisit once another real recurring-friction case or stronger demand for shipped validation appears.

## Finished-Run Review

- Review Status: completed
- Scope Respected: yes
- Proof Status: satisfied
- Intent Served: yes
- Misinterpretation Risk: low
- Follow-On Decision: archive this slice and keep the broader lane open in roadmap form.

## Proof Report

- Validation proof: targeted recurring-friction/improvement-pressure tests passed, the new checker surfaced promotion pressure without structural failure, Memory doctor reported the new recurring-friction signal as advisory pressure, the remediation report continued to recommend validation follow-through, and the source/payload/root-install boundary checker stayed clean.
- Proof achieved now: the recurring-friction path is dogfooded on a real repeated signal and has a cheap dedicated repo check path.
- Evidence for "Proof achieved" state: `.agentic-workspace/memory/repo/runbooks/recurring-friction-ledger.md` now contains a real repeated entry, `scripts/check/check_recurring_friction_ledger.py` prints recurring-friction pressure directly, and the package audit/test suite now enforces entry-level config treatment while allowing valid dated recurrence bullets.

## Intent Satisfaction

- Original intent: advance the recurring-friction lane beyond its first infrastructure slice.
- Was original intent fully satisfied?: no
- Evidence of intent satisfaction: the path is now real and cheaper to use, but the lane still needs more evidence about whether this should remain repo-local proof or graduate into stronger shipped validation/reporting.
- Unsolved intent passed to: `.agentic-workspace/planning/state.toml`

## Closure Check

- Slice status: bounded slice complete
- Larger-intent status: open
- Closure decision: archive-but-keep-lane-open
- Why this decision is honest: the lane now has infrastructure plus one real dogfooded signal, but it still has an open follow-through question about stronger shipped validation/reporting and future recurring cases.
- Evidence carried forward: the live ledger entry, the repo checker, the package audit/test tightening, and the roadmap lane.
- Reopen trigger: reopen only if the live checker path disappears, the ledger stops carrying real repeated signals, or repeated recurring-friction cases show the checker should graduate into stronger shipped follow-through.

## Execution Summary

- Outcome delivered: dogfooded the recurring-friction ledger on a real repeated repo warning, added a cheap recurring-friction checker, and tightened the package audit so recurring-friction entries require explicit config treatment without tripping false-positive task-log drift.
- Validation confirmed: `uv run pytest packages/memory/tests/test_installer.py -k "recurring_friction or improvement_pressure" -q`; `uv run python scripts/check/check_recurring_friction_ledger.py`; `uv run agentic-memory-bootstrap doctor --target . --format json`; `uv run agentic-memory-bootstrap promotion-report --target . --mode remediation --format json`; `uv run python scripts/check/check_source_payload_operational_install.py`; `uv run agentic-workspace summary --format json`
- Follow-On Routed To: `.agentic-workspace/planning/state.toml`
- Post-work Posterity Capture: preserve the rule that recurring-friction proof should stay cheap, dated recurrence bullets are valid evidence rather than task-log drift in this note, and promotion pressure should remain visible even when structural health is clean.
- Knowledge Promoted (Memory/Docs/Config): promoted the live repeated signal into the installed recurring-friction ledger and the repo checker surface; package tests now encode the entry-level config-treatment rule.
- Resume from: the roadmap lane `memory-recurring-friction-improvement-pressure`
