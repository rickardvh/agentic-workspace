# Workspace Reporting Contract

This page defines the compact shared schema used by `agentic-workspace report --format json`.

Use it when you want one derived inspection surface for combined workspace state instead of reading raw module files first.

## Purpose

- Keep workspace reporting compact, machine-readable, and comparable.
- Derive workspace and module summaries from canonical module-owned surfaces.
- Expose next-action guidance without turning reporting into a new source-of-truth store.
- Prefer one bounded question at a time when the report can answer it cheaply.
- Surface setup discovery before any seed writes happen.

## Shared Schema

The report command emits a `schema` object with:

- `schema_version`
- `canonical_doc`
- `command`
- `shared_fields`
- `report_principles`

The surrounding report payload keeps these fields separate:

- `kind`
- `command`
- `target`
- `selected_modules`
- `installed_modules`
- `health`
- `output_contract`
- `execution_shape`
- `findings`
- `next_action`
- `discovery`
- `standing_intent`
- `repo_friction`
- `registry`
- `config`
- `reports`
- `module_reports`

## Authority Boundary

Reportable AW packets may include `authority_boundary`.

Use it to separate:

- `enforced_by_aw`: hard gates or constraints AW is applying.
- `observed_by_aw`: mechanical facts, path buckets, state, or evidence AW observed.
- `recommended_by_aw`: advisory next actions or support signals.
- `candidate_routes`: possible routes AW surfaced without making them semantic authority.
- `proof_hints`: proof burden or validation hints.
- `agent_owned_decisions`: semantic work-shape, route, proof-proportionality, or completion judgments the agent must own.
- `human_owned_decisions`: intent, acceptance, or handoff decisions that require human ownership when present.

Agents should report these categories separately. Do not say "AW classified" or "AW routed" when the boundary says AW only observed facts, suggested a route, or exposed proof guidance. Preserve real hard gates as authoritative when `enforced_by_aw` is non-empty.

### Authority Boundary Examples

Use the authority boundary to write final reports like this:

- `start`: before, "AW classified this as a small task." After, "AW observed no hard blocker and suggested `choose-smallest-workflow-shape`; I judged the task bounded."
- `implement --changed`: before, "AW routed this to direct implementation." After, "AW observed changed paths, named proof hints, and exposed candidate routes; I chose the route and proof scope."
- `report --section closeout_report`: before, "AW decided the work is done." After, "AW reported closeout evidence and hard caveats; I own the completion claim against proof and acceptance."

Dogfooding rule: the in-chat closeout report should be able to say what AW enforced, observed, recommended, and left to agent judgment without using "AW classified" or "AW routed" for advisory signals.

### Canonical Advisory Field Names

Reportable advisory and mechanical packets use names that describe what AW actually provides:

- `gate_result`: planning-safety gate result, including real hard blockers when present.
- `sufficiency_result`: workflow sufficiency status or required evidence result.
- `recommended_route`: delegation or posture recommendation, not an AW-owned semantic decision.
- `changed_path_facts`: observed changed-path buckets and scope facts, not a semantic classification.
- `candidate_route`: surfaced route candidate, not a route AW selected.
- `proof_route_selection`: selected proof route support, not an AW-owned closeout decision.

Legacy compatibility aliases such as `decision`, `changed_path_classification`, `route_candidate`, and `proof_route_decision` may appear in full/internal payloads while existing callers migrate.
User-facing reports and compact projections should prefer the canonical names and should treat compatibility aliases as deprecated.

## Closeout Report Shape

The `closeout_report` object is the operator-facing closeout projection.

It keeps:

- `authority_boundary`
- `profile`
- `profile_policy`
- `work_completed`
- `interpreted_intent`
- `changes`
- `validation`
- `gaps_and_residual_risk`
- `closure_boundary`
- `traceability`
- `completeness`
- `decision_review`
- `review_compression`
- `closeout_adoption`
- `final_response_rendering`
- `next_action`

The profile policy is presentation-only:

- `minimal`: trivial or no-plan closeout with no visible residue.
- `compact`: ordinary bounded work with normal closeout trust.
- `balanced`: active planning or partial evidence needs traceability.
- `explanatory`: continuation, blocked closure, or review needs explanation.
- `audit`: strict closeout, lower trust, incomplete evidence, missing verification, external divergence, or residue routing is present.

The report is derived from Planning, Verification, `completion_contract`, and `closeout_trust`.
It must not become execution state, a proof decision, or a second planning record.
Use `closeout_report.authority_boundary` to distinguish closeout gates and observed evidence from the agent-owned final completion judgment.

Use:

```bash
agentic-workspace report --target ./repo --section closeout_report --format json
```

Use `closeout_report.completeness` to see missing intent boundary, completed-work, changed-surface, validation, residual-risk, follow-up-owner, or traceability evidence before making final closeout claims.
Use `closeout_report.traceability.rows` to connect each intent or requirement to its evidence surface and residual risk or follow-up.

For behavior-preserving refactors, closeout must keep the preservation boundary
separate from ordinary validation. Planning or proof evidence may record:

- `preservation_claims`;
- `allowed_behavior_changes`;
- `unknown_behavior`;
- `proof_classes`;
- `preservation_evidence`;
- `human_confirmation_needed`.

`closeout_report.validation.behavior_preservation` reports those recorded facts,
the evidence classes, unsupported claims, known gaps, and review focus. It must
not infer business behavior from changed paths, filenames, or tests passing. A
`no behavior changed`, `safe refactor`, `business logic preserved`,
compatibility, migration-complete, or dependency-upgrade-compatible claim needs
characterization, golden-master, current-behavior, compatibility, migration
dry-run, manual-scenario, or domain-acceptance evidence, or it must render a
behavior caveat and block broad completion claims.

Use `closeout_report.decision_review` for material system or product decisions.
It is a derived review packet over agent-authored Planning facts, not an AW classifier.
The active owner for decision facts is Planning, primarily `architecture_decision_promotion` and `traceability_refs.decision_refs`.
`closeout_report.decision_review` may render those facts and check completeness, while `report --section decision_pressure` remains the routing and promotion-pressure surface.
When system-shaping signals are present but no decision facts exist, `decision_review.status` should be `absent-required` and `decision_absent_because` must say that no agent-authored facts were found rather than pretending AW inferred the decision.

`decision_review.owner_model` and `decision_pressure.owner_model` describe the proportional ownership split:

- the agent authors semantic decision facts;
- AW derives presence/completeness checks, closeout display, absence visibility, and scaffold/promote routes;
- `decision_pressure` remains routing-only and must not infer decisions from diffs, filenames, or changed paths;
- durable accepted decisions live in host-owned surfaces such as configured decision records, docs or ADRs, Memory, config/checks/tests/contracts, or issue follow-up.

Small, local, or non-system-shaping work should remain decision-light.
Material system-shaping changes should make decision absence visible and routed; absence may block or lower trust only when the claimed work affects public or durable contracts, long-lived operating loops, proof policy, module boundaries, or future-agent guidance.

Decision-review facts are:

- decision made;
- why it was made;
- meaningful rejected alternatives or trade-offs;
- affected subsystem, contract, public behavior, or operating loop;
- proof or validation supporting the decision;
- durable owner;
- promotion status.

Use `closeout_report.review_compression` to see what a human should inspect first for the selected work shape.
It is closeout-first, derived, and non-authoritative.
It is also the first-inspection contract that `closeout_report.final_response_rendering` must honor for user-facing closeout text.
Its modes are:

- `small-direct-edit`;
- `planned-slice`;
- `broad-pr`;
- `system-shaping-change`;
- `behavior-preserving-refactor`;
- `partial-or-lower-trust-closeout`;
- `follow-up-or-residue-heavy-work`.

Every compressed review must either say no material human decision remains beyond ordinary acceptance, or name the human-owned acceptance, risk, handoff, or decision-fact question and its owner.
Every mode must name:

- first-inspection facts;
- rendered facts that must appear in the final response for that work shape;
- secondary detail routes;
- the policy for when raw report/detail inspection is still needed.

For `behavior-preserving-refactor`, the first inspection path should emphasize
semantic-risk surfaces before line-count breadth: changed business-rule paths,
persistence/migration/data-shape code, serialization or public contracts,
dependency/runtime semantics, deleted compatibility paths, updated fixtures or
snapshots, and unproven behavior gaps. These are advisory review targets; the
agent and human own the preservation judgment.

Use `closeout_report.closeout_adoption` as the operator-facing closeout quality rubric.
The rubric asks whether the final response answers:

- what did the agent think the user wanted?
- what changed?
- why is the closure claim honest?
- what proof supports it?
- what remains unproven?
- what follow-up or residue remains?

Terse closeout is acceptable only when `plain_done_allowed` is true and no lower-trust, partial, residue, or decision-gap signal is present.
Broad, lower-trust, partial, or system-shaping work must show proof, closure boundary, residual risk, follow-up owner when present, authority boundary, and system-decision facts or routed absence.

When no active plan exists, `closeout_report.planning_evidence.authority` may be `retained-closeout-evidence` or `archived-planning-evidence`.
Retained closeout evidence is the compact record written when full archive retention was skipped by size guardrails.
Retained or archived evidence may populate the user-facing closeout summary, but it does not restore active Planning state or prove external issue closure.
When refreshed external evidence shows an open issue named by a PR close keyword, closeout trust should explain the residue as `pending-pr-merge` and name the PR or branch plus the post-merge refresh command instead of treating it as ordinary unrouted residue.

Use `closeout_report.final_response_rendering` to turn the report into final user-facing closeout text.
It is a derived rendering packet, not a source of truth.
It keeps:

- `profile`
- `rendering_mode`
- `rendering_guidance`
- `summary_lines`
- `rendered_summary`
- `must_include`
- `must_not_claim`
- `plain_done_allowed`
- `raw_json_allowed`

`final_response_rendering.rendered_summary` is the profile-bound, final-response-ready text packet.
It uses built-in templates for the current rendering mode, such as terse, compact, or evidence-backed.
It keeps:

- `template_id`
- `template_family`
- `rendered_lines`
- `rendered_text`
- `required_fact_coverage`
- `constraints`
- `warnings`

Minimal and guidance-only closeouts without trust, residue, or follow-up signals should stay terse.
Guidance-only closeouts with audit, lower-trust, residue, or follow-up signals should stay compact but still render the caveat and disallow a plain-done claim.
Balanced, explanatory, audit, partial, or lower-trust closeouts should render the material human-facing facts: profile reason, closure boundary, changed work, proof, residual risk, routed residue, and follow-up owner.
System-shaping closeouts should also render decision facts or a decision-gap line from `decision_review`.
Behavior-preserving refactor closeouts should render behavior proof class and
behavior caveat lines when preservation claims exist, especially when ordinary
tests passed but characterization or compatibility proof is missing.
`final_response_rendering.selected_review_mode` and `final_response_rendering.first_inspection_contract` must match `review_compression.selected_mode` and its selected contract so the rendered chat summary cannot drift from the review-compression guidance.
The final response should prefer `rendered_summary.rendered_text` as concise prose or bullets and must not dump raw JSON.
`required_fact_coverage` must make omitted required facts visible before the agent claims completion.
Custom wording or template selection is a future-safe extension only when it cannot hide `must_include`, `must_not_claim`, `plain_done_allowed`, or `raw_json_allowed`.

## Discovery Shape

The `discovery` object is the pre-write, pre-seed setup layer.

It groups candidate surfaces into three buckets:

- `memory_candidates`
- `planning_candidates`
- `ambiguous`

Each candidate item carries:

- `surface`
- `reason`
- `confidence`
- `refs`

## Standing Intent Shape

The `standing_intent` object is the compact effective standing-intent view.

It keeps:

- `canonical_doc`
- `schema_version`
- `promotion_rule`
- `precedence_order`
- `supersession_rules`
- `stronger_home_model`
- `classes`
- `effective_view`

Use it when the question is:

- what durable repo guidance is currently in force?
- which parts are policy, doctrine, active direction, durable understanding, or enforceable workflow?
- which owner surface currently carries each class?
- what rule resolves conflicts across those surfaces?
- when should doctrine or understanding move into config or checks?
- where should newly durable chat-borne guidance be promoted instead of left in chat?

## Execution Shape

The `execution_shape` object is the compact combined answer for the current slice's default execution method.

It keeps:

- `owner_surface`
- `rule`
- `advisory_only`
- `status`
- `sources`
- `default_posture`
- `task_shape`
- `current_slice` when active planning makes one present
- `recommendation`
- `deviation_rule`

Use it when the question is:

- what execution shape should I default to for the current slice?
- does the active planning shape plus local posture justify stronger planning and a bounded executor by default?
- if I choose a different method anyway, where should that deviation remain visible?

## Usage

Prefer:

```bash
agentic-workspace report --target ./repo --format json
```

Use the machine-readable report as the default combined-state inspection path when the question is:

- what modules are installed?
- what is the combined workspace health?
- what output/residue bias is shaping this report's rendering defaults?
- what durable standing intent is currently in force and where does it come from?
- what mixed-agent posture is in effect?
- what default execution shape is recommended for the current slice once active planning state and effective posture are combined?
- what explicit repo-friction hotspots exist right now?
- how repo-directed initiative differs from workspace-self-adaptation under the current policy?
- what concept or routing surfaces are getting large enough to act as concept friction?
- what bounded planning-friction signals suggest unclear seams, proof boundaries, ownership, or minimum-read pressure?
- what bounded validation-friction signals suggest weak seams, bad tranche boundaries, unclear proof contracts, or validation bounce/re-entry?
- what compatible external hotspot artifacts already exist that the workspace can consume instead of recomputing everything itself?
- what agent-produced setup findings have already been preserved as repo-friction evidence?
- what should happen next?
- what state is each installed module in without opening its raw files first?
- what existing repo surfaces look like durable Memory or Planning seed candidates?
- what standing-intent class should a durable repo-wide instruction belong to?
- what literal request the active delegated slice started from and how the current interpretation moved from it?
- what execution bounds and stop conditions currently shape a delegated worker handoff?
- what happened in the current or most recent bounded execution run at a useful level of abstraction?
- what actually changed in that bounded run without broad diff reconstruction?
- how returned delegated work should be reviewed cheaply for scope, proof, and intent fit?
- what dangling larger intent or lower-trust closeout signals currently exist even when no execplan is active?
- which closeout report profile should be used, why it escalated, and which selector produces the operator-facing report?
- whether the operator-facing closeout report is complete, partial, or incomplete before claiming final completion?
- whether optional external planning evidence is present, absent, invalid, or in conflict with checked-in planning visibility?
- whether previously closed archived lanes still look honestly landed or now have reopening evidence that lowers closeout trust?
- what findings or warnings need attention?

Use `agentic-workspace defaults --section intent --format json` when the question is confirmed versus interpreted intent; keep report for combined workspace state.
Use `agentic-workspace defaults --section clarification --format json` when the question is how to ask the smallest useful follow-up.
Use `agentic-workspace defaults --section prompt_routing --format json` when the question is which proof lane or owner should absorb a vague prompt.
Use `agentic-workspace defaults --section relay --format json` when the question is how a strong planner should hand a compact contract to a bounded executor, and `agentic-workspace planning handoff --format json` when the active delegated slice itself needs to be handed off.
Use `agentic-workspace config --target ./repo --format json` when the question is posture alone; keep `execution_shape` for the combined current-slice recommendation.
Use `agentic-workspace memory report --target ./repo --format json` when the question is whether Memory now has a compact ordinary-work pull path; its `habitual_pull` object exposes the baseline bundle, owner boundary, and current proof signals without opening raw memory notes first.
Use `agentic-workspace defaults --section improvement_latitude --format json` when the question is how much evidence-backed repo-friction reduction is welcome by default.
Use `agentic-workspace defaults --section optimization_bias --format json` when the question is how shared report density and residue style should lean by default.
Use the `repo_friction.reporting_destinations` field when the question is where reporting-only findings may surface without creating implicit active work.

If the report already answers the question, stop there.
Only open raw module files or broader docs when the report points you to a follow-on surface or when the missing judgment is semantic rather than operational.

## Guardrails

- Do not treat the report as a second state store.
- Do not require raw module files before the report when the report already answers the question.
- Keep `output_contract` explicit when repo policy affects reporting density or rendered view style.
- Keep findings, warnings, and next-action guidance separate.
- Keep execution-shaping guidance advisory, source-attributed, and compact instead of turning report into a scheduler.
- Keep standing-intent reporting compact, source-attributed, and subordinate to the canonical owner surfaces.
- Keep repo-friction evidence derived and queryable instead of turning it into a second editable state store.
- Keep the repo-directed improvement policy separate from the always-bounded workspace-self-adaptation allowance.
- Keep the default friction-response order explicit: adapt inside the workspace first when that is the honest cheap fix, and only then promote repo-directed improvement when the root problem is genuinely external. See [`.agentic-workspace/docs/signal-hygiene-contract.md`](signal-hygiene-contract.md) for the authoritative adaptive discipline.
- Keep the repeated-evidence threshold explicit as well: repo-directed improvement should require repeated shared evidence that the repo is the real friction source, not one-off agent preference, local taste, or friction the workspace can still remove honestly inside its own surfaces.
- Keep the guardrail explicit as well: if repeated friction still points to repo-owned seams, tranche boundaries, proof boundaries, or ownership problems, reporting should preserve that evidence instead of hiding it behind narrow workspace compensations.
- Treat planning friction as repo-friction evidence when the cheap planning path itself stops being clear because seam, proof, ownership, or minimum-read boundaries are unclear.
- Treat validation friction as repo-friction evidence when otherwise straightforward work keeps stalling at validation because repo seams, tranche boundaries, proof expectations, or rerun/re-entry paths stay unclear.
- Keep validation friction distinct from ordinary bug-fixing, one-off failures, or genuinely difficult domains where the hard part is the domain logic itself rather than validation fit.
- When a repo already has a compatible generated hotspot artifact, prefer consuming it as additional evidence instead of requiring the workspace layer to own the analyzer.
- When setup has already preserved compatible `repo_friction_evidence` findings, consume them as shared repo-friction evidence instead of forcing re-analysis.
- Treat setup findings as a bounded bridge from agent-native analysis into reporting or planning, not as a second analysis framework that tries to preserve every finding class.
- Keep repo-friction policy and evidence as shared workspace-level concerns rather than introducing a new core module for them.
- Keep reporting-only repo-friction follow-through bounded to report output, review output, or already-owned planning residue instead of auto-promoting it into active work.
- Keep module reports compact and derived.
- Prefer `agentic-workspace planning report --format json` and `agentic-workspace memory report --format json` when the question is module state alone rather than combined workspace state.
- Keep concern-shaped subobjects narrow enough that one question does not force unrelated contract domains to load.
- Keep discovery read-only until a setup promotion explicitly decides to seed.
- Keep `agentic-workspace summary --format json` as the planning-side companion surface rather than stretching the workspace report into a second planning schema.
- Keep optional external planning evidence advisory and subordinate to checked-in planning ownership.
- Let optimization bias change report density and rendered text style only; do not let it change report truth, execution posture, or module ownership semantics.
- Keep the optimization-bias surface boundary explicit:
  - honors bias: derived report rendering density, rendered human-facing views, and durable residue style when truth stays unchanged
  - stays invariant: machine-readable report truth, execution method, proof semantics, delegated-judgment boundaries, and ownership semantics
- Treat standing-intent reporting as an inspection and routing surface, not as a new editable source of truth.
- Treat `closeout_report` as derived presentation over Planning, Verification, `completion_contract`, and `closeout_trust`; do not write to it or let profile selection alter execution state.
- Escalate closeout report density for strict, high-risk, lower-trust, continuation-bearing, externally divergent, or incomplete closeout evidence instead of hiding the gap behind a shorter final answer.
- Keep residual risk and follow-up ownership explicit; when either is missing, route the gap to Planning, Verification, Memory, docs/checks, or issue follow-up rather than claiming final closure.

## Relationship To Lazy Discovery

Use [`.agentic-workspace/docs/compact-contract-profile.md`](compact-contract-profile.md) for the selector-shaped answer envelope that should sit underneath the report surface when one answer is enough.

Use [`docs/maintainer/lazy-discovery-measurements.md`](../../docs/maintainer/lazy-discovery-measurements.md) when you want to check whether a narrow query is actually cheaper than a broad dump.

Use `agentic-workspace setup --target ./repo --format json` when the report has already identified a bounded follow-through path and you want the public setup surface rather than the broader combined report.
Use [`.agentic-workspace/docs/standing-intent-contract.md`](standing-intent-contract.md) for the standing-intent classes and owner mapping behind the effective report view.
