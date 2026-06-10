# Knowledge Routing And Source Authority

Agentic Workspace owns a routing layer for governing knowledge. It does not
become a general search engine, a documentation mirror, or the canonical owner
of every source it can point at.

The routing layer answers three operating questions:

- which knowledge source can govern this task;
- how strong that source is for the current decision;
- what evidence must remain visible at closeout.

The answer should be compact enough for ordinary startup. Deep source reading is
selected only when a route trigger makes it relevant.

## Route Record Model

Runtime packets, reports, and future contracts should use these model names when
they project knowledge routes. The design is additive: a command may omit a
field when no matching route exists, but it should not invent a different source
authority vocabulary.

`knowledge_source` describes the source being routed:

| Field | Meaning |
| --- | --- |
| `source_id` | stable local identifier for this source reference |
| `kind` | one of the source kinds in this document |
| `locator` | path, URL, issue/PR reference, command, or owner-specific pointer |
| `owner_surface` | source that owns updates and conflict resolution |
| `authority_class` | one of the authority classes in this document |
| `freshness_state` | `fresh`, `needs_review`, `stale`, `stale_or_superseded`, or `unknown` |
| `freshness_policy` | when to check, what makes it stale, optional refresh command, and stale reason |

`knowledge_route` describes why the source applies now:

| Field | Meaning |
| --- | --- |
| `route_id` | stable local identifier for this route decision |
| `source_id` | referenced `knowledge_source` |
| `stage` | `startup`, `implement`, `report`, or `closeout` |
| `trigger` | task text, changed path, active state, module declaration, obligation, stale marker, review state, or closeout residue |
| `force` | `informational`, `recommended`, `required_before_design`, `required_before_edit`, `required_before_claim`, or `required_at_closeout` |
| `read_budget` | `selector`, `compact_projection`, or `raw` |
| `selector` | compact field, command, or route key to inspect first |
| `detail_command` | optional command for deeper source detail |
| `mirror_policy` | one of the mirror policies in this document |
| `capture_intent` | `ignore`, `capture`, `promote`, or `demote` |

`knowledge_gate` describes blocking or claim-limiting behavior:

| Field | Meaning |
| --- | --- |
| `surface` | command output, report section, closeout surface, or proof surface carrying the gate |
| `required_when` | condition that makes the source required |
| `missing_required_source` | source or class that was expected but not available |
| `required_actions` | freshness check, source read, promotion, dismissal, proof, or escalation needed |
| `block_claims` | whether the gate blocks completion or issue-closure claims |
| `escalation` | human, repo owner, module owner, issue, or follow-up route when the gate cannot be satisfied locally |

## Source Kinds

Knowledge routes may point at these source kinds:

| Kind | Canonical owner | Typical use |
| --- | --- | --- |
| repo doc | the checked-in document or owning package area | current package behavior, local architecture, public or maintainer guidance |
| external doc | the external publisher | vendor APIs, platform rules, legal or product facts that can change outside the repo |
| issue | the issue tracker | requested outcome, acceptance pressure, parent epic context, stakeholder comments |
| PR | the pull request and review threads | proposed change, review decisions, merge blockers, branch-specific evidence |
| ADR or decision record | the decision record location named by the repo | accepted durable decisions and supersession history |
| generated reference | the generator input contract | field-level schema or command reference generated from source contracts |
| Memory note | `.agentic-workspace/memory/` when installed | durable anti-rediscovery knowledge that is cheaper to preserve than rediscover |
| Planning state | `.agentic-workspace/planning/` when installed | active execution ownership, continuation, lane ordering, and closeout state |
| Verification protocol | verification module or repo-native proof contract | proof routes, evidence expectations, stale conditions, and known gaps |
| human or chat capture | the specific human confirmation or captured transcript | high-context intent that must be promoted, dismissed, or treated as local-only |

A route records the owner. Agentic Workspace may select, summarize, or project a
route, but the owner remains the source named by the route.

## Authority Classes

Every routed source should be treated as one of these authority classes:

| Authority class | Meaning | Conflict handling |
| --- | --- | --- |
| canonical repo | checked-in source owns current repo behavior | update or link this source before claiming a different repo rule |
| module-owned | a module contract, README, or manifest owns the rule | defer to the module owner unless root orchestration explicitly overrides it |
| generated from contract | generated reference projects a machine-readable source | change the source contract and regenerate, not the generated page alone |
| external authoritative | external publisher owns the fact | verify freshness before design or claim when the fact may have changed |
| tracker intent | issue or PR owns requested outcome, review pressure, or merge state | preserve parent and child issue boundaries; do not close parent intent accidentally |
| human-confirmed | an explicit human message governs the current slice | capture the decision into the right durable owner before it becomes hidden memory |
| Memory durable | Memory owns reusable anti-rediscovery context | promote to docs or config if it starts governing product behavior |
| Planning active | Planning owns current execution state | close or archive only when the intended work is actually satisfied or routed |
| local-only | machine-local, private, or low-confidence knowledge | do not check in or generalize without explicit promotion |
| inferred | agent inference from evidence | expose as inference and seek a stronger owner before making it a hard rule |

When sources conflict, the route should surface the conflict and name the likely
owner that can resolve it. Agentic Workspace should not silently choose a policy
winner when the choice changes accepted workflow.

## Route Triggers

Routing is triggered by evidence, not by a global reading list. Common triggers
are:

- task text naming an issue, PR, module, source, workflow, proof expectation, or
  source-authority concern;
- changed paths matching a module root, generated reference, schema, installed
  surface, Memory note, Planning state, or Verification protocol;
- active Planning state that owns the current lane, continuation, closeout, or
  stop condition;
- module participation declarations that match the loop step or posture need;
- configured `workflow_obligations` that apply to the current stage or scope;
- stale evidence markers, unresolved review comments, or known proof gaps;
- closeout residue that contains reusable knowledge, parent-intent pressure, or
  a source ownership conflict.

Startup should emit compact route selectors by default. It should emit raw
source content only when the trigger is strong enough to change the allowed next
action, proof burden, task interpretation, or closeout permission.

## Mirror And Reference Policy

Agentic Workspace routes to sources; it mirrors only when mirroring has an owner
and a maintenance rule.

| Policy | Use when | Boundary |
| --- | --- | --- |
| reference-only | the source is canonical and easy to reach | keep a locator and reason, not a prose copy |
| compact projection | startup or report needs a small decision-relevant extract | include provenance and freshness state |
| generated reference | a source contract can regenerate the projection | never hand-edit generated authority |
| Memory capture | a durable fact prevents repeated rediscovery | keep it compact and routeable; do not store execution history |
| docs promotion | a Memory note or repeated route now governs product behavior | move the governing statement into canonical docs or contracts |
| local-only capture | the knowledge is private, machine-specific, or uncertain | keep it out of checked-in repo state unless explicitly promoted |
| no mirror | external terms, volatile docs, or broad source material | point at the source and require freshness verification |

Broad copied docs, unchecked external snapshots, and issue-thread dumps are not
valid mirrors by default.

## Freshness And Staleness

Freshness is route-specific:

- repo docs and contracts are fresh at the checked-in revision unless their
  owner says they are generated or stale;
- generated references are stale when their source contract changed without
  regeneration;
- external docs are stale when the task depends on current behavior and the
  source could have changed since the last verification;
- issues and PRs are stale when new comments, review states, labels, or merge
  status can change the intended outcome;
- Planning state is stale when it no longer includes the active or queued lane
  that owns known follow-up work;
- Memory notes are stale when they conflict with canonical docs, current code,
  or a newer decision record;
- Verification protocols are stale when changed paths or proof expectations
  fall outside the evidence they name.

A stale route can still be useful, but it cannot be treated as governing without
a freshness check or an explicit lower-authority posture.

## Task Posture Integration

Knowledge routing participates in the task posture packet as a selector, not as
a default context dump. When a selected route must constrain work before design,
editing, proof, or closeout, it becomes a [pre-work knowledge
gate](knowledge-gates.md). A posture packet may include:

- selected knowledge routes and why they matched;
- each route's source kind, authority class, owner, locator, and freshness
  state;
- whether the route is informational, recommended, required before design,
  required before edit, required before claim, or required at closeout;
- conflicts between matched routes;
- capture obligations for closeout.

The packet should include only routes that can change task interpretation,
allowed action, proof burden, output shape, review rubric, or closeout
permission. Other known sources remain discoverable through module docs and
owner maps.

## Startup And Work Shaping

Startup and work-shaping commands should apply this sequence:

1. Read task text, changed paths, active Planning state, module declarations, and
   configured obligations.
2. Select compact route candidates with source kind, authority class, owner, and
   reason.
3. Mark the force of each route: informational, recommended, required before
   design, required before edit, required before claim, or closeout-only.
4. Emit the smallest useful posture. Include deep source content only when the
   selected route changes the next safe action.
5. Preserve unresolved conflicts and stale-route warnings instead of hiding them
   behind a generic "context loaded" claim.

This keeps ordinary startup small while making high-consequence knowledge
visible before work begins.

## Closeout And Capture

Closeout should account for routed knowledge when it affected the work. Useful
states are:

- consulted: the source was checked and shaped the result;
- dismissed: the route matched but did not apply, with a reason;
- stale: the source was found but could not govern without refresh;
- unavailable: the source was expected but inaccessible;
- captured: new reusable knowledge was moved to the right owner;
- promotion-required: hidden or local knowledge now needs a durable owner;
- superseded: a newer source replaced the route.

Closeout must not claim the larger intent is complete merely because a local
route was recorded. Parent epics, active Planning lanes, and tracker issues keep
their own closure rules.

## Memory Promotion And Demotion

Memory is a durable anti-rediscovery owner, not a shadow documentation system.

Promote into Memory when a compact fact, invariant, mistake, runbook, or routing
hint is durable, non-private, reusable, and cheaper to preserve than rediscover.
Promote from Memory into canonical docs, config, contracts, or ADRs when the fact
starts governing product behavior or contributor obligations.

Demote or remove Memory authority when the note is stale, duplicated by a
canonical source, too broad to route, local-only, or only records one execution
history. Planning remains the owner for active work; Memory should not become a
backlog or closeout archive.

## Relationship To The Next Lanes

For #1390, each investigated operating-loop step should classify its governing
knowledge sources and decide whether they should be hidden, compact selectors,
task-posture fields, proof gates, or closeout capture obligations.

For #1391, each surface audit should identify whether the surface is a source
owner, a route projection, a generated reference, a diagnostic, or residue that
needs promotion or demotion.

Both lanes should use this model to reduce startup burden. They should add route
triggers and posture fields only where the selected knowledge can change an
agent's next safe action.
