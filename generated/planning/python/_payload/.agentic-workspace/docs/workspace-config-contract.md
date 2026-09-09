# Workspace Config Contract

This installed contract is the no-CLI companion to `.agentic-workspace/config.toml`.
It is intentionally self-contained so a necessary-surface footprint does not depend on source-checkout documentation.

## Authority

- `.agentic-workspace/config.toml` is repo-owned policy.
- `.agentic-workspace/config.local.toml` is optional machine-local policy and must not become shared authority.
- `.agentic-workspace/OWNERSHIP.toml` owns subsystem and managed-surface boundaries.
- Planning owns active execution state; Memory owns durable anti-rediscovery knowledge; Verification owns reported evidence.
- `AGENTS.md` and installed skills are routing adapters over these structured owners.

## Safe fallback

When the configured CLI is unavailable, preserve the last known forbidden actions and avoid mutating managed Planning, Memory, Verification, provenance, or generated surfaces by hand. Read the installed startup skill and module map, then inspect only the named owner surface. Restore a compatible configured invocation before claiming implementation or closeout.

When the CLI works, use its configured `start --target . --task "<task>" --format json` route. Follow the decision packet, submit only bounded answers in returned requests, and execute only the exact returned action through `invoke`.

## Verification source boundary

Keep durable workspace choices and general trust policy in shared configuration.
Operational Verification requirements, proof profiles, domain lanes and subsystem
metadata belong in `.agentic-workspace/verification/manifest.toml` under `[assurance]`.
A source transfer preserves the declarations' force, provenance, commands and
applicability; it does not grant proof, waive policy or acquire native custody.

Former shared-config sections remain recognized for bounded transition. Do not
author new operational registries there. A section present in both sources is an
ownership conflict, even if its bytes look equivalent; preserve both until its
owner resolves the transfer. Re-resolve current requests after a transfer or edit.
The manifest cannot replace shared assurance level/escalation policy. Unsupported
subsystem semantics remain an explicit Verification gap.

Local target confidence is a human-authored prior. Lifecycle learning belongs to
the target-evidence owner; it must not tune `config.local.toml`. Task answers,
setup continuation and proof results are not durable configuration choices.

## Editing rule

Edit shared config only for an intentional repo-policy change. Keep machine paths, credentials, and local execution preferences in local config. Module state is not workspace config and must be changed through its owning module when that command surface is available.

Use the current configuration owner requests returned by native startup. The
admitted writer can set `workspace.cli_invoke` in an existing canonical shared
or local source, including insertion when unrelated bytes can be preserved. It binds the selected source bytes, effective policy,
capability revision and exact value, revalidates immediately before writing, and
preserves unrelated source text. An irreducible human choice requires the exact
bounded human answer. It grants no continuing custody or capability enablement.

Other keys, new source creation and the complete configure-once journey require
their current owner; do not substitute a retired setup/config command. Preserve
recognized unresolved sources and keep their blockers scoped to affected behavior.

Task answers, setup continuation, receipts and learned conclusions belong with
their domain owners outside human-facing configuration. Preserve any former local
`[setup]` or assignment-answer source until its owner explicitly dispositions it;
do not write new task state there or infer that an old answer remains current.
Interruption recovery for an admitted configuration write uses its exact retained
attempt/result, without treating that record as future source ownership.
