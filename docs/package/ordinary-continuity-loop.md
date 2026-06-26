# Ordinary Continuity Loop And Surface Classification

This page is the reviewed target model for ordinary Agentic Workspace operation.
It is the decision basis for simplifying agent-facing surfaces under #1389 and
#1390.

The guiding rule is phase questions first, CLI as aid. Skills and protocols
shape the agent's reasoning when judgment is required. Compact CLI commands
provide facts, checks, routing, proof selection, state writes, and safe
drill-down. The command list is not the workflow.

Each ordinary surface exists to answer one phase question cheaply enough that
the next safe action is obvious. If a surface does not change the answer to a
phase question, it should stay behind routing, become diagnostic, or be removed
by a later simplification slice.

## Phase Questions

These questions are the primary product design unit for ordinary operation.
Commands, skills, state files, docs, and diagnostics are affordances attached to
the current question, not peers in a command-selection menu.

| Phase | Question | Primary ordinary affordance | Boundary |
| --- | --- | --- | --- |
| startup | What is the smallest safe context before acting? | `AGENTS.md` to `start --task "<task>"` plus `next_safe_action` | Should not require browsing command inventories or raw workspace files. |
| work shaping | Is this direct, bounded, lane, epic, takeover, or continuation work? | `start`, `summary`, or routed Planning mutation | Should decide work shape before implementation, not after checks pass. |
| governing knowledge | Which source can change interpretation, edits, proof, or closeout? | knowledge gates in `start`, `implement`, `summary`, `config`, or `report` | Should surface only action-changing authority and freshness. |
| implementation context | What narrow working set is safe to touch now? | `implement --changed <paths>` when paths are known; Planning execplan when active work owns scope | Should not expand into roadmap selection or parent-intent closure. |
| proof | What evidence is required for the claim I want to make? | `proof --changed <paths>` and proof hints from `implement` | Should keep proof execution separate from intent-satisfaction judgment. |
| closeout | What must survive after this agent stops? | Planning closeout/archive, proof report fields, Memory capture, or follow-up issue | Should route residue to one owner instead of leaving it in chat. |
| continuation | How can a future agent resume without replaying chat? | `summary` continuation view and active Planning owner | Should expose freshness, claim boundary, and next action before raw rereads. |

## Lane Completion Model

The ordinary path is not complete merely because the first phase-question slice
landed. A lane that aims to make AW cheaper in ordinary use must also resolve
or explicitly own four product-cost questions:

| Concern | Completion question | Ordinary owner |
| --- | --- | --- |
| surface visibility | Does this surface change the next safe action, working set, proof, owner, or continuation? | `report_profile.ordinary_agent_path.lane_completion_model.visibility_disposition` |
| artifact lifecycle | What survives after active work, and why is that survivor cheaper than raw narrative? | `lane_completion_model.artifact_lifecycle` plus Planning closeout |
| restart economics | Can a future agent recover intent, owner, next action, proof, claim boundary, and gaps from compact state? | `lane_completion_model.restart_scenarios` plus `summary` continuation view |
| affordance-first output | Is prose guidance doing work that should be a typed action, selector, route, proof command, or claim boundary? | `lane_completion_model.affordance_first_rules` |

This model is surfaced as one compact report packet instead of a new manual.
It deliberately keeps generated references, diagnostics, lifecycle commands,
module commands, and package docs behind routing unless they answer the current
phase question.

### Visibility Disposition

Retained first-contact surfaces are `AGENTS.md`, `start`, `summary`,
`implement --changed`, and `proof --changed`, because each can change the next
safe action, working set, proof, or claim boundary. `planning`, `memory`,
`report --section <section>`, `config`, `defaults`, `ownership`, and `modules`
are routed detail. `preflight`, `doctor`, `status`, and `setup` are diagnostic
or recovery. `init`, `install`, `upgrade`, `uninstall`, and `prompt` are
lifecycle. `docs/reference/` and generated command metadata are derived
reference surfaces.

The concrete demotion in this lane is that ordinary report guidance now starts
from `ordinary_agent_path` phase/lane packets while detailed report material
stays behind selectors. That replaces a command-inventory mental model with a
single next-action packet and keeps maintainer/generated/reference material out
of first-contact flow.

### Artifact Lifecycle

AW artifacts use these lifecycle classes:

| Class | Survivor rule |
| --- | --- |
| active | Own current execution only while work is live; do not preserve raw execution narrative after closeout. |
| durable | Promote only reusable intent, invariants, proof boundaries, or anti-rediscovery facts to docs, Memory, or issues. |
| local-only | Keep transient checkpoints and tool-local state outside canonical proof and package-owned residue. |
| generated | Treat generated/reference artifacts as derived detail, routed through selectors or maintainer checks. |
| promoted | Once product output lands, it becomes normal repo output rather than AW residue. |
| archived/removable | Archive, demote, or remove residue that no longer changes continuation, proof, owner, or review. |

The minimal survivor shape for completed work is claim boundary, proof summary,
residue owner, remaining gap, and reopen trigger.

### Restart Scenarios

Restart and continuation are design tests, not only performance metrics. The
representative scenarios are direct work, known changed-path work, active lane
continuation, takeover/recovery, and parent-lane closeout. Each scenario must
recover the governing intent, active owner or absence of one, next safe action,
required sources/selectors, proof expectation, proof state, claim boundary,
residue owner, and unresolved gaps from compact surfaces before broad raw
rereads.

### Affordance-First Rules

Prefer compact packet before explanation, selector before copied source text,
next-safe action before general guidance, owner surface before broad reading,
proof route before proof advice, claim boundary before closeout prose, and
warning force before caution narrative. Reasoning skills remain appropriate
where semantic judgment is required; CLI packets own facts, routes, selectors,
proof commands, and claim boundaries.

## Target Loop

Ordinary installed-repo work should feel like one compact loop:

| Step | Ordinary question | Primary surface | Routed detail |
| --- | --- | --- | --- |
| startup | What is the smallest safe context before acting? | `AGENTS.md` to `agentic-workspace start --task "<task>" --format json` | `skills`, `defaults`, `config`, `WORKFLOW.md`, or repo docs only when routed |
| work shaping | Is this direct, bounded, lane, epic, takeover, or continuation work? | `start`, `summary`, and routed Planning mutation | Planning execplans, decompositions, state, or issue evidence when ownership is required |
| governing knowledge | Which source can change interpretation, work shape, proof, or closeout? | knowledge routes and gates in `start`, `implement`, `summary`, or `report` | Memory notes, docs, issue/PR evidence, external freshness checks, or module-owned sources |
| implementation context | What narrow working set is safe to touch now? | `implement --changed <paths>` | changed-path gates, subsystem profiles, ownership hints, proof hints, or active-plan scope |
| proof | What evidence is required before a claim? | `proof --changed <paths>` and proof commands emitted by `implement` | Verification protocols, proof receipts, test commands, or manual review aids |
| closeout | What must survive after this agent stops? | Planning closeout/archive plus `summary` claim boundaries | Memory capture, follow-up issues, docs/config promotion, proof receipts, or parent-lane residue |
| continuation | How can the next agent resume without chat replay? | `summary` continuation view | source freshness, claim boundary, proof state, active owner, and stale projections |

The intended ordinary path is:

```text
AGENTS.md
  -> agentic-workspace start --task "<task>" --format json
       -> direct action, or exactly one routed next phase:
          work shaping: summary / Planning mutation / implement-context
          governing knowledge: compact route or gate
          implementation context: implement --changed
          proof: proof --changed
          closeout: Planning closeout / residue decision
          continuation: summary continuation_view
          recovery: preflight / doctor / config / ownership / defaults
```

## Surface Classes

Use these classes when deciding whether a surface should stay visible, move
behind routing, become generated/catalogued, merge with another surface, or be
removed.

| Class | Definition | Ordinary posture |
| --- | --- | --- |
| operating protocol | Shapes how the agent reasons or acts in a loop step | visible only when it is the current reasoning aid |
| reasoning skill | Guides judgment the CLI cannot safely automate | standard only if correctness suffers without it |
| CLI aid | Compact command output, check, router, proof selector, or safe writer | invoked by the loop, not memorized as workflow |
| routed state owner | Canonical checked-in state or source owner | opened only when compact routing points there |
| diagnostic | Repair, drift, install health, source freshness, or human inspection | drill-down, takeover, or warning response |
| lifecycle | Mutates installed or managed surfaces | explicit setup/upgrade/remove path, not ordinary work |
| maintainer-only | Source-checkout or package-maintenance workflow | excluded from installed host-repo operation |
| generated/catalogue | Derived reference, adapter, plugin, or CLI-mirroring projection | regenerate from source; do not hand-edit as authority |
| merger/removal candidate | Overlapping, obsolete, or too visible for value | candidate for a later simplification slice |

## Current Surface Classification

### Startup

| Surface | Classification | Decision |
| --- | --- | --- |
| `AGENTS.md` | operating adapter | Keep thin. It should point to the configured CLI invocation and avoid becoming a manual. |
| `start` | CLI aid, primary startup card | Keep as the ordinary front door. It should absorb first-contact routing pressure. |
| `.agentic-workspace/WORKFLOW.md` | routed fallback/projection | Keep subordinate, concise, and replaceable for no-CLI fallback. |
| `.agentic-workspace/docs/module-map.md` | routed fallback/reference | Open only when ownership or module abstraction is unclear. |
| `preflight` | diagnostic/recovery aid | Reserve for takeover, recovery, or unclear active state that `start` did not answer. |
| `defaults`, `config` | diagnostic/reference aids | Route through compact output when exact policy or posture matters. |
| `skills` | routed catalogue aid | Use when compact routing names or recommends a skill; not ordinary browsing. |
| `workspace-startup` | CLI-mirroring projection/fallback skill | Candidate for optional/generated fallback rather than broad default payload. |

### Active Work

| Surface | Classification | Decision |
| --- | --- | --- |
| `summary` | CLI aid, primary active-state card | Keep as the active Planning, handoff, continuation, and claim-boundary answer. |
| `implement --changed` | CLI aid, bounded work-context card | Keep for known changed paths; frame as work/proof context, not another first-contact model. |
| `planning` root group | routed lifecycle/state aid | Use when compact routing requires a Planning mutation or exact active-state operation. |
| Planning files under `.agentic-workspace/planning/` | routed state owner | Open after `summary`, `start`, `preflight`, or Planning commands point there. |
| `agentic-planning` module CLI | advanced module surface | Prefer root `agentic-workspace` for host repos; use module CLI for maintenance/debugging or explicit module control. |
| `system-intent` | routed active-intent/reference aid | Keep behind routing; do not make it a first-contact concept. |
| `workspace-work-shape` | reasoning skill | Keep as a decision protocol for direct/bounded/lane/epic judgment when compact output cannot decide alone. |
| `workspace-intent-discovery` | reasoning skill | Keep for ambiguous, high-stakes, or intent-sensitive tasks; activate by task shape or routing. |

### Governing Knowledge

| Surface | Classification | Decision |
| --- | --- | --- |
| `docs/package/knowledge-routing.md` | operating model reference | Canonical product doc for source authority, route force, freshness, and capture. |
| `docs/package/knowledge-gates.md` | operating model reference | Canonical product doc for blocking or claim-limiting knowledge gates. |
| Memory files under `.agentic-workspace/memory/` | routed state owner | Use as durable anti-rediscovery knowledge, not active task state or broad docs. |
| `memory route`, `memory capture-note`, `memory sync-memory` | routed CLI aids/mutations | Route from startup, work shaping, or closeout when reusable knowledge matters. |
| issue and PR evidence | tracker-intent source | Refresh when comments, state, or review may change requested outcome or merge safety. |
| external docs | external authoritative source | Verify freshness before design or claim when facts may have changed. |
| Planning state | active-intent source | Owns current execution, continuation, lane ordering, and closeout state. |

Knowledge routing is part of the ordinary loop, not another first-contact
surface. It should appear as compact task posture: source kind, authority,
owner, freshness, route force, blocked actions, and closeout capture only when
that knowledge can change the next safe action or completion claim.

### Proof And Verification

| Surface | Classification | Decision |
| --- | --- | --- |
| `proof --changed` | CLI aid, primary proof selector | Keep as the ordinary proof decision surface. |
| proof commands emitted by `implement` | CLI aid | Keep as local work-context convenience; do not create a second proof model. |
| proof receipts | routed proof evidence | Record when needed for closeout or review; proof selection remains separate from claim judgment. |
| Verification files under `.agentic-workspace/verification/` | routed state owner | Use when protocols, evidence bundles, proof routes, or known gaps are configured. |
| `report --section verification` | routed proof detail | Drill down when proof output or active state asks for verification detail. |
| `agentic-verification` module CLI | advanced module surface | Host-repo ordinary flow should prefer root routing. |
| `workspace-proof-selection` | reasoning skill | Keep for proof adequacy and claim-boundary judgment, especially with skipped, stale, negative, or partial evidence. |

### Closeout

| Surface | Classification | Decision |
| --- | --- | --- |
| Planning closeout/archive commands | routed closeout mutation | Keep as the checked-in writer for completed execplans and lane residue. |
| `summary` claim boundary | CLI aid | Use to expose whether full completion, partial progress, or issue closure is allowed. |
| `proof` receipts and proof report fields | routed evidence | Closeout consumes proof; it does not replace proof selection. |
| Memory capture/sync | routed residue owner | Use only for durable anti-rediscovery lessons or owner-routing facts. |
| follow-up issues | external tracker residue | Use for concrete work that should be routable outside current checked-in Planning. |
| `workspace-transition-gates` | transition guard skill | Keep as the reasoning aid for allowed/forbidden transitions when CLI output still requires agent judgment. |
| `workspace-operating-loop` | reasoning/frame skill | Keep as the compact frame for preserving the loop across Workspace, Planning, Memory, Verification, and configured modules. |

Closeout is the weakest ordinary mental-model phase today. The capability
exists, but it is diffused across Planning closeout writers, proof receipts,
Memory capture, skills, and fallback text. The next simplification should
surface closeout readiness and residue ownership through existing compact
outputs before adding another root command.

### Cross-Cutting And Lifecycle Surfaces

| Surface | Classification | Decision |
| --- | --- | --- |
| `init`, `install`, `upgrade`, `uninstall`, `prompt` | lifecycle | Keep outside ordinary work; these mutate managed surfaces or adapters. |
| `status`, `doctor`, `setup`, `report`, `ownership`, `modules` | diagnostic/reference aids | Use when routed by warnings, adoption, drift, ambiguous ownership, or human inspection. |
| `reconcile`, `external-intent refresh-github` | advanced diagnostic/adapters | Keep as optional external-evidence and state-repair aids. |
| `note-delegation-outcome` | local-only diagnostic | Keep local-only and out of shared ordinary workflow. |
| generated references under `docs/reference/` | generated/catalogue | Treat as derived from contracts; edit source contracts or generators. |
| package docs under `docs/package/` | product reference | Human/reference documentation, not first-contact agent payload. |
| source-checkout maintainer docs, scripts, checks, reviews | maintainer-only | Keep out of ordinary host-repo operation except as routed maintainer workflow. |

### Root Command Visibility

The root command contract is the source of exact command metadata. This table is
the #1390 visibility posture for the current top-level command groups.

| Command group | Visibility posture |
| --- | --- |
| `start` | primary startup CLI aid |
| `summary` | primary active-work and continuation CLI aid |
| `implement` | bounded changed-path work-context CLI aid |
| `proof` | primary proof-selection CLI aid |
| `planning` | routed active-state and closeout mutation aid |
| `memory` | routed governing-knowledge and residue aid |
| `report` | routed diagnostic/report aid, not ordinary startup |
| `preflight` | takeover/recovery diagnostic aid |
| `skills` | routed catalogue aid for selected reasoning or fallback skills |
| `defaults`, `config`, `ownership`, `modules`, `status`, `doctor`, `setup` | diagnostic/reference aids |
| `system-intent` | routed active-intent/reference aid |
| `reconcile`, `external-intent` | advanced external-evidence and repair aids |
| `note-delegation-outcome` | local-only diagnostic/calibration aid |
| `init`, `install`, `upgrade`, `uninstall`, `prompt` | lifecycle and adapter mutation commands |

Later lanes may move command docs, generated references, or adapter projections,
but they should preserve this posture unless the follow-on explicitly changes
the operating model.

## Skill Payload Decisions

Skills need two independent classifications: their reasoning role and their
payload eligibility.

| Skill class | Definition | Payload decision |
| --- | --- | --- |
| CLI-mirroring projection | Restates command behavior, output interpretation, or no-CLI fallback | candidate for generated/catalogued optional fallback, not default payload |
| reasoning complement | Guides judgment the CLI cannot make safely | may justify standard availability if compact and decision-shaped |
| transition guard | Preserves allowed/forbidden transition judgment | keep close to the contract and activate through routing |
| module-boundary aid | Helps place action or residue in the right owner surface | keep focused and route by owner ambiguity |
| hybrid | Mixes command facts with judgment protocol | split generated command facts from hand-authored reasoning where possible |

Default inclusion should require a stronger bar than usefulness. A default skill
should materially improve ordinary correctness even when compact CLI output is
available. If it mainly helps when the CLI is absent, it belongs in optional
fallback or generated adapter payload.

## Overlap Findings

1. `start`, `summary`, `implement`, and `preflight` answer neighboring "what
   now?" questions. Keep all four for now, but sharpen phase ownership:
   startup, active continuation, known-path work context, and takeover/recovery.
2. `proof` and `implement` both surface proof. Keep `proof` as the proof
   selector and `implement` as a changed-path work card that includes proof
   hints.
3. Closeout exists but is not visible enough as a loop phase. Improve routed
   closeout readiness before adding a new command.
4. Skills should not become parallel manuals. Keep reasoning skills compact and
   route them from CLI output or task shape; move CLI mirrors toward generated
   or optional fallback payload.
5. Module CLIs should stay behind root routing for ordinary host repos. Planning,
   Memory, and Verification are first-party participants in an open model, not
   the fixed outer boundary.
6. Diagnostics and generated references are valuable only after routing. They
   should not appear as ordinary startup concepts.
7. Knowledge routing must be cheap enough to prevent blind starts without
   becoming a reading list. Gates should block only when source authority can
   change interpretation, edits, proof, or closeout.

## Recommended Follow-On Sequence

1. Compress first-contact routing around `AGENTS.md` and `start`.
   Define when `implement --changed` can be used directly and when `preflight`
   is strictly recovery/takeover.
2. Clarify the `start` / `summary` / `implement` / `preflight` boundary in
   command outputs and docs so each owns one phase.
3. Promote closeout to a routed loop phase through existing compact outputs:
   readiness, proof dependency, intent satisfaction, residue owner, and parent
   closure boundary.
4. Split workspace skills by role and payload eligibility. Keep reasoning
   complements; move CLI-mirroring projection/fallback skills toward generated,
   optional, plugin, or catalogue payload.
5. Move diagnostics and references out of ordinary guidance. Keep `report`,
   `status`, `doctor`, `config`, `defaults`, `modules`, `ownership`, generated
   references, and package docs as drill-down surfaces.
6. Root-route module CLI exposure consistently. Host-repo ordinary docs should
   prefer `agentic-workspace`; module CLIs remain for maintenance, debugging,
   or explicit routed control.
7. Integrate governing knowledge routes into task posture packets: route force,
   source authority, freshness, skipped/stale states, proof impact, and closeout
   capture.

This sequence intentionally leaves #1389 open. #1390 supplies the target model
and classification. #1391 supplies the reviewed per-step inventory in
[Operating loop substep inventory](operating-loop-substeps.md). Later lanes must
reduce actual visible surface area, duplication, or startup burden against
these models.
