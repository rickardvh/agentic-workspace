# Local Integration Area

## Purpose

`.agentic-workspace/local/integrations/` is the sanctioned local-only home for vendor-specific or runtime-specific integration aids.

Use it for disposable helpers that make it cheaper for a local agent/runtime to reach the checked-in workspace outcome without turning those helpers into shared workflow state.

## Folder Convention

Create one direct subfolder per vendor or runtime:

```text
.agentic-workspace/local/integrations/<vendor-or-runtime>/
```

Examples:

```text
.agentic-workspace/local/integrations/codex/
.agentic-workspace/local/integrations/custom-cli/
```

Subfolders may contain prompt helpers, wrappers, export/import shims, native-workflow adapters, resumable handoff helpers, or runtime scratch files.

## Runtime Artifact Shims

A runtime artifact shim is a local-only bridge from agent/runtime artifacts into ordinary Agentic Workspace surfaces. Use it when a runtime has internal plans, check bundles, exported handoff state, or other machine-local artifacts that need a compact workspace-facing summary without making the local file authoritative.

Each shim should keep compact output separate from full evidence:

- Compact output: short status, next action, and proof pointer for the agent.
- Full evidence: an inspectable local artifact, manifest, command log, or exported source file.

Each shim should record metadata before its output is promoted or acted on:

- `kind`
- `source_runtime`
- `artifact_class`
- `input_owner`
- `output_target`
- `authority`
- `promotion_target`
- `proof_command`
- `created_at`

Local shim output is never shared authority by itself. Promote useful results only through checked-in planning, memory, agent-aid, docs, or repo-native review surfaces, with proof attached to the promoted surface.

## Delegated-run protocol

An external orchestrator consumes the released external-consumer profile and
generated Python or TypeScript client. It must not read or edit Planning files.
The small vendor-neutral sequence is:

1. Query the current assignment/action decision and its revision.
2. Use `assignment.export` to obtain the canonical packet and run identity.
3. Invoke its own target and record only transport provenance; transport success
   is neither worker success nor AW admission, proof, integration, or closeout.
4. Use `assignment.import` to return structured success, failure, cancellation,
   or blocked output. Duplicate or stale returns remain recoverable states.
5. Query the assignment state and recovery action, then use `assignment.admit`,
   reject/repair/reassign, or the authorised override operation as directed.
6. Let AW-owned admission, integration, proof, intent satisfaction, and
   closeout remain separate transitions. An adapter cannot mark any of them.

Manual and automatic transport use this same packet/import/admission sequence.
The adapter owns credentials, target discovery, invocation, cancellation, and
disposable local logs; AW owns assignment selection, lifecycle, recovery,
proof, and closeout. Unknown additive result fields must be preserved, and an
incompatible profile or missing operation must fail closed rather than causing
an adapter to reconstruct lifecycle semantics.

## External conformance

Released clients expose the generated external conformance profile from the
same operation-test authority used by AW. Python consumers call
`external_conformance_profile([...])`; TypeScript consumers call
`externalConformanceProfile([...])`. The returned package data names the
transport matrix, readiness cases, operation-specific valid input, current
runtime-exception revision, and any explicit non-applicable mutation vector.

An integration should execute the selected cases through its own transport and
preserve AW's structured result or error unchanged. Missing cases, unavailable
targets, and failed vectors are not passing evidence. A process exit of zero is
not enough for mutation conformance: the integration must retain the applied,
rejected, failed, or explicitly excluded outcome named by the profile. AW
maintainers publish the canonical executed receipts with:

`uv run --active python scripts/check/run_operation_conformance_tests.py --target all --require-node`

That command executes four distinct boundaries: ordinary direct CLI JSON, the
generated Python client, the generated TypeScript client, and a public
TypeScript client packed into an isolated temporary consumer. It exercises the
IR-owned absent, disabled, incompatible, malformed, retryable, additive-field,
and applicable mutation vectors and publishes revision-bound receipts only
when every case records the expected executor provenance. #2198 owns semantic
parity between necessary-surface and full-mirror installations for this bounded
ready subset. #2200 retains the broader independent clean-install, consumer
removal, no-residue, and general adapter-readiness closure proof; it does not
substitute for the #2198 footprint matrix.

## Scratch Space

Use `.agentic-workspace/local/scratch/` freely for temporary agent working files. It is git-ignored local space and is there so agents do not need to invent a repo-specific scratch convention.

## Boundary Rules

- The area is local-only and git-ignored.
- Ordinary workspace commands must not require it to exist.
- It is non-authoritative for planning, memory, startup, review, and workflow state.
- It must be safe to delete without changing repo-owned shared behavior.
- It is not a plugin registry, shared compatibility framework, or source of canonical workflow truth.
- Adapter configuration, credentials, trust decisions, package lifecycle, and global caches stay in the external tool's own storage.
- A local integration may consume released AW client/profile resources, but ordinary AW commands and necessary-surface installs must never depend on its files.
- Deleting a consumer and its local subfolder must leave checked-in AW state and ordinary AW operation unchanged.

Durable facts that should survive across agents belong in the appropriate checked-in workspace, planning, memory, or repo-owned documentation surface instead.
