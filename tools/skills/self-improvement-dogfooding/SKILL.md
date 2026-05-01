---
name: self-improvement-dogfooding
description: Run bounded repo-local self-improvement passes that dogfood Agentic Workspace surfaces without becoming shipped product workflow.
---

# Self-Improvement Dogfooding

Use this repo-owned skill when asked to continue, repeat, or run autonomous improvement work in this repository. This skill is local guidance for this repo only; it is not package authority, not a shipped feature, and not a replacement for human-owned product direction.

## Purpose

Make the package the cheapest path for improving itself: review compact state, choose one bounded slice, implement it through existing package commands, validate, assess intent satisfaction, route friction, then stop or continue only while the current direction remains already established.

## Required First Commands

Run compact package surfaces before reading broad files:

1. `uv run agentic-workspace summary --format json`
2. `uv run agentic-workspace report --target . --format json`
3. `uv run agentic-workspace report --target . --section improvement_intake --format json`
4. `uv run agentic-workspace reconcile --format json`
5. `uv run agentic-workspace skills --target . --task "<current task>" --format json`

Read `.agentic-workspace/system-intent/intent.toml` or `SYSTEM_INTENT.md` only when the compact surfaces or the current issue need product-direction context.

## Loop Shape

Use one pass at a time:

1. Inspect compact state and current external-work evidence.
2. Choose one bounded slice tied to an open issue, active plan, review finding, or clear system-intent pressure.
3. Promote to an execplan before broad implementation.
4. Implement using existing package commands and package-selected proof.
5. Validate with `agentic-workspace proof --target . --changed <paths> --format json` plus required commands.
6. Assess intent satisfaction separately from validation success.
7. Assess total operating cost separately from issue completion and intent satisfaction.
8. Route durable residue separately from validation, issue closure, intent satisfaction, and cost assessment.
9. Route discovered friction into a narrow fix, review record, memory note, issue, or explicit dismissal.
10. Review changed operational surfaces for affordance quality before closeout.
11. Close/archive only when evidence is compact and reconstructable.

## Allowed Autonomous Actions

- Promote roadmap or external-work evidence into a bounded execplan.
- Make scoped code, contract, test, docs, or repo-local skill changes.
- Create issues for bugs, unclear commands, validation gaps, or recurring friction.
- Close issues only after implementation, proof, closeout review, and reconcile evidence agree.
- Commit and push after each milestone when the working tree is clean for that milestone.

## Stop And Review Triggers

Stop for human review when:

- the next useful change would alter product direction, authority boundaries, or system intent;
- the slice would add a new first-line surface instead of compressing or routing an existing one;
- confidence depends on subjective product judgment rather than local evidence;
- validation cannot prove the behavioral claim;
- the work risks overfitting to this repo or this agent runtime;
- scope wants to expand beyond the current issue or execplan.

## Evidence To Leave

Each pass should leave:

- an active or archived execplan when work was broad enough to need one;
- a closeout review or equivalent compact evidence for issue closure;
- proof selector output or named validation commands;
- external-work evidence updates when tracked issues change state;
- an `improvement_signal_review` or equivalent note that says whether signals were found, fixed, routed, dismissed, or absent;
- a total-operating-cost assessment with net cost direction;
- a durable-residue routing answer that says whether future-relevant motivation or lessons were promoted, routed, dismissed, or absent;
- a clear continuation owner for any unsolved intent.

## Constrained Prose Shape

Prefer structured execplan and review fields. When a self-improvement pass needs a short human-readable note, use the same constrained shape exposed by planning review `prose_templates`:

- `Intent`: the original or larger product outcome being served.
- `What changed`: the bounded implementation or routing decision.
- `Proof`: the validation, check, or review evidence.
- `Remaining risk`: the unresolved risk or why none remains.
- `Durable residue`: where reusable learning was promoted, routed, or dismissed.
- `Next owner`: the issue, plan, Memory/docs/contracts/check owner, or `none`.

## Required Cost Assessment

Every self-improvement pass must answer this before claiming the system improved. Validation success and issue closure are evidence, but they are not sufficient by themselves.

Record a compact cost assessment in the execplan closeout, review artifact, or issue-close proof:

- `workflow_cost_found`: What workflow was slower, more manual, or easier to bypass than it should be?
- `architecture_cost_found`: What module, boundary, duplication, or overgrown surface made change harder?
- `needless_complexity_found`: What concept, field, command, or artifact can be merged, removed, demoted, or made optional?
- `correct_by_design_assessment`: Did the change make the correct action easy to construct before validation runs, and if not, what scaffold, writer helper, alias, lifecycle command, compact route, or agent aid owns that gap?
- `surfaces_added`: Which visible surfaces were added?
- `surfaces_removed_merged_or_demoted`: Which visible surfaces were removed, merged, shortened, hidden behind selectors, or made opt-in?
- `artifact_footprint_changed`: What happened to planning, review, Memory, generated, local-only, or evidence artifacts?
- `shipped_default_footprint_changed`: Did ordinary host-repo startup/install get smaller, larger, or unchanged?
- `signals_consumed`: Which `improvement_signal_candidates`, Memory improvement-signal notes, Planning follow-through entries, review findings, or human corrections were consumed?
- `signals_still_accumulating`: Which cost signals remain and where are they routed?
- `durable_residue_consumed_or_routed`: Which future-relevant motivation, constraints, lessons, or closeout residue were consumed or routed, and to which owner?
- `human_steering_avoided_next_time`: What repeated correction should the package catch without the human saying it again?
- `validation_role`: Did validation confirm an already-correct construction, or did it still teach artifact/workflow construction through a repair loop?
- `follow_up_routed`: What issue, plan, Memory note, review, docs/check/skill change, or dismissal owns the remainder?
- `net_cost_direction`: `lower`, `same`, or `higher`.

If `net_cost_direction` is `same` or `higher`, do not close as an improvement solely because tests passed. Route the remaining cost signal or explain why retention is intentional.

## Required Durable-Residue Routing

Every self-improvement pass must answer this before claiming the system improved. Validation passing, an issue closing, intent being satisfied, and operating cost going down are separate answers; none of them proves durable residue was routed.

Record a compact durable-residue answer in the execplan closeout, review artifact, or issue-close proof:

- `validation_passed`: yes | no, with proof command or reason
- `issue_completed`: yes | no | not_applicable, with tracker or local owner
- `intent_satisfied`: yes | no | partial, with the larger-intent owner if partial
- `operating_cost_reduced`: yes | no | same | unknown, with the cost assessment reference
- `durable_residue_routed`: yes | no | none_found, with the destination or dismissal reason
- `durable_residue_owner`: Memory | docs | contracts | checks | planning | issue | review | none
- `durable_residue_summary`: one sentence naming the motivation, constraint, lesson, or reason no residue exists
- `post_promotion_shape`: retain | shrink | stub | delete | not_applicable

Do not close a self-improvement pass as improved when future-relevant motivation or lessons exist only in an archived execplan, review artifact, issue comment, or chat transcript. Route that residue to Memory, docs, contracts, checks, planning, an issue, a review record, or explicitly dismiss it as not future-relevant.

If residue is routed to Memory, keep it compact and use the Memory note template's closeout-derived residue fields. If residue belongs in docs, contracts, checks, or planning, update or create that owner instead of duplicating the full archive. If no residue exists, say `durable_residue_routed = "none_found"` and explain why future work does not need to act differently.

## Friction Routing

Treat dogfooding friction as product input, but do not derail the active lane. Prefer this order:

1. Fix immediately only if the friction blocks the current proof or causes unsafe behavior.
2. Consume `agentic-workspace report --target . --section improvement_intake --format json` and decide whether each relevant signal is fixed, routed, reviewed, remembered, dismissed, or intentionally retained.
3. Treat repeated validation repair loops as package/interface defects; prefer scaffolds, writer helpers, aliases, lifecycle commands, compact routes, or agent aids before adding more validation prose.
4. Create a narrow issue when the friction is real but not blocking.
5. Record a review finding when evidence needs later prioritization.
6. Promote durable repo knowledge to memory only when it will prevent rediscovery.

## Required Anti-Overfitting Review

Before closing a self-improvement pass, record a compact anti-overfitting review in the execplan closeout, review artifact, or issue-close proof. Do not treat validation success alone as enough to close.

Answer all four fields:

- `user_agent_value`: What real entry, recovery, proof, closure, handoff, or operating cost became cheaper for agents or users?
- `surface_pressure`: Did this add a visible surface, and if so which existing surface did it replace, compress, merge, or background?
- `portability_boundary`: Did this avoid hardening this repo's language, tooling, host, vendor, or agent-runtime assumptions into package contract?
- `human_intent_preserved`: Where is the human-owned why or larger system intent preserved separately from implementation detail?

Route to a planning review instead of closing when:

- product direction, authority, or portability is ambiguous;
- the benefit is only package-internal neatness;
- the change adds a new visible surface without reducing another repeated cost;
- a reviewer cannot understand the value and boundary from checked-in evidence.

## Required Operational-Affordance Review

When a pass changes startup, recovery, proof, closeout, lifecycle, Memory, planning, agent-aid, or other operational surfaces, review it against `docs/maintainer/operational-affordance-design.md` before closing.

Record a compact answer in the execplan closeout, review artifact, or issue-close proof:

- `primary_next_action`: the one obvious action the surface now presents, or why none is appropriate.
- `irrelevant_actions_demoted`: which distracting, raw, historical, or deep actions were hidden, deferred, or placed behind selectors.
- `resolved_invocation`: whether copyable commands use the resolved repo/local invocation or intentionally stay canonical.
- `weak_agent_path`: whether an unfamiliar or generic agent can proceed without reading package internals first.
- `strong_agent_escape_hatch`: how an expert can inspect, override, or bypass safely.
- `context_burden_change`: whether the change reduces, preserves, or increases the amount of live context needed to act.
- `validation_role`: whether validation confirms an already-guided path or still teaches the construction after failure.

Treat a repeated need to reread raw planning, Memory, review, contract, or issue-thread detail as an affordance signal. Prefer reshaping existing compact routes, action objects, selectors, scaffolds, writer helpers, aliases, or lifecycle flows before adding a new surface.

## Closure Criteria

Close the pass when the bounded slice is implemented, validated, assessed against intent, assessed for operating-cost direction, durable residue is routed or explicitly absent, and any follow-up is routed. Continue to another pass only when an already-established issue or roadmap lane remains and no stop trigger fired.
