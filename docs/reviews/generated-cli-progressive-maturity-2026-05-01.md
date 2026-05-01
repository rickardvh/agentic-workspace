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
| `runtime-backed-read-only-adapter` | Generated parser/dispatch is the interface authority and delegates to hand-owned runtime primitives. | Python root `defaults`, `config`, `modules`, and `start`, Planning `status`, and Memory `status`. |
| `weak-agent-safe-adapter` | Generated read-only target is safe for weak-agent routing after broader off-happy-path proof. | Not enabled yet. |
| `mutation-capable-adapter` | Generated target can invoke guarded mutation primitives. | Deferred until dry-run, preflight, and refusal conformance are explicit. |

## Implemented Promotions

| Surface | Command | Previous maturity | New maturity | Runtime owner | Proof |
| --- | --- | --- | --- | --- | --- |
| Root workspace Python CLI | `agentic-workspace defaults` | `metadata-proof-fixture` | `runtime-backed-read-only-adapter` | `workspace.defaults.load`, `workspace.defaults.select`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace config` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.root.resolve`, `workspace.config.load`, `workspace.config.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace modules` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.root.resolve`, `workspace.modules.inspect`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace Python CLI | `agentic-workspace start` | handwritten root parser/dispatch | `runtime-backed-read-only-adapter` | `workspace.root.resolve`, `preflight.context.assemble`, `startup.context.assemble`, `output.emit` | generated freshness, Python parser/dispatch test, black-box process conformance |
| Root workspace TypeScript package | `agentic-workspace defaults`, `agentic-workspace config`, `agentic-workspace modules`, `agentic-workspace start` | `runnable-read-only-adapter` | unchanged | canonical Python process handoff | Node-backed conformance |
| Planning Python CLI | `agentic-planning-bootstrap status` | `metadata-proof-fixture` | `runtime-backed-read-only-adapter` | `planning.bootstrap.status.load`, `output.emit` | generated parser/dispatch test and process smoke proof |
| Memory Python CLI | `agentic-memory-bootstrap status` | `metadata-proof-fixture` | `runtime-backed-read-only-adapter` | `memory.bootstrap.status.load`, `output.emit` | generated parser/dispatch test and process smoke proof |

## Remaining Root Read-Only Commands

Tracked by #643. These commands already have interface declarations in `cli_commands.json`, but they are not promoted to runtime-backed generated Python parser/dispatch in this PR.

| Command | Current authority | Next maturity step | Notes |
| --- | --- | --- | --- |
| `modules` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Promoted in the #643 continuation slice with minimal-repo black-box conformance. |
| `config` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Promoted in the #643 continuation slice with minimal-repo black-box conformance. |
| `start` | generated parser/dispatch backed by command-package IR | `runtime-backed-read-only-adapter` | Promoted in the #643 continuation slice with changed-path black-box conformance. |
| `implement` | handwritten root parser/dispatch backed by CLI contract manifests | `runtime-backed-read-only-adapter` | Needs task text and changed-path coverage. |
| `preflight` | handwritten root parser/dispatch backed by CLI contract manifests | `runtime-backed-read-only-adapter` | Needs active-only conformance. |
| `proof` | handwritten root parser/dispatch backed by CLI contract manifests | `runtime-backed-read-only-adapter` | Needs descriptor setup and changed-path conformance. |
| `ownership` | handwritten root parser/dispatch backed by CLI contract manifests | `runtime-backed-read-only-adapter` | Needs concern/path selector conformance. |
| `skills` | handwritten root parser/dispatch backed by CLI contract manifests | `runtime-backed-read-only-adapter` | Needs task recommendation conformance. |
| `reconcile` | handwritten root parser/dispatch backed by CLI contract manifests | `runtime-backed-read-only-adapter` | Depends on planning package availability and external evidence cache policy. |
| `report` | handwritten root parser/dispatch backed by CLI contract manifests | `runtime-backed-read-only-adapter` | Needs selection/profile/section conformance before promotion. |
| `setup`, `status`, `doctor` | handwritten lifecycle diagnostics | `runtime-backed-read-only-adapter` after root context routers | Selection and module descriptor binding should be factored first. |

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
