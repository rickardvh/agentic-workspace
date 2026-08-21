# Agentic Planning

Agentic Planning is the Agentic Workspace module for active execution ownership, bounded intent continuity, decomposition, and continuation. It is one peer capability in the generic `resolve -> act -> reconcile` loop, not the workflow engine or conceptual center of AW.

Use the root `agentic-workspace` CLI for ordinary host-repo work. The `agentic-planning` CLI is the explicit module maintenance/debugging surface.

Support-bearing installs use the exact root-wheel command projected from a versioned release's `distribution-install-readiness.json`; mutable branches and source-checkout commands are not supported install identities. See the root [installation guide](../../docs/agentic-workspace-install.md).

## Domain boundary

Planning owns checked-in active-work custody: selected execution owners, bounded plans, lanes/decompositions, issue relations, continuation, and lifecycle transitions. It can contribute current ownership, a routed operation, or reconciliation facts when relevant.

Planning does not own canonical product knowledge, proof sufficiency, semantic issue completion, general task tracking, or mutation authority outside the selected owner. Direct work should remain direct when no durable execution custody is needed.

## Ordinary participation

- **Resolve:** contribute active owner/intent/continuation facts only when current work needs them.
- **Act:** expose schema-backed Planning operations through the root Workspace front door.
- **Reconcile:** record bounded result, continuation, parent intent, and archive/integration transitions without inferring semantic completion.

Start with `agentic-workspace start`, `implement`, or `summary`; follow the exact Planning operation named by the current decision. Use generated [current CLI catalogue](../../docs/reference/cli-catalogue.md) for exact flags rather than copying a command inventory here.

## Continuation contract

If the completed slice came from the active queue or roadmap state, clear the matched queue residue in the same pass instead of leaving stale completed entries behind.

Execplans now treat four fields as first-class:

- `Intent Continuity`: whether the larger intended outcome is actually complete and what checked-in surface owns it if not
- `Required Continuation`: whether follow-on is mandatory for that larger outcome, plus its owner and activation trigger
- `Iterative Follow-Through`: what the slice enabled, deferred, discovered, and still needs to prove
- `Execution Summary`: what was delivered, validated, routed, retained, and how later work resumes

Required continuation for an unfinished larger intended outcome must be routed into a checked-in owner before the current slice closes. Keep `Iterative Follow-Through` current when a slice stops intentionally. Planning progress alone does not authorize a parent or issue completion claim.

## Installed contract

The package ships these payload files:

- `AGENTS.template.md`
- `.agentic-workspace/docs/execution-flow-contract.md`
- `.agentic-workspace/docs/lifecycle-and-config-contract.md`
- `.agentic-workspace/docs/minimum-operating-model.md`
- `.agentic-workspace/docs/routing-contract.md`
- `.agentic-workspace/docs/system-intent-contract.md`
- `.agentic-workspace/docs/workspace-config-contract.md`
- `.agentic-workspace/planning/UPGRADE-SOURCE.toml`
- `.agentic-workspace/planning/agent-manifest.json`
- `.agentic-workspace/planning/decompositions/README.md`
- `.agentic-workspace/planning/decompositions/TEMPLATE.decomposition.json`
- `.agentic-workspace/planning/execplans/README.md`
- `.agentic-workspace/planning/execplans/TEMPLATE.plan.json`
- `.agentic-workspace/planning/execplans/archive/README.md`
- `.agentic-workspace/planning/lanes/README.md`
- `.agentic-workspace/planning/lanes/TEMPLATE.lane.json`
- `.agentic-workspace/planning/schemas/planning-decomposition.schema.json`
- `.agentic-workspace/planning/schemas/planning-execplan.schema.json`
- `.agentic-workspace/planning/schemas/planning-external-intent-evidence.schema.json`
- `.agentic-workspace/planning/schemas/planning-finished-work-evidence.schema.json`
- `.agentic-workspace/planning/schemas/planning-closeout-evidence.schema.json`
- `.agentic-workspace/planning/schemas/planning-integration-proposal.schema.json`
- `.agentic-workspace/planning/schemas/planning-integration-receipt.schema.json`
- `.agentic-workspace/planning/schemas/planning-issue-relation.schema.json`
- `.agentic-workspace/planning/schemas/planning-lane.schema.json`
- `.agentic-workspace/planning/schemas/planning-owner-selection-receipt.schema.json`
- `.agentic-workspace/planning/schemas/planning-review.schema.json`
- `.agentic-workspace/planning/reviews/TEMPLATE.review.json`

The list above is mechanically checked against the package installer. Host repositories normally discover installed ownership through Workspace reports and generated footprint references rather than this package-maintainer list.

## Deeper maintenance

- `AGENTS.md` in this package owns contributor routing.
- `bootstrap/.agentic-workspace/planning/execplans/README.md` owns execplan field semantics.
- `skills/README.md` owns package skill discovery.
- Source-checkout tests and checks live under `packages/planning/tests` and `packages/planning/scripts`.

Public maturity: **alpha**, matching coordinated package metadata. Strong capability evidence does not independently promote the distribution support contract.
