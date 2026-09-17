# Operational Affordance Design

## Purpose

Design AW interactions so an agent can do useful work without first learning the package's internal architecture. This guide applies the [design principles](../design-principles.md) to source delivery, questions, actions, proof and continuation. The [canonical skill](../../.agentic-workspace/skills/workspace-startup/SKILL.md) remains the ordinary agent procedure; this is maintainer design guidance, not another operating loop.

## Core principle

An affordance should make the next useful decision or authorized action understandable and constructible. Ask what uncertainty the interaction addresses, which decision it can change, and whether a cheaper trustworthy route would suffice.

Use decision-relevant information gain as a design heuristic, not a score to compute. A failed test or contradictory source may reveal that the agent knew less than it thought. That is useful information, not a failure to reduce uncertainty. Executing work and recording required effect custody can also be necessary without producing new knowledge.

Authority, safety, currentness and mandatory proof constrain the available choices. Apparent information value cannot authorize an effect or replace required review.

## Design target

Prefer the current decision frontier over an inventory of everything AW can do. The frontier may expose direct work, one exact action, several legitimate alternatives, a bounded judgment, or recovery. Do not invent a single primary action when the owner has not settled the choice.

Skills teach reusable methods. Owners supply current facts, requests, effects and claim limits. The agent supplies semantic judgment. Deterministic helpers may carry already-selected and authorized mechanics until a real judgment, currentness or authority boundary appears; they must not become blind action loops.

## Current-state sufficiency

The current decision must be understandable from current owner state, relevant source references and explicit unresolved facts, not from having witnessed the conversation that produced it. This is a design goal for AW's supported operational boundary, not a promise that the repository is fully observable or that an agent can solve the whole task from one response. The agent still supplies changed task meaning or scope that owners cannot observe.

When delivering a fact, make its subject, scope and current decision consequence clear. For example, a compatibility constraint should arrive with the API decision it constrains, not as an unexplained note that the agent must remember until much later. If that constraint is irrelevant now, keep its source lazy. When later scope makes it relevant, expose the current constraint or exact read route at that point.

Re-anchor meaning, not necessarily bytes. A continuing consumer can reuse unchanged material it still has. A fresh consumer or one whose context is no longer available must not inherit a delivery-suppression assumption. Delivery neither proves understanding nor replaces owner currentness. Dependencies and source-set membership, not every unrelated commit, determine reconsideration.

At a meaningful custody boundary, retain enough outcome, accepted progress, assumptions, open questions, effect disposition and exact refs for continuation through the existing owner. Do not persist every observation or require a new universal state record. A result-only delta can supplement current state but must not be the sole entry path for a fresh agent.

Optional carriers can be discarded and reconstructed from current owners. Actual loss of unique evidence or local effect custody is a different state: report the missing evidence and supported recovery. Never infer an effect did not happen from a lost continuation, or manufacture safe replay to make two histories look equivalent. Historical evidence remains useful when explicitly read for the current question.

## Operational affordance review

For the changed surface, ask:

- What does the consumer need to decide or do now, and which missing fact could change that?
- Is there an exact source, operation or bounded question that can resolve it without broad discovery?
- Could a cheap upstream observation prevent expensive work on an invalid branch?
- Are mandatory restrictions and legitimate alternatives visible, even when deeper detail is lazy?
- Is small certainly-required material delivered together, while optional material stays selective?
- Can a knowledgeable agent use a known route directly, and can an unfamiliar agent discover it without protocol reconstruction?
- Does the proposed saving include interpretation, tool calls, retries, human attention, proof and later maintenance rather than just displayed bytes?

These are design questions, not fields to add to every response or a checklist every task must execute. Independent observations may be batched when that is cheaper; dependency ordering does not imply one observation per model turn or a universal ranking algorithm.

## Warning and Gate Posture

Show a warning when it changes an action, a claim, a required observation, or an explicit trust boundary. Explain the affected scope and route to the responsible owner. Uncertainty should constrain only the dependent action or claim unless governing authority makes it task-global.

Advisory background stays optional. Semantic applicability is agent judgment admitted through current contracts, not inferred as hard policy from keyword matches. Unknown, absent, inapplicable and conflicting remain different observations.

## Examples

These are interaction-design examples, not new command or packet schemas.

### Startup

Instead of a fixed reading list, let the canonical skill and current task identify useful sources. Use `start` when current composition is needed; a known exact source or dedicated operation may be sufficient. A direct task need not acquire a plan or an uncertainty-assessment step.

### Human clarification

Instead of “clarify the API change,” explain: “The current contract does not settle whether existing clients must keep accepting the response. That determines whether this proposed response shape is admissible.” Request the bounded compatibility decision only when current sources and standing authority cannot settle it. Do not force a binary answer when the alternatives are incomplete; preserve clarification or insufficient evidence as appropriate.

### Proof

Instead of returning every available check, show which unresolved claim or failure mode each applicable method addresses and which current evidence already contributes. A compatibility check may answer a question that another generic test run does not. Similar scope alone does not prove redundancy. The owner keeps mandatory floors; the agent judges genuine sufficiency or method alternatives. A genuinely sole required, authorized executable action needs no model selection ritual.

### Closeout

Instead of an unconditional closeout-helper sequence, show the consequence of the admitted result and what remains required. “Selected check passed; independent review remains” is different from “task complete.” Stop optional investigation when it cannot materially change the supported outcome, without waiving work, review, proof or required reconciliation.

### Planning state

Separate intended outcome, accepted progress, assumptions, blockers and next useful work from activity history. Retain only what helps continuation or verification. Do not make a feature branch mirror changing PR, CI or provider status; obtain those observations from their current owners when needed.

## Relationship to validation

Apply the [testing strategy](testing-strategy.md): evidence design, current validation and permanent retention are different decisions. Inspect existing owner and integration evidence before adding tests. A missing observation in this audit is not automatically a missing implementation.

For an information-efficiency change, use a representative choice where an early observation can rule out costly downstream work, plus a direct or unrelated control. Observe the action or claim consequence, not just whether a resource was read. Reuse existing frontier, proof and continuation cases when they cover the same failure class. Additional permanent coverage must protect a distinct durable risk.

Compare total observable burden with equal access to authoritative information. Do not give one comparison an oracle-selected answer or forbid ordinary repository improvements in the baseline. Report missing costs as unknown and negative results honestly. No numerical entropy measurement, model-confidence estimate, transcript capture or production telemetry is required.

For a continuity change, compare two histories that converge on the same decision-relevant task, owner state, authority, evidence/effects and available environment observations. Compare permissible actions, unresolved questions, claim limits and constructible recovery, not timestamps, opaque handles, identical tool sequences or identical model prose. Use a fresh consumer without parent chat or disposable delivery/carriage context. If one history genuinely lost evidence, expect an explicit gap instead of treating it as equal state.

A delayed-relevance case should make an existing source matter after a scope or source-set change; the consumer must obtain its current consequence without remembering the earlier delivery. Pair it with valid same-consumer reuse and an unrelated-change control. Reuse current frontier, delivery, recovery, Planning and worker-entry tests; extend only a demonstrated missing behavior class. Loss of a required evidence store is not a disposable-cache test.

A source audit can identify a likely seam and shape a focused test. It cannot claim a runtime defect, improvement or universal attention-model benefit without corresponding evidence. Broad ordinary-use payoff belongs to the existing evaluation owners, not a new release gate.

## Relationship to prose reduction

Return enough context to interpret the decision and exact references to inspect it. Let tools carry immutable protocol fields rather than requiring the model to reproduce them. Do not remove purpose, scope or claim limits merely to shorten output. A compact response that needs several reconstruction calls can be more expensive than a slightly larger sufficient one.

## Relationship to Memory and Planning

Use the strongest appropriate existing owner for a useful consequence. Work continuity belongs with Planning; advice with Memory; reusable procedure with skills; binding policy with its repository or human authority. Code, tests or documentation may absorb a recurring lesson more directly. Recurrence does not turn advisory evidence into policy. No retention is a valid outcome; neither Memory nor Planning is a mandatory sink.

## Anti-patterns

Avoid forced primary actions, full inventories followed by model filtering, repeated requests for an already-settled choice, proof selected by command count, and new scoring or uncertainty stores. Do not fix a deterministic owner defect with permanent warnings elsewhere. Never mistake delivery, helper success or owner-local quietness for whole-task completion.

## Success signal

An unfamiliar agent can identify the current decision, reach its useful evidence and act within the actual constraints. A knowledgeable agent can go directly to sufficient sources and tools. Both can stop at a supported outcome without a mandatory discovery, planning or retrospective ceremony.
