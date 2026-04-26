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
3. `uv run agentic-workspace reconcile --format json`
4. `uv run agentic-workspace skills --target . --task "<current task>" --format json`

Read `.agentic-workspace/system-intent/intent.toml` or `SYSTEM_INTENT.md` only when the compact surfaces or the current issue need product-direction context.

## Loop Shape

Use one pass at a time:

1. Inspect compact state and current external-work evidence.
2. Choose one bounded slice tied to an open issue, active plan, review finding, or clear system-intent pressure.
3. Promote to an execplan before broad implementation.
4. Implement using existing package commands and package-selected proof.
5. Validate with `agentic-workspace proof --target . --changed <paths> --format json` plus required commands.
6. Assess intent satisfaction separately from validation success.
7. Route discovered friction into a narrow fix, review record, memory note, or issue.
8. Close/archive only when evidence is compact and reconstructable.

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
- a clear continuation owner for any unsolved intent.

## Friction Routing

Treat dogfooding friction as product input, but do not derail the active lane. Prefer this order:

1. Fix immediately only if the friction blocks the current proof or causes unsafe behavior.
2. Create a narrow issue when the friction is real but not blocking.
3. Record a review finding when evidence needs later prioritization.
4. Promote durable repo knowledge to memory only when it will prevent rediscovery.

## Anti-Overfitting Checks

Before closing a pass, ask:

- Did the package make entry, recovery, proof, or closure cheaper?
- Did this preserve repo-, agent-, tool-, host-, and language-agnostic package behavior?
- Did this avoid making a repo-local convenience look like shipped package authority?
- Can a reviewer understand the improvement without reconstructing chat?
- Is lane satisfaction honest for now, even if broader system intent remains open?

## Closure Criteria

Close the pass when the bounded slice is implemented, validated, assessed against intent, and any follow-up is routed. Continue to another pass only when an already-established issue or roadmap lane remains and no stop trigger fired.
