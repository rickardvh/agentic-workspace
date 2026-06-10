# Modules

`agentic-workspace` is the package. It composes first-party modules behind one root lifecycle and context CLI. Modules own domain behavior; the package root owns orchestration, shared config, compact routing, and lifecycle coordination.

## Open Participation Model

Agentic Workspace is an operating substrate, not a fixed bundle of slots. It
ships a recommended skill-guided loop for ordinary agents, but repos can add
workflow obligations and modules can contribute capabilities to that loop when
the contribution is explicit, queryable, safe, and cheap to route.

The recommended loop is:

| Step | Default owner | What modules may add |
| --- | --- | --- |
| startup | Workspace | startup routing hints, prompts, reports, or gates surfaced through compact routing |
| active work | Workspace and Planning | state owners, lifecycle hooks, workflow phases, owned roots, and stop conditions |
| durable knowledge | Memory | routeable durable context resources and prompts without owning active sequencing |
| proof | Workspace proof and Verification | proof routes, protocols, evidence bundles, result schemas, and safety metadata |
| closeout | Planning closeout | closeout obligations, residue routes, and claim gates without over-closing parent intent |

Modules may contribute resources, tools, prompts or skills, schemas, roots,
reports, gates, proof routes, lifecycle hooks, workflow phases, startup routing
hints, state owners, and safety metadata. Those declarations live in the module
registry or module-owned manifests and can be projected into generated docs,
plugin/catalogue entries, or MCP-style adapters. Generated projections are not
the source of truth.

Repo-configured `workflow_obligations` compose with the same loop by stage and
scope tag. A matched obligation raises the force of an existing step or closeout
gate; an unmatched obligation stays quiet. Obligations do not replace module
ownership and do not make every repo rule a new module.

Conflicts should be surfaced, not resolved silently. Examples include
overlapping owned roots, incompatible module selections, contradictory workflow
obligations, proof-route collisions, lifecycle-hook collisions, and startup
burden growth. The agent chooses a safe route from compact evidence; policy
conflicts that change accepted workflow remain repo-owner or human decisions.

Planning, Memory, and Verification are first-party examples of this model:

| Module | Example role |
| --- | --- |
| Planning | active execution state, lane/slice decomposition, continuation ownership, and honest closeout |
| Memory | durable anti-rediscovery knowledge and residue routing that reduces repeated context work |
| Verification | soft verification protocols, bounded evidence, proof route hints, and known gaps |

This model is deliberately open-ended. It should keep ordinary startup small
while allowing any number of modules to participate through declared roots,
tools, state, reports, gates, proof routes, and lifecycle behavior.

## Task Posture And Dynamic Instructions

The same participation model covers task posture. Agentic Workspace acts like a
richer configurable `AGENTS.md`: the static adapter points to the workspace
entrypoint, while startup and changed-path commands emit the task-specific
posture that is relevant now.

A task posture packet can include task intent, operating posture, workflow
obligations, skill routes, allowed and forbidden actions, proof and closeout
boundaries, read budget, authority boundaries, output-shape requirements,
review rubrics, and matched module contributions. It is composed from repo
config, task facts, changed paths, active planning state, and module
participation declarations.

Config posture participates in that composition:

| Input | Effect |
| --- | --- |
| `optimization_bias` | changes density, routing emphasis, and residue style without overriding hard obligations |
| artifact posture | constrains generated, persisted, or user-facing outputs |
| initiative posture | limits unsolicited cleanup and broader action |
| assurance posture | raises proof, review, and delegation requirements |
| read budget | controls whether startup emits compact selectors or deeper raw context |
| `workflow_obligations` | adds stage- and scope-specific requirements to the current loop step |

Modules declare their posture contributions instead of relying on bespoke core
logic. A declaration names the loop steps it can affect, contribution classes,
posture triggers, startup/report/closeout projections, authority boundaries, and
conflict provenance. Startup includes only matching fragments so ordinary first
contact does not grow into a full module manual.

Reports and closeout keep the model auditable. They expose applied workflow
obligations, selected module contributions, posture conflicts, and provenance
when posture changed the allowed next action, proof burden, output shape, review
rubric, authority boundary, or closeout permission.

## Module Profiles

| Profile | Modules | Checked-in footprint |
| --- | --- | --- |
| routing-only | none | root config, startup, ownership, workspace skills, module map, and report routing surfaces |
| memory | Memory | durable repo knowledge surfaces |
| planning | Planning | active execution state and execplan surfaces |
| verification | Verification | soft verification protocols and bounded evidence projections |
| full | Planning and Memory | both active work state and durable repo knowledge |

The AW package currently bundles first-party modules for simple `uvx` and `pipx` lifecycle use. That may change later, but the installed repository footprint is already selected by profile. The exact profile and component metadata is defined by the generated [Module registry](../reference/module-registry.md) and [Module capability](../reference/module-capability.md) references.

## Planning

Planning owns active execution state. Use it when work needs to stay bounded, resumable, and finishable across sessions.

Planning is good for:

- active queue state;
- bounded execution plans;
- handoff and restart contracts;
- proof expectations for active work;
- honest closeout and required continuation routing.

Planning is not a ticketing system, backlog manager, durable knowledge base, or broad documentation system.

Module implementation: [Planning README](../../packages/planning/README.md).

Command: `agentic-planning`.

## Memory

Memory owns durable repo knowledge that is expensive to rediscover. Use it when agents repeatedly relearn the same boundaries, runbooks, invariants, or subsystem orientation.

Memory is good for:

- durable technical facts;
- subsystem orientation;
- recurring failure lessons;
- authority boundaries;
- operator runbooks;
- routing hints that help agents read less.

Memory is not active task state, execution history, issue triage, or a replacement for canonical docs.

Module implementation: [Memory README](../../packages/memory/README.md).

Command: `agentic-memory`.

## Verification

Verification owns repo-native soft verification protocols, bounded evidence
records, known gaps, and proof route hints. Use it when executable tests are not
enough and the repo needs shared, reviewable verification expectations.

Verification is good for:

- declaring protocol activation by changed path, task marker, assurance
  requirement, proof profile, or planning ref;
- routing proof selection toward manual or semi-automated verification;
- recording bounded evidence summaries, transcript refs, residual risk, and
  stale conditions;
- keeping verification context repo-visible without turning AW into a browser
  automation platform.

Verification is not a generic test runner, compliance engine, UI automation
host, or global evidence store.

Module implementation: [Verification README](../../packages/verification/README.md).

Command: `agentic-verification`.

## Command Generation

`packages/command-generation/` is an internal implementation workspace for generic command package generation. It is not a host-repo module and is not part of the ordinary installed runtime.

Implementation reference: [Command generation README](../../packages/command-generation/README.md).

## Module Contracts

The module registry declares available modules, profiles, component metadata, and repository footprint policy. See [Module registry](../reference/module-registry.md) for the generated field reference. The lower-level command and component generation path is documented by [Command package IR](../reference/command-package-ir.md), [Command adapter generation](../reference/command-adapter-generation.md), and [Lifecycle generation readiness](../reference/lifecycle-generation-readiness.md).
