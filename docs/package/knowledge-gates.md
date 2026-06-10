# Pre-Work Knowledge Gates

Knowledge gates are compact startup and work-shaping decisions that prevent
blind starts. They apply when known sources may change task interpretation,
work shape, proof burden, allowed actions, or completion claims.

A gate is not a reading list. It names the smallest governing source or selector
that can answer the shaping question, then states what work is allowed before
that source is consulted, dismissed, refreshed, or escalated.

Knowledge gates build on [Knowledge routing and source
authority](knowledge-routing.md). Source authority decides what can govern a
task; a gate decides whether that governance must be handled before design,
editing, proof, or closeout.

## Gate Record Model

Command outputs and future contracts should use these names when they project a
knowledge gate:

| Field | Meaning |
| --- | --- |
| `gate_id` | stable local identifier for the gate decision |
| `route_id` | referenced `knowledge_route` from the source-authority model |
| `surface` | `start`, `implement`, `summary`, `preflight`, `report`, `proof`, or `closeout` |
| `trigger` | why the route may change this task |
| `force` | how strongly the gate constrains work |
| `reason` | short explanation of the task-shaping risk |
| `next_allowed_action` | smallest safe next action |
| `forbidden_actions` | actions blocked until the gate is resolved |
| `required_actions` | consult, dismiss, refresh, prove, capture, promote, demote, or escalate |
| `record_resolution_to` | owner surface for evidence or dismissal |
| `resolution_state` | `open`, `consulted`, `dismissed`, `stale`, `missing`, `unavailable`, `captured`, or `superseded` |
| `block_claims` | completion or issue-closure claims blocked by the gate |
| `fallback` | safe behavior when a CLI, source, or external access is unavailable |

The gate record should be omitted when no route can change the current work.
Commands may expose a count or selector when a gate exists but should not dump
all known knowledge routes by default.

## Trigger Sources

Knowledge gates can be triggered by:

- task text naming issues, PRs, modules, external sources, proof expectations,
  source authority, durable knowledge, or closeout pressure;
- issue or PR references whose current comments, state, labels, or reviews may
  change requested outcome or merge safety;
- changed paths matching module roots, generated references, schema contracts,
  installed startup adapters, Memory notes, Planning state, or Verification
  protocols;
- active Planning state that owns lane order, continuation, parent-intent
  closure, or stop conditions;
- Memory routes that report durable knowledge, stale notes, promotion pressure,
  or chat-derived knowledge that needs a stable owner;
- Verification protocols that can change proof selection, evidence collection,
  or known-gap reporting;
- module participation declarations that match the current loop step;
- configured `workflow_obligations` for the current stage or scope;
- external source freshness policies that require current vendor, legal,
  platform, or product behavior before design or claim;
- closeout residue that must be captured or dismissed before the work can be
  honestly claimed complete.

The route must explain why the trigger may change the task. A path match alone
is not enough to block work unless the matched source can alter interpretation,
allowed action, proof, or closeout.

## Force Levels

Use one of these force levels:

| Force | Effect |
| --- | --- |
| `informational` | show compact context, but do not constrain work |
| `recommended_before_work` | advise consultation before work; skipping must be visible if it affects confidence |
| `required_before_design` | block architecture or work-shape decisions until resolved |
| `required_before_edit` | block file edits until resolved |
| `required_before_claim` | allow work but block completion, merge, or issue-closure claims |
| `stale_check_required` | require freshness verification before treating the source as governing |

The force should be the minimum needed to protect the task. A gate can lower
force after consultation, dismissal, or a freshness check.

## Gate Effects

Gate effects should be explicit:

- block architecture choice until the source is consulted or dismissed;
- block edits until repo-owned intent, active Planning state, or source
  freshness is checked;
- block completion claims until required external or tracker authority is
  verified;
- lower closeout trust when recommended or required knowledge was skipped;
- route durable chat-derived knowledge to Memory, docs, Planning, or issues
  before it disappears;
- expose conflicts between sources instead of choosing a policy winner silently;
- require escalation when the source is unavailable and no lower-authority path
  is acceptable.

Forbidden actions should be concrete. Prefer "do not change schema fields until
the generated reference owner is checked" over generic "do not proceed" text.

## Command Integration

`start` should emit only gates that affect the first safe action. It may include
the gate id, force, source selector, reason, next allowed action, and blocked
claim classes. It should not emit broad route lists.

`implement --changed` should combine task text with changed paths. It should
raise gates for active Planning ownership, generated-reference freshness,
module-owned rules, workflow obligations, Memory promotion pressure, and
Verification protocols when those sources can change implementation or proof.

`summary` should preserve active Planning gates and claim boundaries. It should
make a missing active owner or stale follow-up route visible before work
continues.

`preflight` should bundle startup and active-state gates for takeover or
recovery. It should prefer selectors and detail commands over raw source
content.

`report` should expose gate health: open gates, resolved gates, stale sources,
missing sources, unavailable sources, and claim-limiting gates.

Work-shape skills should treat gates as posture input. A required gate changes
whether the next step is direct implementation, design, investigation,
verification, closeout, or escalation.

## Task Posture Fields

A task posture packet may include:

| Field | Meaning |
| --- | --- |
| `knowledge_gates` | compact list of gates relevant to the current task |
| `gate_summary` | count by force and resolution state |
| `blocked_actions` | concrete actions currently forbidden |
| `blocked_claims` | completion or issue-closure claims currently forbidden |
| `next_allowed_action` | smallest safe action across all active gates |
| `resolution_routes` | owner surfaces or commands for consultation, dismissal, refresh, or capture |
| `gate_conflicts` | source conflicts that need owner or human resolution |

The packet should include gate detail only when the gate changes action. Other
routes remain available through selectors.

## Closeout And Report Evidence

Closeout and reports should record gate resolution using these states:

- `consulted`: the source was checked and shaped the result;
- `dismissed`: the source matched but did not apply, with a reason;
- `stale`: the source was found but could not govern without refresh;
- `missing`: an expected source did not exist;
- `unavailable`: the source exists but could not be accessed;
- `captured`: new reusable knowledge moved to the right owner;
- `superseded`: a newer source replaced the route.

If a required gate remains open, closeout must block completion claims or route
the unsatisfied work to a durable owner. If a recommended gate was skipped,
closeout should lower confidence or explain why the skipped source could not
change the result.

## Fallback Behavior

When the CLI cannot emit gate detail, use the normal source authority model:
identify the owner surface, read the smallest routeable selector, and record the
fallback in closeout.

When external access is unavailable, do not invent freshness. Treat the route as
`unavailable` or `stale_check_required`, then either block claims, use a
lower-authority design posture, or escalate.

When Memory is not installed, route durable knowledge capture to docs, Planning,
issues, or local-only notes according to source authority. Do not silently turn
chat context into checked-in authority.

When active Planning state is missing or stale, do not close parent intent from
local evidence alone. Promote, repair, or explicitly route the missing owner
before claiming completion.

## Compact Audit Rules

Knowledge gates stay compact by following these rules:

- emit gates only when a source may change task interpretation, work shape,
  proof, allowed action, or completion claim;
- emit selectors and detail commands before raw source content;
- include source owner, force, next allowed action, blocked actions, and evidence
  route;
- keep local-only and inferred sources below hard-gate authority unless they are
  explicitly promoted;
- do not require external web lookup unless the source authority or freshness
  policy requires current external state;
- never mirror issue threads, external docs, or Memory bundles into gate output;
- make skipped required gates visible in closeout instead of hiding them behind
  successful tests.

These rules let gates prevent blind starts without making ordinary startup a
general knowledge search.
