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
- what findings or warnings need attention?

Use `agentic-workspace defaults --section intent --format json` when the question is confirmed versus interpreted intent; keep report for combined workspace state.
Use `agentic-workspace defaults --section clarification --format json` when the question is how to ask the smallest useful follow-up.
Use `agentic-workspace defaults --section prompt_routing --format json` when the question is which proof lane or owner should absorb a vague prompt.
Use `agentic-workspace defaults --section relay --format json` when the question is how a strong planner should hand a compact contract to a bounded executor, and `agentic-planning-bootstrap handoff --format json` when the active delegated slice itself needs to be handed off.
Use `agentic-workspace config --target ./repo --format json` when the question is posture alone; keep `execution_shape` for the combined current-slice recommendation.
Use `agentic-memory-bootstrap report --target ./repo --format json` when the question is whether Memory now has a compact ordinary-work pull path; its `habitual_pull` object exposes the baseline bundle, owner boundary, and current proof signals without opening raw memory notes first.
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
- Prefer `agentic-planning-bootstrap report --format json` and `agentic-memory-bootstrap report --format json` when the question is module state alone rather than combined workspace state.
- Keep concern-shaped subobjects narrow enough that one question does not force unrelated contract domains to load.
- Keep discovery read-only until a setup promotion explicitly decides to seed.
- Keep `agentic-workspace summary --format json` as the planning-side companion surface rather than stretching the workspace report into a second planning schema.
- Let optimization bias change report density and rendered text style only; do not let it change report truth, execution posture, or module ownership semantics.
- Keep the optimization-bias surface boundary explicit:
  - honors bias: derived report rendering density, rendered human-facing views, and durable residue style when truth stays unchanged
  - stays invariant: machine-readable report truth, execution method, proof semantics, delegated-judgment boundaries, and ownership semantics
- Treat standing-intent reporting as an inspection and routing surface, not as a new editable source of truth.

## Relationship To Lazy Discovery

Use [`.agentic-workspace/docs/compact-contract-profile.md`](.agentic-workspace/docs/compact-contract-profile.md) for the selector-shaped answer envelope that should sit underneath the report surface when one answer is enough.

Use [`docs/lazy-discovery-measurements.md`](docs/lazy-discovery-measurements.md) when you want to check whether a narrow query is actually cheaper than a broad dump.

Use `agentic-workspace setup --target ./repo --format json` when the report has already identified a bounded follow-through path and you want the public setup surface rather than the broader combined report.
Use [`.agentic-workspace/docs/standing-intent-contract.md`](.agentic-workspace/docs/standing-intent-contract.md) for the standing-intent classes and owner mapping behind the effective report view.
