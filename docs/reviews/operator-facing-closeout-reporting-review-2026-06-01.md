# Operator-Facing Closeout Reporting Review

## Report Header

- Host repo: `agentic-workspace` source checkout used as package dogfood
- Report date: `2026-06-01`
- Reporter / agent runtime: ChatGPT in the Agentic Workspace project context
- Package source: repository surfaces inspected through the GitHub connector
- Installed preset/modules observed: repo config indicates `full`; workspace, planning, and memory installed
- Review goal: evaluate how Agentic Workspace should make agent-completed work, decisions, validation, and remaining gaps understandable to the human operator after each turn or tranche
- Slice type: product direction / operator-facing reporting design review

## Problem / Intent

Codex and other agents can usually summarize what changed and how it was validated for the immediately preceding turn. That summary is narrow, chat-local, and often insufficient for larger tranches, whole features, or epics.

As agent-authored work grows in scope, the human operator remains responsible for the delivered code and needs to understand what was produced, why it was shaped that way, what evidence supports it, and what remains unproven. Agents should be held to the same or a higher standard for documentation and code structure, but they cannot be expected to answer system questions accurately from chat memory alone.

Agentic Workspace already preserves much of the underlying state: intent, planning, proof, handoff, verification, closeout trust, durable memory, workflow obligations, and reporting density. The gap is that these surfaces are mostly optimized for agent routing and internal continuity. The operator-facing explanation after a turn remains too dependent on the agent's local summary habits.

## Current Substrate

Existing repo surfaces already support most of the needed capability:

- `README.md` frames AW as a repo-native operating layer for preserving intent, recovering context, validating changes, and handing off safely without relying on chat history.
- `docs/package/overview.md` describes AW as an amortized coordination layer that avoids rediscovery, stale context, weak proof, unsafe handoff, and unreviewable output.
- `.agentic-workspace/docs/reporting-contract.md` defines report output as compact, machine-readable, derived from canonical module-owned surfaces, and not a second source-of-truth store.
- `src/agentic_workspace/contracts/optimization_bias_policy.json` already separates rendering density from invariant truth, proof requirements, execution method, and ownership semantics.
- `src/agentic_workspace/reporting_support.py` already has router/full/section report profiles and a compact `closeout_trust` section.
- `.agentic-workspace/config.toml` already has assurance, strict closeout, optimization bias, and workflow obligations that push agents to separate validation success, issue completion, intent satisfaction, and operating-cost direction before claiming completion.

The proposed work should therefore avoid a new heavy module. It should add a configurable operator-facing closeout / explanation projection over existing state.

## Product Recommendation

Add configurable **operator-facing closeout reporting**: a rendered view over existing AW state that makes work traceable and reviewable without turning every turn into an audit package.

This should not be framed as "more verbose summaries." The stronger product frame is:

> Make the human operator's accountability cheaper by producing configurable, evidence-backed explanations of what landed, why, how it was validated, what remains unproven, and whether closure is honest.

## Proposed Reporting Profiles

Introduce a closeout reporting policy with profiles that change rendered density only, not canonical truth.

| Profile | Use case | Shape |
| --- | --- | --- |
| `minimal` | no-code answers, tiny edits, low-risk hobby work | changed / validated / remaining |
| `compact` | ordinary small implementation turns | intent / changed / proof / residuals |
| `balanced` | default for meaningful feature work | traceable narrative with bounded detail |
| `explanatory` | larger tranche or user wants understanding | material decisions, alternatives, boundaries, proof, residual risk |
| `audit` | high-risk work, handoff, PR review, enterprise use | structured traceability table plus evidence refs |

Suggested config shape:

```toml
[closeout_reporting]
default_profile = "balanced"
escalate_for = [
  "broad_work",
  "strict_closeout",
  "public_api",
  "architecture_decision",
  "migration",
  "security",
  "external_user_impact",
]
include_traceability = true
include_decision_notes = "when_material"
include_validation_detail = "evidence_summary"
include_residual_risk = true
include_operator_questions = true
```

This should integrate with existing `optimization_bias` rather than replace it. Optimization bias can still influence terse versus explanatory rendering, but it must not weaken proof requirements or machine-readable report truth.

## Operator Questions The Report Should Answer

A useful post-turn report should answer the questions a responsible human operator needs answered:

1. What did the agent believe the user wanted?
2. What landed, in behavior and affected surfaces?
3. Why was this implementation shape chosen?
4. How does it map back to the plan, issue, prompt, or intended outcome?
5. How was it validated?
6. What is not proven?
7. What state was updated for continuation?
8. Can the user honestly treat this as done?

The last question is the most important. The report should separate:

| Claim | Meaning |
| --- | --- |
| `slice_landed` | The bounded task was completed. |
| `intent_satisfied` | The larger intended outcome is satisfied. |
| `proof_sufficient` | Evidence supports the claim being made. |
| `safe_to_close` | No known required continuation remains. |
| `follow_up_required` | Work landed, but closure is not honest yet. |

## Traceability Shape

For larger tranches, include a compact traceability table:

| Intent / requirement | Implementation surface | Evidence | Status |
| --- | --- | --- | --- |
| Support a requested behavior | code, docs, config, or generated surface | test, check, review, or manual proof | landed / partial / unproven |
| Preserve package quietness | `.agentic-workspace/` or package-owned surface | diff review / ownership check | satisfied / attention |
| Maintain future continuation | planning state, issue, review doc, memory | summary/report/closeout evidence | satisfied / follow-up |

For `audit`, expose the same shape in JSON so downstream agents, reviewers, or scripts can consume it:

```json
{
  "intent_refs": [],
  "change_refs": [],
  "decision_refs": [],
  "proof_refs": [],
  "residual_risks": [],
  "continuation_refs": []
}
```

## Suggested Rendered Report Template

For `balanced` or `explanatory` profile:

```markdown
## Work completed

One-paragraph summary of the landed slice.

## Intent interpreted

- Original request:
- Working interpretation:
- Scope boundary:

## Changes

- Surface:
- Behavior:
- Files/modules:

## Decisions

- Decision:
- Reason:
- Alternatives not taken:

## Validation

- Passed:
- Not run:
- Manual/soft verification:
- Evidence boundary:

## Traceability

| Intent | Change | Evidence | Status |
| --- | --- | --- | --- |

## Remaining gaps

- Residual risk:
- Follow-up owner:
- Whether larger intent is fully satisfied:
```

For `minimal` profile:

```markdown
Changed:
Validated:
Not proven / remaining:
```

## Escalation Rules

The default profile should come from config, but work shape should be allowed to escalate the rendered report detail.

| Trigger | Suggested minimum profile |
| --- | --- |
| no code changes / answer-only | `minimal` |
| small contained edit | `compact` |
| active execplan or issue-backed task | `balanced` |
| strict closeout enabled | `balanced` |
| broad file spread or multi-step tranche | `explanatory` |
| architecture, API, data migration, security, or proof-sensitive work | `audit` |
| failed validation or partial completion | `balanced` or higher |
| user asks why, whether something is done, what remains, or whether it can be trusted | `explanatory` |

## Residue Routing

Do not treat the rendered report as a new durable state store. Route durable content to the strongest existing owner surface:

| Information type | Default destination |
| --- | --- |
| turn-local change summary | in-chat only |
| proof evidence | closeout report / planning evidence |
| unfinished work | Planning |
| expensive-to-rediscover repo lesson | Memory |
| stable architecture decision | ADR / decision surface |
| repeated friction | issue / improvement intake |
| user-facing behavior | docs only when docs are part of the product contract |

This keeps the feature consistent with AW's low-residue, repo-native posture.

## Mixed-Agent Compliance

Do not assume every agent will voluntarily write a good closeout explanation. Make the correct path cheap and omissions visible:

- startup/report output should tell the agent which closeout profile applies;
- strict closeout should degrade trust when evidence, residual risk, or follow-up owner is missing;
- a closeout check should report missing fields;
- a generated skeleton should give agents a low-effort path;
- unknowns should be explicit instead of omitted.

## Proposed Implementation Lane

Break the work into a parent direction issue with child slices:

1. Define configurable closeout reporting profiles.
2. Add a derived operator-facing closeout report projection.
3. Add traceability rows to closeout output.
4. Wire closeout profile expectations into startup/report routing.
5. Add closeout completeness checks.
6. Document the operator-facing reporting contract.

## Closure Boundary

This review is not implementation. It records the product direction and suggested decomposition.

Final satisfaction for the overall direction requires a configurable, profile-driven operator-facing closeout report that is derived from existing AW state, makes closure honesty explicit, and gives agents a cheap compliant path without turning ordinary small work into mandatory audit ceremony.
