---
name: self-improvement-dogfooding
description: Handle new repo-local improvement findings discovered while dogfooding Agentic Workspace. Use when current work reveals a defect, friction, wasted work, misleading guidance, authority mismatch, or other improvement opportunity outside the task already being executed. Do not use as a general gate for implementing existing issues, Plans, review fixes, or explicit human instructions.
---

# Self-Improvement Dogfooding

This is maintainer guidance for handling **new findings discovered while Agentic
Workspace uses itself**. It is not an ambient workflow for repository work and it
grants no product, mutation, proof, review, or completion authority.

Ordinary implementation follows `AGENTS.md`, the current issue or Planning owner,
and the relevant domain owner. Do not invoke this skill merely because the work is
in this repository, is reconstruction work, or improves Agentic Workspace.

## Activation boundary

Use this skill only when both are true:

1. Current work exposes a concrete improvement finding that is not already the
   intended outcome of the task, issue, approved Plan, review fix, or explicit
   human instruction.
2. The agent must decide whether and how to act on that newly discovered finding.

Once the human or an existing owner explicitly adopts the finding as planned work,
execute that work through the ordinary owner path. This skill adds no second
approval gate.

Examples:

- An issue explicitly requires a typed authority boundary: implement it normally;
  do not ask again because the change touches authority.
- A test run reveals redundant proof work or misleading guidance: this is a
  dogfooding finding; triage it here.
- A discovered fix would redefine the package's product direction or authority
  model: surface the finding and obtain human direction before implementing it.

## Finding triage

1. State the finding in terms of observed behavior, cost, or violated intent.
   Preserve failed or censored evidence; do not upgrade suspicion into fact.
2. Find the smallest existing owner. Prefer repairing that owner over adding a new
   command, store, registry, report, workflow concept, or parallel state surface.
3. Classify the finding:

   - **Bounded defect or friction** — existing intended behavior is wrong,
     misleading, redundant, unnecessarily expensive, or harder to continue than it
     needs to be. If the correction preserves the human-owned why, existing
     authority boundaries, and product shape, fix it autonomously when safe and
     proportionate. No confirmation is required merely because the finding was not
     in the original task.
   - **Evidence or conformance gap** — deterministic behavior exists but current
     proof is missing, stale, or too broad. Repair or run the smallest owner-aligned
     proof and keep closure honest. Do not turn missing evidence into new product
     machinery.
   - **Distinct bounded follow-up** — the finding is real but should not enlarge the
     current patch. Refine the existing issue when it has the same owner/outcome, or
     create a distinct issue only when a genuinely separate owner is needed. Filing
     work does not itself authorize a change of product direction.
   - **Product-shaping change** — resolving the finding would change the human-owned
     outcome, introduce or widen an authority/custody boundary, add or redefine a
     first-line product surface, materially widen package scope, or contradict an
     approved issue/Plan. Present the finding and proposed consequence to the human
     before implementing that change.

4. After a bounded autonomous repair, return to the original task unless the repair
   invalidates its assumptions. Do not let incidental improvement work silently
   replace the user's requested outcome.

## Human review boundary

Ask for human direction because of this skill only when the **newly discovered
finding** requires a product-shaping decision such as:

- changing the intended outcome or an accepted non-goal;
- introducing or materially widening authority, custody, or permission;
- adding or redefining a first-line human- or agent-facing product surface;
- materially broadening an issue or Plan beyond its already approved outcome;
- waiving or bypassing an existing policy, blocker, or owner boundary.

Do **not** ask for confirmation under this skill for:

- implementing an existing issue, approved Plan, or explicit human instruction;
- implementing a planned authority boundary that is already part of that work;
- routine implementation choices and bounded corrections within approved scope;
- addressing review comments or CI failures;
- fixing code, tests, docs, or routing so they match already-established intent;
- subtracting obsolete or redundant machinery when its disposition is already
  determined;
- collecting focused proof for an already-defined outcome.

A domain owner may still require a specific bounded human judgment for its own
operation. That requirement comes from the domain authority, not from dogfooding,
and this skill neither supplies nor removes that judgment.

## Proof and residue

Prove the finding and repair at the smallest useful boundary. Keep implementation
proof separate from independent review and parent closure. Preserve only residue
that makes recurrence, handoff, or verification cheaper; do not create a dogfood
ledger or archive merely to show that the skill ran.

When reporting a material finding, keep it compact:

- `finding`: what was newly observed;
- `action`: fixed autonomously, routed to an owner, or escalated for human direction;
- `proof`: current evidence for the finding and any repair;
- `unresolved`: only the remaining decision or owner gap.

If no new finding was discovered, this skill should leave no visible work or
additional approval step.
