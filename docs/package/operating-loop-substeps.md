# Operating Loop Substep Inventory

This page is the reviewed #1391 bridge between the ordinary continuity model in
[Ordinary continuity loop and surface classification](ordinary-continuity-loop.md)
and concrete simplification slices under #1389.

The five-step loop stays stable: startup, active work, durable knowledge, proof,
and closeout. This inventory simplifies inside those steps. It starts from the
skill-shaped workflow question, then decides which facts, checks, routes,
writers, and diagnostics belong in CLI aids.

It also applies the open participation model from [Modules](modules.md).
Planning, Memory, and Verification are first-party occupants of generic module
slots. Later work should not hard-code those module names into ordinary agent
workflow when a module declaration, workflow obligation, or task posture field
can supply the same responsibility through a contract.

## Inventory Fields

Each step uses the same questions.

| Field | Purpose |
| --- | --- |
| Operating skill/protocol | The skill-shaped workflow that tells the agent how to work in the step. |
| Required agent decision | The judgment the agent must make; the CLI can inform it but should not pretend to own it. |
| CLI aids | Compact facts, checks, routing, proof selection, diagnostics, or safe writers. |
| Reasoning guidance | Guidance needed because the CLI cannot safely replace semantic judgment. |
| CLI-mirroring artifacts | Command-order text, fallback snippets, docs, or projections that can move toward generated/catalogued/optional payload. |
| State owners | Checked-in or external owners of durable state for the step. |
| Fallback path | Conservative route when the CLI is unavailable. |
| Merge/remove candidates | Visible concepts, duplicated substeps, or command/docs exposure to simplify. |
| Module slot responsibility | Generic responsibility independent of current first-party modules. |
| First-party occupant | Current AW implementation that fills the slot. |
| Third-party integration seam | What another module must declare to participate safely. |
| Slot routing rule | How the operating protocol chooses the module contribution. |
| Generic fallback | What happens when no module occupies the slot. |
| Follow-on issue | Bounded implementation slice produced by this inventory. |

Knowledge routes and gates are posture inputs across all steps. They should
appear only when task text, changed paths, active state, Memory routes,
Verification protocols, workflow obligations, module declarations, source
authority, freshness, or closeout residue can change the next safe action,
proof burden, or completion claim.

When a knowledge gate applies, each step should carry the same compact gate
fields rather than inventing step-local wording.

| Knowledge gate field | Meaning |
| --- | --- |
| `force_level` | Required, recommended, advisory, or not applicable. |
| `gate_trigger` | The task text, changed path, active state, Memory route, Verification protocol, workflow obligation, module declaration, source authority, stale marker, review state, or closeout residue that selected the gate. |
| `required_next_action` | The smallest route, consult, freshness check, dismissal, escalation, or capture needed before the agent can safely continue. |
| `forbidden_action` | Design, edit, proof, claim, closeout, or parent closure action blocked while the gate is unresolved. |
| `route_freshness` | Current, stale, unavailable, unchecked, dismissed, or lower-authority. |
| `closure_boundary` | How the gate affects proof adequacy, claim permission, closeout trust, and residue ownership. |

## Startup

Startup should be owned by a Startup Router operating protocol. `AGENTS.md` is
the adapter into that protocol, and `start --task "<task>" --format json` is
the primary CLI aid. The ordinary startup experience should not feel like a
manual or root command list.

| Field | Inventory |
| --- | --- |
| Operating skill/protocol | Startup Router: decide the smallest safe context, allowed next action, skill route, module slot, and forbidden actions before work begins. |
| Required agent decision | Decide whether to proceed directly, load active Planning, use known changed paths, ask a clarification, enter takeover/recovery, trust the configured CLI invocation, or fall back without CLI. |
| CLI aids | `start`, `implement --changed` when paths are already known, `preflight` only for takeover/recovery, `config` for exact local posture, `skills` for routed skill lookup, and `defaults` for routed policy reference. |
| Reasoning guidance | Do not broadly read raw `.agentic-workspace/` files before compact routing; distinguish read permission from implementation permission; preserve forbidden actions until a newer packet supersedes them; keep no-CLI fallback conservative. |
| CLI-mirroring artifacts | Startup command-order text in `workspace-startup`, command tables in fallback docs, plugin projections, and broad first-contact docs that duplicate `start` output. |
| State owners | `AGENTS.md`, `.agentic-workspace/config.toml`, `.agentic-workspace/WORKFLOW.md`, `.agentic-workspace/docs/module-map.md`, `src/agentic_workspace/contracts/skill_specs.json`, and `src/agentic_workspace/contracts/schemas/startup_context.schema.json`. |
| Fallback path | Read `AGENTS.md`, then `.agentic-workspace/WORKFLOW.md` only far enough to recover the conservative no-CLI path; avoid broad Planning/Memory reads and durable artifact creation unless continuation ownership is required. |
| Merge/remove candidates | Reframe `AGENTS.md` as "use Startup Router"; demote `preflight`, `config`, `defaults`, `skills`, `modules`, `ownership`, and `report` to routed drill-down; compress `.agentic-workspace/WORKFLOW.md` once startup packets are authoritative enough. |
| Module slot responsibility | Startup/context router and module-slot resolver. |
| First-party occupant | Workspace root. |
| Third-party integration seam | Module registry or manifest declarations for startup routing hints, task posture fragments, skills/prompts, reports, gates, owned roots, safety boundaries, and fallback resources. |
| Slot routing rule | Route a module only when task text, changed paths, active state, workflow obligations, or module posture triggers match and the contribution changes allowed action, required reading, proof, or closeout. |
| Generic fallback | Use workspace-only startup posture and no-CLI fallback; unmatched module contributions stay quiet. |
| Follow-on issue | #1404 Make startup protocol-first and reduce ordinary first-contact command exposure. |

Knowledge gates matter most before the agent chooses architecture or starts
edits. Startup should emit compact source authority, freshness, route force,
blocked actions, and closeout capture only for selected governing sources.

## Active Work

Active work should be owned by a Work Shaping + Planning Autopilot protocol.
Work shaping decides direct, bounded, lane, epic, takeover, or continuation
posture. Planning Autopilot applies only when Planning owns active state or a
planning mutation.

| Field | Inventory |
| --- | --- |
| Operating skill/protocol | Work Shaping + Planning Autopilot: choose the smallest safe workflow shape, then use Planning only when active execution state or continuation ownership is required. |
| Required agent decision | Decide whether intent is clear enough, whether work is direct/bounded/lane/epic, whether Planning is optional or required, whether external issue evidence is authoritative or intake only, and whether a local slice can honestly leave parent intent open. |
| CLI aids | `start`, `summary`, `implement --changed`, `planning <mutation>`, `planning delegation-decision`, `ownership`, and `preflight` for recovery only. |
| Reasoning guidance | Resolve soft intent instead of keyword-matching; stop before coding when scope becomes lane/epic; avoid creating Planning artifacts to show work; preserve parent intent separately from slice closure. |
| CLI-mirroring artifacts | Planning command lists, skill text that restates `summary` or `planning` command order, generated Planning plugin prompts, and module-map snippets that duplicate root routing. |
| State owners | Planning state, execplans, decompositions, lane records, Planning schemas, and external trackers as evidence rather than universal authority. |
| Fallback path | Use startup fallback first; read Planning workflow guidance before raw state edits; open active execplans only when compact/fallback routing identifies them; avoid hand-editing `state.toml` when a command-owned mutation exists. |
| Merge/remove candidates | Clarify `start` as first contact, `summary` as active continuation, `implement` as changed-path work/proof context, and `planning` as routed state mutation; demote module CLIs from ordinary docs; split Work Shape reasoning from command mirroring. |
| Module slot responsibility | Active execution state and continuation owner. |
| First-party occupant | Planning, with Workspace work-shape routing. |
| Third-party integration seam | Active-state resource, mutation tools, readiness report, continuation/handoff protocol, owned roots, lifecycle hooks, closeout bridge, workflow phases, proof effects, and safety metadata. |
| Slot routing rule | Route to the module when a compact packet says active state exists, task shape requires continuity, changed paths touch owned roots, or a workflow obligation requires module-owned state. |
| Generic fallback | Treat work as direct or bounded with explicit assumptions; if continuity is required and no state owner exists, stop with a minimal handoff instead of inventing unmanaged state. |
| Follow-on issue | #1405 Clarify active-work protocol boundaries across `start`, `summary`, `implement`, and `planning`. |

Pre-work knowledge gates belong here when task text, changed paths, Planning
state, Memory routes, Verification protocols, workflow obligations, or module
participation can change the work shape or safe edit boundary.

## Durable Knowledge

Durable knowledge should be owned by a Memory Consultation / Anti-Rediscovery
protocol. This is not "read Memory." The protocol decides whether durable
knowledge is relevant, what the smallest route is, whether nothing was found or
not checked, and where residue belongs.

| Field | Inventory |
| --- | --- |
| Operating skill/protocol | Memory Consultation / Anti-Rediscovery: route only knowledge that prevents rediscovery, then route residue to the correct owner after the work. |
| Required agent decision | Decide whether Memory matters now, whether route results are enough, whether a lesson is durable or one-off, whether owner is Memory, Planning, docs, tests, contracts, config, review, issue, or dismissal, and whether friction is an improvement signal. |
| CLI aids | `start` memory posture, `memory route`, `memory capture-note`, `memory sync-memory`, `memory promotion-report`, `report --section module_reports`, and routed `doctor` checks. |
| Reasoning guidance | Memory helps agents read less; do not bulk-load it; do not store active sequencing, task logs, backlog, issue triage, or broad docs there; distinguish `checked_none` from `not_checked`; prefer tightening existing notes. |
| CLI-mirroring artifacts | Exact memory command snippets, route/report/capture command facts, MCP or plugin projections for memory index/manifest/freshness, and module registry component projections. |
| State owners | `.agentic-workspace/memory/repo/`, Memory index and manifest, note taxonomy, Planning for active execution state, docs for canonical product/system content, and `.agentic-workspace/local/` for local transient residue. |
| Fallback path | Read only `AGENTS.md`, Memory index/manifest when present, and already-routed notes; record consultation/residue status in final or Planning closeout; avoid mutating managed Memory state unless fallback rules permit it. |
| Merge/remove candidates | Make Memory Consultation the concept rather than memory commands; align residue vocabulary with closeout; move command-only snippets toward generated/catalogued artifacts; decide payload posture for Memory skills by reasoning versus mirror role. |
| Module slot responsibility | Durable anti-rediscovery knowledge and routeable context. |
| First-party occupant | Memory. |
| Third-party integration seam | Routeable knowledge index/resource, manifest/freshness contract, consultation status, capture/update tools, residue ownership vocabulary, source authority metadata, and route projections. |
| Slot routing rule | Route when selected knowledge can change interpretation, implementation, proof, closeout, or rediscovery cost; do not route merely because a source exists. |
| Generic fallback | Continue without durable knowledge only after recording `not_checked`, `checked_none`, `unavailable`, `stale`, `dismissed`, or `follow_up_required` as the honest posture. |
| Follow-on issue | #1408 Simplify durable-knowledge flow around Memory Consultation and residue ownership. |

This step also owns cross-source knowledge routing posture: source authority,
freshness/staleness, reference-versus-mirror policy, chat-derived knowledge
capture, and promotion/demotion rules. Memory is one durable owner, not the
container for every governing source.

## Proof And Verification

Proof should be owned by a Proof Adequacy protocol, with Verification as routed
enrichment when executable tests are insufficient or soft verification is
configured. The goal is meaningful evidence for the claim, not maximal command
execution.

| Field | Inventory |
| --- | --- |
| Operating skill/protocol | Proof Adequacy: decide what evidence is meaningful for the claim and whether Verification should enrich the route. |
| Required agent decision | Decide claim level, whether proof covers behavior and intent, how warnings/skips/crashes/environment failures lower the claim, whether Verification activates, whether proof permits completion or a narrower claim, and who owns gaps. |
| CLI aids | `proof --changed`, `implement --changed`, `summary`, `proof --record-receipt`, `report --section verification`, and module CLI only for maintenance/debugging. |
| Reasoning guidance | Proof success is not intent satisfaction; narrow tests do not prove parent claims; skipped or unavailable proof must be classified; manual inspection is valid only for suitable surfaces or configured protocols; environment absence is a proof gap. |
| CLI-mirroring artifacts | Proof command tables, exact invocation lists, skill sections that restate `proof`/`implement`, plugin-facing proof projections, and Verification report snippets. |
| State owners | Workspace proof routing, proof receipts, Verification protocols and bounded evidence, Planning claim expectations, and closeout for completion/intent satisfaction. |
| Fallback path | Choose the narrowest existing test, lint, contract, or inspection route; classify result explicitly; avoid claiming more than fallback proof supports; route soft verification or environment gaps to the correct owner. |
| Merge/remove candidates | Separate `implement` work context from `proof` selection; keep Verification behind routed proof/report outputs; deduplicate proof doctrine across fallback docs, skills, command docs, and Verification docs; generate route projections from contracts where possible. |
| Module slot responsibility | Proof enrichment and soft verification protocol provider. |
| First-party occupant | Workspace proof routing plus Verification. |
| Third-party integration seam | Proof-route hints, activation rules, evidence bundle schemas, result schemas, stale/gap semantics, safety metadata, proof/report projections, and claim-impact vocabulary. |
| Slot routing rule | Activate module proof contribution when changed paths, task markers, active plan proof profile, workflow obligations, source gates, or module manifests say the contribution can change evidence or claim permission. |
| Generic fallback | Use baseline proof route and downgrade the claim when no module proof provider is available or current. |
| Follow-on issue | #1406 Unify proof selection around a Proof Adequacy protocol with Verification as routed enrichment. |

Knowledge routes affect proof when required or stale sources change what must
be proven, when source consultation becomes evidence, or when skipped,
unavailable, stale, or dismissed knowledge limits the permitted claim.

## Closeout

Closeout should be owned by a Completion Honesty / Residue Routing protocol.
The capability exists today, but it is spread across Planning closeout writers,
proof receipts, Memory residue, reports, and transition skills. The
simplification target is a single protocol vocabulary before adding any new
root command.

| Field | Inventory |
| --- | --- |
| Operating skill/protocol | Completion Honesty / Residue Routing: reconcile proof, intent, claim level, residue, continuation owner, and closure permission. |
| Required agent decision | Decide what proof established, what claim is allowed, whether task/slice/lane/epic intent is satisfied, whether parent intent remains open, what durable residue exists, where it belongs, and whether dogfooding friction should become follow-up work. |
| CLI aids | `summary`, `proof`, `proof --record-receipt`, Planning archive/closeout writers, `memory route`, `memory capture-note`, `memory promotion-report`, and `report --section closeout_trust` when needed. |
| Reasoning guidance | Validation success is not issue completion; issue completion is not parent intent satisfaction; no Memory write is not no residue; completed execplans are not the knowledge base; do not hide deferred intent without an owner. |
| CLI-mirroring artifacts | Planning closeout command forms, closeout report field guides, proof-to-closeout command snippets, and fallback procedures that mostly restate contract fields. |
| State owners | Planning/`planning.closeout` for active work completion, proof receipts for evidence, selected residue owners, workspace report projections, and external trackers as source-owned evidence. |
| Fallback path | Do not mutate managed Planning closeout state by hand; state proof, intent satisfaction, claim boundary, gaps, residue decision, and next owner explicitly; leave minimal continuation guidance if Planning owns active work. |
| Merge/remove candidates | Consolidate closeout as a loop phase through existing outputs; expose readiness without forcing agents to discover multiple subcommands; align Memory residue with Planning closeout; compress fallback closeout text after protocol stability. |
| Module slot responsibility | Completion honesty, residue router, and continuation owner. |
| First-party occupant | Planning closeout, Memory residue, Workspace report projections, and external issue/PR evidence. |
| Third-party integration seam | Closeout-readiness report, claim-boundary semantics, residue route declarations, continuation-owner fields, safe mutation tools, proof-gap vocabulary, and issue/external closure effects. |
| Slot routing rule | Route closeout contribution when proof, active state, module obligations, residue, or tracker state can change closure permission or continuation ownership. |
| Generic fallback | State a narrower claim and explicit next owner; do not close managed state or parent intent without the owning module or tracker path. |
| Follow-on issue | #1407 Make closeout a protocol-first loop phase without adding premature command surface. |

Closeout must record knowledge posture when consultation affected the work.
Useful statuses include consulted, skipped, stale, unavailable, dismissed,
captured, promotion-required, and not-applicable. These statuses should change
closeout trust and claim permission when the source was governing.

## Follow-On Implementation Sequence

The recommended #1389 implementation order after #1391 is:

1. Make startup protocol-first and reduce ordinary first-contact command
   exposure (#1404).
2. Clarify active-work protocol boundaries across `start`, `summary`,
   `implement`, and `planning` (#1405).
3. Unify proof selection around a Proof Adequacy protocol with Verification as
   routed enrichment (#1406).
4. Make closeout a protocol-first loop phase without adding premature command
   surface (#1407).
5. Simplify durable-knowledge flow around Memory Consultation and residue
   ownership (#1408).
6. Split generated/catalogued CLI mirrors from reasoning skills across the
   loop, using module-slot declarations rather than first-party module names as
   the contract boundary.

The first five are concrete child issues. The sixth is cross-cutting and should
be promoted only after at least one earlier slice proves the
generated/catalogued boundary with real surfaces.

## Closure Boundary

This page satisfies #1391 when it is reviewed with the issue comments that
seeded it. It does not satisfy #1389. The parent epic remains open until later
implementation slices produce installed-product evidence that ordinary
agent-facing complexity, duplicated guidance, and startup burden have actually
been reduced.
