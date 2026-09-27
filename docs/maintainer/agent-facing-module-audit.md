# Module agent-facing audit (#3669)

This audit covers every current Planning and Memory skill source, registry,
README and host prompt. No `.agentic-workspace/verification/skills/` directory
exists; the core proof procedure is audited in #3668. The canonical writing guide
is unchanged.

| Source | Disposition | Reason |
| --- | --- | --- |
| `.agentic-workspace/memory/skills/memory-capture/agents/openai.yaml` | rewrite | Launcher describes supported operations and removes retired command or rewrite claims. |
| `.agentic-workspace/memory/skills/memory-capture/procedure.md` | rewrite | Branch descriptions identify observable missing input or result; identities and resources are unchanged. |
| `.agentic-workspace/memory/skills/memory-capture/references/candidate.md` | rewrite | Anchors the action to concrete records, returned fields or an exact source link. |
| `.agentic-workspace/memory/skills/memory-capture/references/destination.md` | keep | Choose the smallest responsible home: concrete inputs and exact supported operations already identify scope and recovery. |
| `.agentic-workspace/memory/skills/memory-capture/references/publication.md` | keep | Authored decision and publication: concrete inputs and exact supported operations already identify scope and recovery. |
| `.agentic-workspace/memory/skills/memory-capture/SKILL.md` | rewrite | Names the situation, action and stopping boundary before internal terminology. |
| `.agentic-workspace/memory/skills/memory-consultation-and-residue/agents/openai.yaml` | rewrite | Launcher describes supported operations and removes retired command or rewrite claims. |
| `.agentic-workspace/memory/skills/memory-consultation-and-residue/SKILL.md` | rewrite | Names the situation, action and stopping boundary before internal terminology. |
| `.agentic-workspace/memory/skills/memory-hygiene/agents/openai.yaml` | rewrite | Launcher describes supported operations and removes retired command or rewrite claims. |
| `.agentic-workspace/memory/skills/memory-hygiene/procedure.md` | rewrite | Branch descriptions identify observable missing input or result; identities and resources are unchanged. |
| `.agentic-workspace/memory/skills/memory-hygiene/references/declarations.md` | keep | Inspect bounded declaration hygiene: concrete inputs and exact supported operations already identify scope and recovery. |
| `.agentic-workspace/memory/skills/memory-hygiene/references/disposition.md` | keep | Retain, retire or promote selected material: concrete inputs and exact supported operations already identify scope and recovery. |
| `.agentic-workspace/memory/skills/memory-hygiene/references/repair.md` | keep | Repair and receiving evidence: concrete inputs and exact supported operations already identify scope and recovery. |
| `.agentic-workspace/memory/skills/memory-hygiene/SKILL.md` | rewrite | Names the situation, action and stopping boundary before internal terminology. |
| `.agentic-workspace/memory/skills/memory-refresh/agents/openai.yaml` | rewrite | Launcher describes supported operations and removes retired command or rewrite claims. |
| `.agentic-workspace/memory/skills/memory-refresh/SKILL.md` | keep | Memory Refresh: concrete inputs and exact supported operations already identify scope and recovery. |
| `.agentic-workspace/memory/skills/memory-router/agents/openai.yaml` | keep | Prompt names the narrow note-selection task and adds no operation or permission. |
| `.agentic-workspace/memory/skills/memory-router/SKILL.md` | rewrite | Names the situation, action and stopping boundary before internal terminology. |
| `.agentic-workspace/memory/skills/memory-upgrade/agents/openai.yaml` | rewrite | Launcher describes supported operations and removes retired command or rewrite claims. |
| `.agentic-workspace/memory/skills/memory-upgrade/SKILL.md` | rewrite | Anchors the action to concrete records, returned fields or an exact source link. |
| `.agentic-workspace/memory/skills/README.md` | rewrite | Removes stale summary/command claims and routes to current methods with correct ownership. |
| `.agentic-workspace/memory/skills/REGISTRY.json` | rewrite | Summaries match the actual methods; activation entries are generated from procedure sources. |
| `.agentic-workspace/planning/skills/bootstrap-upgrade/SKILL.md` | rewrite | Anchors the action to concrete records, returned fields or an exact source link. |
| `.agentic-workspace/planning/skills/planning-assignment/procedure.md` | rewrite | Branch descriptions identify observable missing input or result; identities and resources are unchanged. |
| `.agentic-workspace/planning/skills/planning-assignment/references/assessment.md` | rewrite | Names the situation, action and stopping boundary before internal terminology. |
| `.agentic-workspace/planning/skills/planning-assignment/references/binding.md` | keep | Follow current role, target and transport: concrete inputs and exact supported operations already identify scope and recovery. |
| `.agentic-workspace/planning/skills/planning-assignment/references/local.md` | keep | Continue locally or leave the choice unresolved: concrete inputs and exact supported operations already identify scope and recovery. |
| `.agentic-workspace/planning/skills/planning-assignment/references/manual.md` | keep | Carry a sealed manual packet: concrete inputs and exact supported operations already identify scope and recovery. |
| `.agentic-workspace/planning/skills/planning-assignment/references/recovery.md` | keep | Preserve uncertain transport and continuity: concrete inputs and exact supported operations already identify scope and recovery. |
| `.agentic-workspace/planning/skills/planning-assignment/references/return.md` | keep | Admit and integrate returned material: concrete inputs and exact supported operations already identify scope and recovery. |
| `.agentic-workspace/planning/skills/planning-assignment/SKILL.md` | rewrite | Names the situation, action and stopping boundary before internal terminology. |
| `.agentic-workspace/planning/skills/planning-closeout-trust/procedure.md` | rewrite | Branch descriptions identify observable missing input or result; identities and resources are unchanged. |
| `.agentic-workspace/planning/skills/planning-closeout-trust/references/finish.md` | rewrite | Anchors the action to concrete records, returned fields or an exact source link. |
| `.agentic-workspace/planning/skills/planning-closeout-trust/references/intent.md` | keep | Compare the requested outcome: concrete inputs and exact supported operations already identify scope and recovery. |
| `.agentic-workspace/planning/skills/planning-closeout-trust/SKILL.md` | rewrite | Names the situation, action and stopping boundary before internal terminology. |
| `.agentic-workspace/planning/skills/planning-reporting/SKILL.md` | rewrite | Anchors the action to concrete records, returned fields or an exact source link. |
| `.agentic-workspace/planning/skills/planning-review-continuation/procedure.md` | rewrite | Branch descriptions identify observable missing input or result; identities and resources are unchanged. |
| `.agentic-workspace/planning/skills/planning-review-continuation/references/continuation.md` | rewrite | Anchors the action to concrete records, returned fields or an exact source link. |
| `.agentic-workspace/planning/skills/planning-review-continuation/references/triage.md` | keep | Receive and classify current findings: concrete inputs and exact supported operations already identify scope and recovery. |
| `.agentic-workspace/planning/skills/planning-review-continuation/SKILL.md` | rewrite | Names the situation, action and stopping boundary before internal terminology. |
| `.agentic-workspace/planning/skills/planning-work/procedure.md` | rewrite | Branch descriptions identify observable missing input or result; identities and resources are unchanged. |
| `.agentic-workspace/planning/skills/planning-work/references/continuity.md` | rewrite | Anchors the action to concrete records, returned fields or an exact source link. |
| `.agentic-workspace/planning/skills/planning-work/references/intake.md` | rewrite | Names the situation, action and stopping boundary before internal terminology. |
| `.agentic-workspace/planning/skills/planning-work/references/structure.md` | keep | Bound the outcome and its dependencies: concrete inputs and exact supported operations already identify scope and recovery. |
| `.agentic-workspace/planning/skills/planning-work/SKILL.md` | rewrite | Names the situation, action and stopping boundary before internal terminology. |
| `.agentic-workspace/planning/skills/README.md` | rewrite | Removes stale summary/command claims and routes to current methods with correct ownership. |
| `.agentic-workspace/planning/skills/REGISTRY.json` | rewrite | Summaries match the actual methods; activation entries are generated from procedure sources. |

## Generated and preserved boundaries

Declared module copies under `src/core/payload/` are **generated-from-source**
through the existing interface generator. Memory skill sources are not declared
in the current host payload; this change does not widen the shipped surface set.
Registry activation projections are generated. No merge/remove disposition was
needed: the remaining references describe distinct operations or exact recovery.

## Concrete repairs

- Planning reporting no longer promises retired canonical-summary JSON.
- Planning assignment explains the selected worker and the restriction on local
  implementation before using binding terminology; assessment names `target_scope`.
- Memory README no longer asks for directory scans or promises prose pruning.
- Memory hygiene defines retain/retire/promote against the actual metadata effect.
- Memory upgrade launcher no longer suggests retired `agentic-memory` commands;
  it points to the shared setup procedure while preserving repository notes.

These are corrections to procedure and launcher prose, not new native semantics,
capabilities or authority. Exact request identifiers and generated paths remain
unchanged. Fresh-reader and validation results are recorded below.

## Fresh-reader evidence

A reader with no prior AW conversation correctly chose direct work for an unrelated
selected plan, saved missing handoff meaning through Planning, refused local
substitution for a nonlocal assignment, distinguished Memory metadata from prose,
followed shared setup for upgrade, and reused delivered advice without another query.
No wrong action or user intervention was observed. The reader identified terms in
continuity and an imprecise upgrade-source pointer; the source now defines the
complete record/JSON transport and links the exact shared entry and refresh section.
These exercises are implementation evidence, not independent PR review.

A bounded repair recheck confirmed the concrete record/transport definitions, exact
upgrade links and current-result wording. The remaining generic use of frontier
was replaced with remaining work. This recheck is not a second fresh-reader run.

## Validation

The interface, selected-procedure, Memory declaration and Planning creation suites
passed (79 tests). After the reader repairs, the interface and selected-procedure
checks passed again (18 tests). The native workspace build, generator parity,
Markdown and link checks, and whitespace checks passed. One build attempt while
native tests were running failed to replace a Windows executable with access denied;
the build succeeded after those tests finished. No native behavior changed and no
new permanent test framework was added.
