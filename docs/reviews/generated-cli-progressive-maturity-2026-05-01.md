# Generated CLI Progressive Maturity Review

Issue: #641
Child issues: #642, #643, #644
Date: 2026-05-01

## Maturity Model

Generated command surfaces move through these levels:

| Level | Meaning | Current use |
| --- | --- | --- |
| `metadata-proof-fixture` | Generated metadata proves the package can project the command-package IR, but is not a runnable interface. | TypeScript Planning and Memory packages remain here. |
| `runnable-read-only-adapter` | Generated target can run a read-only command through a process handoff. | TypeScript root workspace `defaults`. |
| `runtime-backed-read-only-adapter` | Generated parser/dispatch is the interface authority and delegates to hand-owned runtime primitives. | Python root read-only/context/diagnostic commands, Planning `status`, and Memory `status`. |
| `weak-agent-safe-adapter` | Generated read-only target is safe for weak-agent routing after broader off-happy-path proof. | Not enabled yet. |
| `mutation-capable-adapter` | Generated target can invoke guarded mutation primitives. | Deferred until dry-run, preflight, and refusal conformance are explicit. |

## Implemented Promotions

| Surface | Command | Previous maturity | New maturity | Runtime owner | Proof |
| --- | --- | --- | --- | --- | --- |
| Root workspace Python CLI | `agentic-workspace defaults` | `metadata-proof-fixture` | `runtime-backed-read-only-adapter` | `workspace.defaults.load`, `workspace.defaults.select`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace config` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.root.resolve`, `workspace.config.load`, `workspace.config.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace modules` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.root.resolve`, `workspace.modules.inspect`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace start` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.root.resolve`, `preflight.context.assemble`, `startup.context.assemble`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace summary` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.root.resolve`, `planning.summary.load`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace implement` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.root.resolve`, `implementer.context.assemble`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace preflight` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.root.resolve`, `preflight.context.assemble`, `preflight.response.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace proof` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.root.resolve`, `proof.selection.load`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace ownership` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.root.resolve`, `ownership.review.load`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace skills` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.root.resolve`, `skills.recommend`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace report` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.root.resolve`, `workspace.config.load`, `workspace.selection.resolve`, `workspace.report.assemble`, `workspace.report.select`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace reconcile` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.root.resolve`, `planning.reconcile.load`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace setup` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.root.resolve`, `workspace.selection.resolve`, `workspace.report.assemble`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace status` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.root.resolve`, `workspace.selection.resolve`, `workspace.report.assemble`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace doctor` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.root.resolve`, `workspace.selection.resolve`, `workspace.report.assemble`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace TypeScript package | Root read-only/context/diagnostic generated commands | `runnable-read-only-adapter` | unchanged | canonical Python process handoff | Node-backed conformance |
| Planning Python CLI | `agentic-planning-bootstrap status` | `metadata-proof-fixture` | `runtime-backed-read-only-adapter` | `planning.bootstrap.status.load`, `output.emit` | generated parser/dispatch test and process smoke proof |
| Memory Python CLI | `agentic-memory-bootstrap status` | `metadata-proof-fixture` | `runtime-backed-read-only-adapter` | `memory.bootstrap.status.load`, `output.emit` | generated parser/dispatch test and process smoke proof |

## Remaining Root Read-Only Commands

Tracked by #643. These commands already have interface declarations in `cli_commands.json`, but they are not promoted to runtime-backed generated Python parser/dispatch in this PR.

| Command | Current authority | Next maturity step | Notes |
| --- | --- | --- | --- |
| `modules` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Promoted in the #643 continuation slice with minimal-repo black-box conformance. |
| `config` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Promoted in the #643 continuation slice with minimal-repo black-box conformance. |
| `start` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Promoted in the #643 continuation slice with changed-path black-box conformance. |
| `summary` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Promoted in the #643 continuation slice with no-active-execplan black-box conformance. |
| `implement` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Promoted in the #643 continuation slice with task text and changed-path conformance. |
| `preflight` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Promoted in the #643 continuation slice with active-only conformance. |
| `proof` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Promoted in the #643 continuation slice with changed-path conformance. |
| `ownership` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Promoted in the #643 continuation slice with concern selector conformance. |
| `skills` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Promoted in the #643 continuation slice with task recommendation conformance. |
| `reconcile` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Promoted in the #643 continuation slice with provider-agnostic reconciliation conformance. |
| `report` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Promoted in the #643 continuation slice with router-profile conformance. |
| `setup`, `status`, `doctor` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Promoted in the #643 continuation slice with explicit planning-module fixture conformance. |

## Package Read-Only Commands

Tracked by #644. This PR implements the first package-local promotion for both packages: `status` is now generated parser/dispatch with hand-owned runtime primitives. The next package candidates should follow after package-local conformance fixtures are added for `doctor`, `report`, `summary`, and routing/reporting commands.

## Lifecycle Dry-Run And Mutation Commands

Tracked by #642. Lifecycle commands stay below `mutation-capable-adapter` until generated adapters can prove:

- dry-run behavior separately from apply behavior;
- strict preflight gate handling before mutation;
- destructive-refusal behavior before runtime primitive invocation;
- human review requirements in generated help/error paths;
- black-box failure coverage for unsafe or incomplete invocations.

This PR deliberately does not promote `install`, `init`, `upgrade`, `uninstall`, `prompt`, or package mutation commands beyond deferred/readiness status.

## Reference Docs

The generated schema reference for the command-package IR is [docs/reference/command-package-ir.md](../reference/command-package-ir.md). It now documents the generated parser `interface` block and the `runtime-backed-read-only-adapter` Python target status used by this migration.
