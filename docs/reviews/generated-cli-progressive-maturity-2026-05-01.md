# Generated CLI Progressive Maturity Review

Issue: #641
Child issues: #642, #643, #644
Date: 2026-05-01

## Maturity Model

Generated command surfaces move through these levels:

| Level | Meaning | Current use |
| --- | --- | --- |
| `metadata-proof-fixture` | Generated metadata proves the package can project the command-package IR, but is not a runnable interface. | Historical TypeScript fixture level. |
| `runnable-read-only-adapter` | Generated target can run a read-only command through generated runtime code and contract-backed output projection. | Historical root workspace TypeScript `defaults` slice. |
| `runtime-backed-read-only-adapter` | Generated parser/dispatch is the interface authority and delegates to hand-owned runtime primitives. | Python root read-only/context/diagnostic commands, Planning `status`, and Memory `status`. |
| `weak-agent-safe-adapter` | Generated read-only target is safe for weak-agent routing after broader off-happy-path proof. | Not enabled yet. |
| `mutation-capable-adapter` | Generated target can invoke guarded mutation primitives. | Deferred until dry-run, preflight, and refusal conformance are explicit. |

## Implemented Promotions

| Surface | Command | Previous maturity | New maturity | Runtime owner | Proof |
| --- | --- | --- | --- | --- | --- |
| Root workspace Python CLI | `agentic-workspace defaults` | `metadata-proof-fixture` | `runtime-backed-read-only-adapter` | `workspace.defaults.load`, `workspace.defaults.select`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace config` | generated parser/dispatch with contract-declared output views | `runtime-backed-read-only-adapter` | `workspace.target-root.resolve`, `workspace.config.load`, `payload.project`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace modules` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.target-root.resolve`, `workspace.modules.inspect`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace start` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.target-root.resolve`, `preflight.context.assemble`, `startup.context.assemble`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace summary` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.target-root.resolve`, `planning.summary.load`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace implement` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.target-root.resolve`, `implementer.context.assemble`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace preflight` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.target-root.resolve`, `preflight.context.assemble`, `preflight.response.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace proof` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.target-root.resolve`, `proof.selection.load`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace ownership` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.target-root.resolve`, `ownership.review.load`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace skills` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.target-root.resolve`, `skills.recommend`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace report` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.target-root.resolve`, `workspace.config.load`, `workspace.selection.resolve`, `workspace.report.assemble`, `workspace.report.select`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace reconcile` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.target-root.resolve`, `planning.reconcile.load`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace setup` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.target-root.resolve`, `workspace.selection.resolve`, `workspace.report.assemble`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace status` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.target-root.resolve`, `workspace.selection.resolve`, `workspace.report.assemble`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace doctor` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.target-root.resolve`, `workspace.selection.resolve`, `workspace.report.assemble`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace TypeScript package | all root generated commands | `runnable-read-only-adapter` | native TypeScript/Node | generated parser, validation, native operation dispatch, and contract-backed output projection without Python runtime handoff | Node-backed conformance |
| Planning Python CLI | `agentic-planning-bootstrap status` | `metadata-proof-fixture` | `runtime-backed-read-only-adapter` | `planning.bootstrap.status.load`, `output.emit` | generated parser/dispatch test and process smoke proof |
| Memory Python CLI | `agentic-memory-bootstrap status` | `metadata-proof-fixture` | `runtime-backed-read-only-adapter` | `memory.bootstrap.status.load`, `output.emit` | generated parser/dispatch test and process smoke proof |
| Planning Python CLI | `agentic-planning-bootstrap doctor`, `summary`, `report`, `reconcile` | handwritten package parser/dispatch | `runtime-backed-read-only-adapter` | package-local planning report primitives | generated parser/dispatch test and process conformance |
| Memory Python CLI | `agentic-memory-bootstrap doctor`, `report` | handwritten package parser/dispatch | `runtime-backed-read-only-adapter` | package-local memory report primitives | generated parser/dispatch test and process conformance |

## Root Read-Only Commands

Tracked by #643. These commands now have runtime-backed generated Python parser/dispatch and black-box conformance where promoted in this lane.

| Command | Current authority | Status | Notes |
| --- | --- | --- | --- |
| `modules` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Minimal-repo black-box conformance. |
| `config` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Minimal-repo black-box conformance. |
| `start` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Changed-path black-box conformance. |
| `summary` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | No-active-execplan black-box conformance. |
| `implement` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Task text and changed-path conformance. |
| `preflight` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Active-only conformance. |
| `proof` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Changed-path conformance. |
| `ownership` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Concern selector conformance. |
| `skills` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Task recommendation conformance. |
| `reconcile` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Provider-agnostic reconciliation conformance. |
| `report` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Router-profile conformance. |
| `setup`, `status`, `doctor` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Explicit planning-module fixture conformance. |

## Package Read-Only Commands

Tracked by #644. This PR promotes the stable package-local read-only commands that fit the current operation registry model: Planning `status`, `doctor`, `summary`, `report`, and `reconcile`; Memory `status`, `doctor`, and `report`. Memory-only unique commands such as `route-report`, `promotion-report`, `list-files`, and `list-skills` need a separate package-command namespace follow-up before promotion, because the operation registry currently validates command names against global/root command names.

## Lifecycle Dry-Run And Mutation Commands

Tracked by #642. This lane added black-box conformance for lifecycle dry-run/refusal behavior without enabling mutation-capable generated adapters:

- `install.lifecycle.dry-run.process` proves install dry-run plan shape and no writes.
- `init.lifecycle.dry-run.process` proves init dry-run plan shape and no writes.
- `upgrade.lifecycle.dry-run.process` proves upgrade dry-run planning, root-upgrade front-door routing, and review-before-apply flags.
- `upgrade.lifecycle.strict-preflight-refusal.process` proves strict preflight refuses before mutation.
- `uninstall.lifecycle.destructive-refusal.process` proves ambiguous destructive removal is review-required and write-free in dry-run.
- `uninstall.lifecycle.strict-preflight-refusal.process` proves strict preflight refuses destructive lifecycle mutation before apply.

Lifecycle commands stay below `mutation-capable-adapter` until generated adapters can prove:

- dry-run behavior separately from apply behavior;
- strict preflight gate handling before mutation;
- destructive-refusal behavior before runtime primitive invocation;
- human review requirements in generated help/error paths;
- black-box failure coverage for unsafe or incomplete invocations.

This PR deliberately does not promote `install`, `init`, `upgrade`, `uninstall`, `prompt`, or package mutation commands beyond deferred/readiness status. Follow-up #652 tracks the contract gap where dry-run/refusal maturity needs to be represented separately from apply/mutation maturity, and #653 tracks setup phases for stronger installed-state process conformance.

## Reference Docs

The generated schema reference for the command-package IR is [docs/reference/command-package-ir.md](../reference/command-package-ir.md). It now documents the generated parser `interface` block and the `runtime-backed-read-only-adapter` Python target status used by this migration.
