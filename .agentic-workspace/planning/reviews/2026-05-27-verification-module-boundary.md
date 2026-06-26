# Verification Module Boundary Investigation

## Intent

GitHub #1159 asks whether Agentic Workspace should grow a repo-native
verification module for soft or semi-structured verification protocols, manual
scenarios, evidence bundles, transcripts, proof-route artifacts, and reusable
review evidence.

The answer is: yes, but only as a narrow repo-native owner for verification
protocols and bounded evidence records. Verification should not become a second
Planning system, an Assurance store, a Memory dump, a CI replacement, or a
general evaluator platform.

## Recommendation

Create a small `verification` module boundary when implementation starts:

```text
Planning says what work is active.
Assurance says what evidence is required.
Verification says how evidence is produced, repeated, recorded, bounded, and reviewed.
Proof routes verification work into validation choices.
Closeout says what may honestly be claimed.
Memory keeps durable anti-rediscovery lessons after verification, not raw evidence.
```

Start with read projection and schemas, not a writer-heavy subsystem. The first
slice should define a minimal manifest for verification protocols and project it
through report/proof surfaces. Evidence bundle writing and transcript retention
can follow only after the protocol routing shape proves useful.

## Existing Surface Inventory

- Planning owns active work, intent, decomposition, control gates, proof reports,
  intent proof, closeout distillation, durable residue, and continuation owners.
- Assurance owns repo-declared evidence requirements, activation signals, proof
  profiles, authority refs, force, claim blockers, waiver, and dismissal state.
- Workflow obligations own repo-configured lifecycle commands and review hints.
- Proof owns proof selection, selected lanes, proof confidence, and the
  validation/review commands that should be run for changed work.
- Closeout trust owns proof-to-claim reconciliation, completion option blockers,
  residue routing, and issue/parent closure honesty.
- Memory owns durable anti-rediscovery knowledge, freshness/promotion metadata,
  and compact notes after repeated value is proven.
- The long-horizon harness owns disposable evaluator runs, model transcripts,
  hidden/reference oracle handling, and maintainer review evidence for
  exploratory optimisation.

Those surfaces are enough to require, select, consume, and remember evidence.
They are not enough to own reusable soft verification procedures or bounded
human/model evidence artifacts.

## Artifacts With No Good Home

These artifacts currently fall between owners:

- Manual scenarios that should be repeated across tasks but are not active
  Planning work.
- Soft verification protocols that explain how to produce evidence for a
  repo-specific claim, such as "run this manual UI path and capture these
  observations".
- Evidence bundles that are not automated CI output but should still be cited by
  proof and closeout.
- Transcript summaries and hashes for long-horizon/model-agent runs whose raw
  transcript should not become durable Memory.
- Proof-route records that map a changed path, task marker, assurance
  requirement, or proof profile to a verification protocol.
- Known verification gaps with reopen triggers, expiry, and claim boundaries.

Planning can reference these artifacts while work is active, Assurance can
require them, Proof can select them, and Closeout can consume them. None of
those owners should become the canonical library of reusable verification
protocols.

## Boundary Decision

Verification is justified as a module if its artifacts need to be checked in,
durable, reviewable, branch-aware, and reused across agents working in the repo.
It is not justified for ephemeral provider session state, generic UI automation,
global evaluator analytics, or broad compliance semantics.

The module should own:

- protocol definitions;
- scenario definitions;
- proof-route mappings from repo signals to protocols;
- bounded evidence bundle records;
- transcript summaries, retention metadata, and optional raw transcript refs;
- known-gap records for verification that remains incomplete.

The module should not own:

- active task state;
- required evidence semantics;
- automated CI execution;
- completion claim authority;
- Memory promotion decisions;
- model benchmark scoring as a product feature.

## Minimal Artifact Model

### Protocol

```text
id
title
purpose
applies_to_paths
applies_to_task_markers
assurance_requirement_refs
proof_profiles
scenario_refs
steps
expected_evidence
review_owner
authority_refs
stale_when
retention
non_goals
```

Protocols describe how evidence is produced and reviewed. They should not
declare that evidence is required; Assurance owns that.

### Scenario

```text
id
protocol_id
title
steps
expected_observations
pass_evidence_labels
fail_evidence_labels
automation_hint
manual_boundary
```

Scenarios are reusable execution recipes. They can be manual, semi-automated, or
adapter-backed.

### Evidence Bundle

```text
id
protocol_id
scenario_id
task_refs
issue_refs
pr_refs
changed_paths
executor
executed_at
outcome
evidence_items
transcript_refs
transcript_summaries
residual_risk
claim_boundaries
reviewer
retention_until
stale_when
```

Evidence bundles should be compact enough for closeout and review. Raw logs or
large transcripts should be referenced, summarized, bounded, and expirable.

### Proof Route

```text
id
matches
protocol_refs
scenario_refs
proof_lane_hint
assurance_requirement_refs
reason
```

Proof routes bridge changed paths, task markers, assurance requirements, and
proof profiles into verification protocols.

### Known Gap

```text
id
protocol_id
reason
owner
created_from
reopen_trigger
blocked_claims
residual_risk
status
```

Known gaps keep incomplete verification honest without turning every gap into an
active plan.

## Routing

Verification should activate only from explicit repo signals:

- changed path matches protocol or proof-route globs;
- task text matches repo-owned task markers;
- active Planning references cite a verification protocol or scenario;
- Assurance requirement references required evidence or a proof profile that maps
  to a protocol;
- proof selection asks for a lane whose route includes a protocol;
- closeout finds an active claim that cites or requires a verification evidence
  bundle.

The ordinary tiny path should stay quiet when no route matches. Detail belongs in
`report --section verification`, selected/verbose proof output, and closeout
trust when a claim boundary is affected.

## Retention And Transcript Bounding

Protocols and scenarios are durable repo artifacts.

Evidence bundles should be retained while they support active work, issue
closure, parent-lane closure, assurance gates, or recurring evaluator analysis.
After that, they should either shrink to a retained summary, move a durable
lesson to Memory/docs/checks, or expire.

Transcripts need stricter bounds:

- store summary first;
- keep raw transcript refs optional;
- record source tool/model and execution context;
- record hash/path when raw material is retained;
- set retention and redaction posture explicitly;
- avoid promoting raw transcript content to Memory;
- keep hidden/reference oracle material out of primary evaluator prompts and
  expose it only as post-score review metadata.

Memory receives only durable lessons, anti-rediscovery notes, unresolved
recurring gaps, or promotion pressure after verification. Planning receives only
current-work references, evidence status, and continuation decisions.

## Proof And Closeout Integration

Proof should consume verification protocols as review aids and validation lanes:

- selected proof can cite matched protocol ids and scenario ids;
- matched assurance requirements can pull protocol-linked proof commands;
- proof confidence can state whether verification evidence is absent, manual,
  representative, or sufficient for the claim boundary;
- proof output should separate automated checks from soft verification evidence.

Closeout should consume evidence status, not own verification artifacts:

- missing required verification evidence can block `claim-work-complete` and
  `close-parent-lane`;
- `request-review`, `route-residue`, and `stop-with-status` remain available;
- waived/dismissed verification should require owner and reason through the
  Assurance or Planning surface that owns the waiver;
- closeout should cite evidence bundle ids and residual risk rather than embed
  transcripts.

## Candidate Workflows

### Intent-Proof Manual Scenario Reuse

A repo has a recurring user-visible behavior that cannot be proven by tests
alone. A verification protocol defines the manual scenario and expected
observations. Proof selects the scenario when matching files or task markers
change. Closeout accepts the claim only when the evidence bundle or an explicit
residual-risk note is present.

### High-Assurance Evidence Recording

An assurance requirement declares `required_evidence = ["operator_runbook_review",
"manual_recovery_scenario"]`. Verification maps those labels to concrete
protocols. Proof shows the protocol steps. Closeout blocks broad claims until an
evidence bundle, waiver, or dismissal exists.

### Long-Horizon Evaluator Evidence

The model CLI harness produces transcripts, checkpoints, evaluator output, and a
post-score reference oracle. Verification records the reusable episode protocol,
retains only bounded summaries and refs, and lets Memory receive recurring
lessons after repeated evidence.

### Non-Code Verification

A docs/runbook/config change needs a human review sequence rather than tests. A
verification scenario records the review protocol, expected evidence labels, and
claim boundary. Proof selects a review lane; closeout cites the evidence bundle
or routes residue.

## First Implementation Slice

Create a child issue for:

```text
[Verification]: Add minimal verification protocol manifest and report projection
```

Scope:

- add `.agentic-workspace/verification/manifest.toml` schema support;
- support protocol and scenario records with activation signals;
- require stable ids, purpose, at least one activation signal, and review owner
  or explicit ownerless posture;
- add `report --section verification` projection;
- include matched protocol ids in proof/report surfaces when explicitly selected
  or verbose;
- keep default start/implement/proof output quiet unless a route affects the next
  action or claim boundary;
- no evidence writer, transcript store, or closeout gates yet.

## Follow-Up Issues

1. Add protocol manifest and report projection.
2. Route matched protocols into proof selection and routine work context.
3. Add bounded evidence bundle schema and closeout citation support.
4. Add transcript retention/summarization policy for harness and manual runs.
5. Add Assurance integration so requirements can map required evidence to
   protocol ids.
6. Add a high-assurance/manual-scenario fixture that proves the loop end to end.

## Non-Goals

- Do not create a generic verification or compliance platform.
- Do not store active evidence in Memory.
- Do not duplicate CI or automated test execution.
- Do not make raw transcripts durable by default.
- Do not make all configured verification protocols noisy for unrelated tasks.
- Do not let verification decide completion claims; Closeout owns that.
- Do not encode domain-specific semantics in AW beyond repo-owned labels and
  references.

## Module Vs Report Section

A report section alone is sufficient if the only need is to summarize existing
proof, assurance, and closeout state. A module is justified when the repo needs
durable, reusable verification protocols or bounded evidence artifacts that are
neither active Planning records nor Memory notes.

#1159 meets that threshold for protocol/scenario reuse, high-assurance soft
evidence, long-horizon evaluator evidence, and non-code verification.

## Validation

This investigation is design-only. Recommended validation for the artifact:

- `uv run agentic-workspace implement --changed .agentic-workspace/planning/reviews/2026-05-27-verification-module-boundary.md .agentic-workspace/planning/reviews/2026-05-27-verification-module-boundary.review.json --task "Ingest #1159 and complete verification module boundary investigation" --format json`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run python -m json.tool .agentic-workspace/planning/reviews/2026-05-27-verification-module-boundary.review.json`
